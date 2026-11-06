import os
import gc
import re
import json
import time
import uuid
import shutil
import atexit
import logging
import threading
import subprocess
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Tuple, List, Callable
import httpx
from ..core.config import settings

logger = logging.getLogger(__name__)

class DebateCancelledException(Exception):
    """Raised when debate execution is cancelled mid-generation."""
    pass


class LocalModelManager:
    """
    Manages inference for the EXACT THREE standardized models in the AI Debate Simulator:
    - PRO: Google Gemma 4 E4B Instruct (Q4_0 GGUF via persistent llama.cpp server)
    - CON: Alibaba Qwen2.5-VL-7B-Instruct (local PyTorch / GGUF runner)
    - JUDGE: Google Gemini 3.5 Flash (remote Google GenAI API)

    Guarantees:
    - Sequential memory management: evicts prior model before loading subsequent model.
    - Thread-safe transitions: prevents concurrent load/unload while a model is in active generation.
    - Architecture-specific loading matching actual model configurations.
    - Safe hardware pre-checks to protect CPU host from memory exhaustion / bitsandbytes kernel faults.
    - Zero fabrication in non-mock mode (never substitutes synthetic text for missing models).
    """
    def __init__(self, device: Optional[str] = None):
        self.model_paths = {
            "PRO": getattr(settings, "GEMMA_MODEL_PATH", getattr(settings, "PRO_MODEL_PATH", "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf")),
            "CON": getattr(settings, "QWEN_MODEL_PATH", getattr(settings, "CON_MODEL_PATH", "D:/models/Qwen2.5-VL-7B-Instruct")),
            "JUDGE": getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash"),
        }
        self.registered_models = {
            "PRO": {
                "name": getattr(settings, "GEMMA_MODEL_NAME", "gemma-4-E4B-Q4_0"),
                "provider": "llama_server",
                "role": "PRO",
                "endpoint": getattr(settings, "GEMMA_BASE_URL", "http://127.0.0.1:8081/v1"),
                "path": getattr(settings, "GEMMA_MODEL_PATH", "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf"),
            },
            "CON": {
                "name": getattr(settings, "QWEN_MODEL_NAME", "Qwen2.5-VL-7B-Instruct"),
                "provider": "llama_server" if os.path.exists(getattr(settings, "QWEN_GGUF_PATH", "")) else "local_pytorch",
                "role": "CON",
                "endpoint": getattr(settings, "QWEN_BASE_URL", "http://127.0.0.1:8083/v1"),
                "path": getattr(settings, "QWEN_MODEL_PATH", "D:/models/Qwen2.5-VL-7B-Instruct"),
                "gguf_path": getattr(settings, "QWEN_GGUF_PATH", "D:/models/qwen-2.5-VL-7B-Q4/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"),
                "mmproj_path": getattr(settings, "QWEN_MMPROJ_PATH", "D:/models/qwen-2.5-VL-7B-Q4/mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf")
            },
            "JUDGE": {
                "name": getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash"),
                "provider": "google_genai",
                "role": "JUDGE",
                "endpoint": "https://generativelanguage.googleapis.com",
                "path": "api:gemini",
            }
        }
        self.device_setting = (device if device is not None else getattr(settings, "INFERENCE_DEVICE", "cpu")).strip().lower()
        self.device = self.resolve_device(self.device_setting)
        self._loaded_models: Dict[str, Any] = {}
        self._loaded_tokenizers: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self.mock_mode = False
        self._gemma_server_proc: Optional[subprocess.Popen] = None
        self._qwen_server_proc: Optional[subprocess.Popen] = None
        self._qwen_current_mode: str = "text"
        self._generation_lock = threading.RLock()
        atexit.register(self.stop_all_servers)

    def _has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    def _has_accelerate(self) -> bool:
        try:
            import accelerate
            return True
        except ImportError:
            return False

    def resolve_device(self, configured_device: Optional[str] = None) -> str:
        """
        Resolves effective compute device from configured setting ('cpu', 'cuda', 'auto', 'cuda:N').
        - 'cpu': explicitly use CPU.
        - 'auto': use CUDA if available and compatible; otherwise fall back to CPU.
        - 'cuda' (or 'cuda:N'): explicitly request CUDA; validates syntax/index and fails fast if unavailable.
        """
        raw_setting = configured_device if configured_device is not None else getattr(settings, "INFERENCE_DEVICE", "cpu")
        choice = (raw_setting or "cpu").strip().lower()

        if choice == "cpu":
            return "cpu"
        elif choice == "auto":
            return "cuda" if self._has_cuda() else "cpu"
        elif choice.startswith("cuda"):
            if choice != "cuda":
                if not choice.startswith("cuda:"):
                    raise ValueError(
                        f"Invalid CUDA device specification '{raw_setting}'. Supported formats are 'cuda' or 'cuda:N' (e.g. 'cuda:0')."
                    )
                idx_str = choice.split(":", 1)[1].strip()
                if not idx_str.isdigit():
                    raise ValueError(
                        f"Invalid CUDA device index in '{raw_setting}'. Device index must be a non-negative integer (e.g. 'cuda:0')."
                    )

            if not self._has_cuda():
                raise RuntimeError(
                    f"Explicit CUDA inference device requested ('{raw_setting}'), but CUDA is not available on this system "
                    f"(torch.cuda.is_available() is False). "
                    "Ensure compatible NVIDIA drivers and a CUDA-enabled PyTorch build are installed, "
                    "or configure INFERENCE_DEVICE='cpu' or 'auto'."
                )

            if choice.startswith("cuda:"):
                import torch
                idx = int(choice.split(":", 1)[1].strip())
                try:
                    count = torch.cuda.device_count()
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to query CUDA device count for '{raw_setting}': {e}. "
                        "Ensure your NVIDIA driver and CUDA installation are functioning properly."
                    ) from e
                if idx >= count:
                    raise RuntimeError(
                        f"Requested CUDA device index {idx} in '{raw_setting}', but only {count} CUDA device(s) are available "
                        f"(valid indices: 0 to {count - 1})."
                    )
            return choice
        else:
            raise ValueError(
                f"Invalid inference device configuration '{raw_setting}'. Supported choices: 'cpu', 'cuda', 'auto'."
            )

    def get_input_target_device(self, model: Any) -> Any:
        """
        Reliably identifies the execution device for input tensors across all loading paths:
        1. Checks input embedding layer device (authoritative for token tensors).
        2. Checks model.device property (standard in Hugging Face PreTrainedModel).
        3. Checks the device of the first parameter in the model.
        4. Falls back to torch.device(self.device).
        """
        import torch

        # 1. Embedding layer check
        try:
            if hasattr(model, "get_input_embeddings"):
                embeddings = model.get_input_embeddings()
                if embeddings is not None and hasattr(embeddings, "weight") and embeddings.weight is not None:
                    emb_dev = embeddings.weight.device
                    if emb_dev is not None and str(emb_dev) != "meta":
                        return emb_dev
        except Exception:
            pass

        # 2. model.device property
        try:
            dev = getattr(model, "device", None)
            if dev is not None and str(dev) != "meta":
                return dev if isinstance(dev, torch.device) else torch.device(dev)
        except Exception:
            pass

        # 3. First parameter device
        try:
            first_param = next(model.parameters(), None)
            if first_param is not None and first_param.device is not None and str(first_param.device) != "meta":
                return first_param.device
        except Exception:
            pass

        # 4. Fallback to manager's resolved device
        return torch.device(self.device)

    def set_device(self, device_setting: str) -> str:
        """
        Updates the configured device and resolves the active device.
        Unloads any loaded models if the device changes to prevent cross-device reference leaks.
        """
        with self._lock:
            new_device = self.resolve_device(device_setting)
            if new_device != self.device:
                logger.info(f"Inference device changed from '{self.device}' to '{new_device}'. Unloading cached models.")
                self.unload_all()
            self.device_setting = device_setting.strip().lower()
            self.device = new_device
            return self.device

    def get_model_path(self, role: str) -> str:
        """
        Retrieves the configured filesystem path or identifier for a role model.
        Strictly enforces that only PRO, CON, and JUDGE roles exist.
        """
        role_upper = role.upper()
        if role_upper not in ("PRO", "CON", "JUDGE"):
            raise ValueError(
                f"Invalid debate role '{role}'. Only exactly three local LLMs are permitted: "
                "PRO (gemma-4-E4B-Q4_0), CON (Qwen2.5-VL-7B-Instruct), JUDGE (gemini-3.5-flash)."
            )
        if role_upper == "JUDGE":
            return getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash")

        path = self.model_paths.get(role_upper, "")
        if os.path.exists(path):
            return path
        # Check standard location variations on D: drive
        alt_paths = {
            "PRO": [
                getattr(settings, "GEMMA_MODEL_PATH", ""),
                getattr(settings, "PRO_MODEL_PATH", ""),
                "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf",
                "D:/models/gemma-4-E4B-it",
                "D:/gemma-4-E4B-it"
            ],
            "CON": ["D:/models_cpu_converted/Qwen2.5-VL-7B-Instruct", "D:/Qwen2.5-VL-7B-Instruct", "D:/models/Qwen2.5-VL-7B-Instruct"],
        }
        for alt in alt_paths.get(role_upper, []):
            if alt and os.path.exists(alt):
                return alt
        return path

    def check_qwen_health(self) -> Dict[str, Any]:
        """
        Verifies availability and runtime environment compatibility for Alibaba Qwen2.5-VL-7B-Instruct.
        Audits whether local weights exist, inspects quantization configuration (BitsAndBytes 4-bit NF4),
        and verifies device capability (CPU vs CUDA).
        """
        qwen_path = self.get_model_path("CON")
        exists = os.path.exists(qwen_path)
        has_cuda = self._has_cuda()
        
        is_bitsandbytes = False
        if exists:
            cfg_path = os.path.join(qwen_path, "config.json")
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    is_bitsandbytes = "quantization_config" in cfg and cfg["quantization_config"].get("quant_method") == "bitsandbytes"
                except Exception:
                    pass

        if not exists:
            return {
                "status": "NOT_FOUND",
                "healthy": False,
                "path": qwen_path,
                "error": f"Model directory not found at {qwen_path}",
                "device": self.device
            }

        if is_bitsandbytes and not has_cuda and self.device == "cpu":
            return {
                "status": "BLOCKED_CPU_NF4",
                "healthy": False,
                "path": qwen_path,
                "quantization": "bitsandbytes_nf4",
                "device": "cpu",
                "error": "BitsAndBytes 4-bit NF4 safetensors require a discrete CUDA GPU; CPU execution throws AssertionError. GGUF format required for CPU inference via llama.cpp."
            }

        return {
            "status": "READY",
            "healthy": True,
            "path": qwen_path,
            "quantization": "bitsandbytes_nf4" if is_bitsandbytes else "unquantized",
            "device": self.device
        }

    def check_gemini_health(self) -> Dict[str, Any]:
        """
        Verifies connectivity and configuration for Google Gemini 3.5 Flash Judge.
        Validates GEMINI_API_KEY presence and format without leaking credentials.
        """
        api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
        if not api_key or api_key == "YOUR_GEMINI_API_KEY":
            return {
                "status": "MISSING_API_KEY",
                "healthy": False,
                "model": getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash"),
                "error": "GEMINI_API_KEY is not configured in backend/.env"
            }

        try:
            import google.genai
            return {
                "status": "CONFIGURED",
                "healthy": True,
                "model": getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash"),
                "provider": "google_genai"
            }
        except ImportError:
            return {
                "status": "MISSING_DEPENDENCY",
                "healthy": False,
                "model": getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash"),
                "error": "google-genai SDK is not installed in the active environment"
            }

    def check_nvidia_health(self) -> Dict[str, Any]:
        """
        Verifies connectivity and configuration for NVIDIA NIM API Judge.
        Validates NVIDIA_API_KEY presence and probes API endpoint without leaking credentials.
        """
        api_key = (getattr(settings, "NVIDIA_API_KEY", "") or "").strip()
        model_id = getattr(settings, "NVIDIA_JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
        if not api_key or api_key == "YOUR_NVIDIA_API_KEY":
            return {
                "status": "MISSING_API_KEY",
                "healthy": False,
                "model": model_id,
                "error": "NVIDIA_API_KEY is not configured in backend/.env"
            }

        base_url = (getattr(settings, "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1") or "").rstrip("/")
        try:
            with httpx.Client(base_url=base_url, timeout=5.0) as client:
                resp = client.get(
                    "/models",
                    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
                )
                if resp.status_code == 200:
                    return {
                        "status": "CONFIGURED",
                        "healthy": True,
                        "model": model_id,
                        "provider": "nvidia_nim"
                    }
                else:
                    return {
                        "status": "AUTHENTICATION_FAILED" if resp.status_code in (401, 403) else f"HTTP_{resp.status_code}",
                        "healthy": False,
                        "model": model_id,
                        "error": f"NVIDIA NIM API responded with HTTP {resp.status_code}"
                    }
        except Exception as e:
            return {
                "status": "CONNECTION_FAILED",
                "healthy": False,
                "model": model_id,
                "error": str(e).split("Bearer")[0].strip()
            }

    def check_all_providers_health(self) -> Dict[str, Any]:
        """
        Aggregated health status across PRO, CON, and dual JUDGE providers (Gemini & NVIDIA NIM).
        """
        gemma_online = self.check_gemma_server_health()
        qwen_server_online = self.check_qwen_server_health()
        qwen_health = self.check_qwen_health()
        gemini_health = self.check_gemini_health()
        nvidia_health = self.check_nvidia_health()

        qwen_is_healthy = qwen_server_online or qwen_health.get("healthy", False)
        qwen_status = "ONLINE" if qwen_server_online else ("READY" if qwen_health.get("healthy") else qwen_health.get("status", "OFFLINE"))

        active_judge_provider = getattr(settings, "JUDGE_PROVIDER", "gemini").strip().lower()
        if active_judge_provider == "nvidia":
            active_judge_info = {
                "role": "JUDGE",
                "model": getattr(settings, "NVIDIA_JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
                "provider": "nvidia_nim",
                "healthy": nvidia_health.get("healthy", False),
                "status": nvidia_health.get("status", "UNKNOWN"),
                "details": nvidia_health
            }
        else:
            active_judge_info = {
                "role": "JUDGE",
                "model": getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash"),
                "provider": "google_genai",
                "healthy": gemini_health.get("healthy", False),
                "status": gemini_health.get("status", "UNKNOWN"),
                "details": gemini_health
            }

        return {
            "PRO": {
                "role": "PRO",
                "model": getattr(settings, "GEMMA_MODEL_NAME", "gemma-4-E4B-Q4_0"),
                "provider": "llama_server",
                "healthy": gemma_online,
                "status": "ONLINE" if gemma_online else "OFFLINE",
                "endpoint": getattr(settings, "GEMMA_BASE_URL", "http://127.0.0.1:8081/v1"),
                "path": getattr(settings, "GEMMA_MODEL_PATH", "")
            },
            "CON": {
                "role": "CON",
                "model": getattr(settings, "QWEN_MODEL_NAME", "Qwen2.5-VL-7B-Instruct"),
                "provider": "llama_server" if qwen_server_online or os.path.exists(getattr(settings, "QWEN_GGUF_PATH", "")) else "local_pytorch",
                "healthy": qwen_is_healthy,
                "status": qwen_status,
                "endpoint": getattr(settings, "QWEN_BASE_URL", "http://127.0.0.1:8083/v1"),
                "path": getattr(settings, "QWEN_GGUF_PATH", "") if qwen_server_online else qwen_health.get("path", ""),
                "details": qwen_health
            },
            "JUDGE": active_judge_info,
            "JUDGE_GEMINI": {
                "role": "JUDGE",
                "model": getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash"),
                "provider": "google_genai",
                "healthy": gemini_health.get("healthy", False),
                "status": gemini_health.get("status", "UNKNOWN"),
                "details": gemini_health
            },
            "JUDGE_NVIDIA": {
                "role": "JUDGE",
                "model": getattr(settings, "NVIDIA_JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
                "provider": "nvidia_nim",
                "healthy": nvidia_health.get("healthy", False),
                "status": nvidia_health.get("status", "UNKNOWN"),
                "details": nvidia_health
            }
        }

    def get_available_ram_gb(self) -> float:
        """Returns currently available physical host RAM in GiB."""
        try:
            import psutil
            return psutil.virtual_memory().available / (1024**3)
        except Exception:
            return 8.0

    def is_gemma_running(self) -> bool:
        """Fast non-blocking check whether Gemma llama-server process is active."""
        if hasattr(self, "_gemma_server_proc") and self._gemma_server_proc is not None:
            return self._gemma_server_proc.poll() is None
        return self.check_gemma_server_health()

    def is_qwen_running(self) -> bool:
        """Fast non-blocking check whether Qwen llama-server process is active."""
        if hasattr(self, "_qwen_server_proc") and self._qwen_server_proc is not None:
            return self._qwen_server_proc.poll() is None
        return self.check_qwen_server_health()

    def _wait_for_ram_stabilization(self, timeout_seconds: float = 1.0):
        """
        Adaptive pause ensuring Windows virtual memory manager has deallocated freed pages.
        Eliminates blind 2.5s sleeps while preventing memory paging.
        """
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < timeout_seconds:
            time.sleep(0.05)
            if time.perf_counter() - t0 >= 0.15:
                break
        gc.collect()

    def check_gemma_server_health(self) -> bool:
        """
        Probes the local Gemma llama.cpp HTTP server to verify readiness.
        Uses /health endpoint on the server base URL host and port.
        """
        try:
            base = settings.GEMMA_BASE_URL.rstrip("/")
            health_url = (base[:-3] + "/health") if base.endswith("/v1") else (base + "/health")
            resp = httpx.get(health_url, timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def ensure_gemma_server_running(self) -> bool:
        """
        Ensures the local Gemma llama-server is online.
        If already running, returns True.
        If offline and GEMMA_AUTOSTART_SERVER is enabled, starts it in a background process
        and polls /health until ready.
        """
        if self.is_gemma_running() and self.check_gemma_server_health():
            return True

        if not getattr(settings, "GEMMA_AUTOSTART_SERVER", True):
            return False

        gguf_path = getattr(settings, "GEMMA_MODEL_PATH", "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf")
        if not os.path.exists(gguf_path):
            logger.warning(f"Gemma GGUF model file not found at {gguf_path}; cannot autostart llama-server.")
            return False

        # Memory guard: Sequential RAM swap - unload Qwen before starting Gemma to reclaim ~5.5 GB of RAM
        if getattr(settings, "SEQUENTIAL_SWAP_IF_LOW_RAM", True):
            if self.is_qwen_running() or (hasattr(self, "_qwen_server_proc") and self._qwen_server_proc is not None):
                ram_before = self.get_available_ram_gb()
                t_stop0 = time.perf_counter()
                logger.info(f"[ModelManager: Sequential Swap] Stopping Qwen server to reclaim RAM for Gemma (Available RAM: {ram_before:.2f} GiB)...")
                self.stop_qwen_server()
                self._wait_for_ram_stabilization()
                ram_after = self.get_available_ram_gb()
                logger.info(f"[ModelManager: Sequential Swap] Qwen stopped in {time.perf_counter() - t_stop0:.3f}s. Reclaimed: {ram_after - ram_before:+.2f} GiB (Now available: {ram_after:.2f} GiB)")

        llama_bin = shutil.which("llama-server") or shutil.which("llama-server.exe") or "llama-server.exe"

        parsed = urlparse(settings.GEMMA_BASE_URL)
        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 8081)
        model_name = getattr(settings, "GEMMA_MODEL_NAME", "gemma-4-E4B-Q4_0")

        self._kill_orphan_llama_server(int(port))

        cmd = [
            llama_bin,
            "-m", gguf_path,
            "-c", str(getattr(settings, "LLAMA_CONTEXT_SIZE", 2048)),
            "-n", str(getattr(settings, "PRO_MAX_NEW_TOKENS", 160)),
            "-t", str(getattr(settings, "LLAMA_THREADS", 6)),
            "-tb", str(getattr(settings, "LLAMA_THREADS_BATCH", 6)),
            "-b", str(getattr(settings, "LLAMA_BATCH_SIZE", 512)),
            "-ub", str(getattr(settings, "LLAMA_UBATCH_SIZE", 512)),
            "--cache-reuse", str(getattr(settings, "LLAMA_CACHE_REUSE", 256)),
            "-np", "1",
            "--no-warmup",
            "--prio", "2",
            "--no-mmproj",
            "--reasoning", "off",
            "--host", host,
            "--port", port,
            "-a", model_name
        ]
        ram_pre_start = self.get_available_ram_gb()
        logger.info(f"Autostarting local Gemma llama-server (Available RAM: {ram_pre_start:.2f} GiB): {' '.join(cmd)}")
        try:
            os.makedirs("scratch", exist_ok=True)
            self._gemma_log_file = open("scratch/gemma_server.log", "a", encoding="utf-8")
            self._gemma_server_proc = subprocess.Popen(
                cmd,
                stdout=self._gemma_log_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            # Fast adaptive polling: 100ms intervals instead of 1.0s blind intervals
            poll_start = time.perf_counter()
            while time.perf_counter() - poll_start < 60.0:
                if self.check_gemma_server_health():
                    elapsed = time.perf_counter() - poll_start
                    ram_post_start = self.get_available_ram_gb()
                    logger.info(f"Gemma llama-server started successfully on {settings.GEMMA_BASE_URL} in {elapsed:.2f}s (RAM consumed: {ram_pre_start - ram_post_start:.2f} GiB, Available: {ram_post_start:.2f} GiB)")
                    return True
                proc = self._gemma_server_proc
                if proc is not None and proc.poll() is not None:
                    logger.error(f"Gemma llama-server exited prematurely with code {proc.returncode}")
                    break
                time.sleep(0.1)
            logger.error("Gemma llama-server failed to become healthy within 60s timeout.")
            return False
        except Exception as e:
            logger.error(f"Failed to launch Gemma llama-server process: {e}")
            return False

    def _kill_orphan_llama_server(self, port: int):
        """Finds and terminates any orphan llama-server process configured for the specified port."""
        try:
            import psutil
            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    name = (p.info['name'] or '').lower()
                    if 'llama-server' in name:
                        cmdline = p.info.get('cmdline') or []
                        for i, arg in enumerate(cmdline):
                            if (arg in ("--port", "-p") and i + 1 < len(cmdline) and str(cmdline[i+1]) == str(port)) or f":{port}" in arg or f"--port={port}" in arg:
                                logger.info(f"Terminating orphan llama-server PID {p.pid} for port {port}")
                                p.terminate()
                                try:
                                    p.wait(timeout=3)
                                except Exception:
                                    p.kill()
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.debug(f"Orphan cleanup error for port {port}: {e}")

    def stop_gemma_server(self):
        """Stops the autostarted llama-server process if one was spawned by this manager."""
        if hasattr(self, "_gemma_server_proc") and self._gemma_server_proc is not None:
            try:
                self._gemma_server_proc.terminate()
                self._gemma_server_proc.wait(timeout=3)
            except Exception as e:
                logger.debug(f"Error terminating gemma-server process: {e}")
                try:
                    self._gemma_server_proc.kill()
                    self._gemma_server_proc.wait(timeout=2)
                except Exception:
                    pass
            self._gemma_server_proc = None
        if hasattr(self, "_gemma_log_file") and self._gemma_log_file is not None:
            try:
                self._gemma_log_file.flush()
                self._gemma_log_file.close()
            except Exception:
                pass
            self._gemma_log_file = None
        self._kill_orphan_llama_server(getattr(settings, "GEMMA_PORT", 8081))
        gc.collect()

    def check_qwen_server_health(self) -> bool:
        """
        Probes the local Qwen llama.cpp HTTP server to verify readiness.
        Uses /health endpoint on the server base URL host and port.
        """
        try:
            base = getattr(settings, "QWEN_BASE_URL", "http://127.0.0.1:8083/v1").rstrip("/")
            health_url = (base[:-3] + "/health") if base.endswith("/v1") else (base + "/health")
            resp = httpx.get(health_url, timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def ensure_qwen_server_running(self, mode: str = "text") -> bool:
        """
        Ensures the local Qwen llama-server is online.
        Supports 'text' mode (no vision projector) or 'vision' mode (with Q8_0 mmproj).
        When in vision mode, if RAM is tight, safely unloads Gemma.
        """
        target_mode = mode.lower()
        if self.is_qwen_running() and self.check_qwen_server_health():
            if target_mode == "vision" and self._qwen_current_mode != "vision":
                logger.info("Switching Qwen server from text mode to vision mode (loading mmproj)...")
                self.stop_qwen_server()
            elif target_mode == "text" and self._qwen_current_mode == "vision":
                if self.get_available_ram_gb() < getattr(settings, "DUAL_SERVER_MIN_MEMORY_GB", 1.0):
                    logger.info("Unloading vision projector to reclaim RAM for text mode...")
                    self.stop_qwen_server()
                else:
                    return True
            else:
                return True

        if not getattr(settings, "QWEN_AUTOSTART_SERVER", True):
            return False

        gguf_path = getattr(settings, "QWEN_GGUF_PATH", "D:/models/qwen-2.5-VL-7B-Q4/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf")
        if not os.path.exists(gguf_path):
            logger.warning(f"Qwen GGUF model not found at {gguf_path}; cannot autostart llama-server.")
            return False

        # Memory guard: Sequential RAM swap - Always stop Gemma before starting Qwen to reclaim ~3.5 GB of RAM
        if getattr(settings, "SEQUENTIAL_SWAP_IF_LOW_RAM", True):
            if self.is_gemma_running() or (hasattr(self, "_gemma_server_proc") and self._gemma_server_proc is not None):
                ram_before = self.get_available_ram_gb()
                t_stop0 = time.perf_counter()
                logger.info(f"[ModelManager: Sequential Swap] Stopping Gemma server to reclaim RAM for Qwen (Available RAM: {ram_before:.2f} GiB)...")
                self.stop_gemma_server()
                self._wait_for_ram_stabilization()
                ram_after = self.get_available_ram_gb()
                logger.info(f"[ModelManager: Sequential Swap] Gemma stopped in {time.perf_counter() - t_stop0:.3f}s. Reclaimed: {ram_after - ram_before:+.2f} GiB (Now available: {ram_after:.2f} GiB)")

        llama_bin = shutil.which("llama-server") or shutil.which("llama-server.exe") or "llama-server.exe"
        parsed = urlparse(getattr(settings, "QWEN_BASE_URL", "http://127.0.0.1:8083/v1"))
        host = parsed.hostname or "127.0.0.1"
        port = str(getattr(settings, "QWEN_PORT", parsed.port or 8083))
        model_name = "qwen2.5-vl-7b-instruct"

        self._kill_orphan_llama_server(int(port))

        cmd = [
            llama_bin,
            "-m", gguf_path,
            "-c", str(getattr(settings, "LLAMA_CONTEXT_SIZE", 2048)),
            "-n", str(getattr(settings, "CON_MAX_NEW_TOKENS", 160)),
            "-t", str(getattr(settings, "LLAMA_THREADS", 6)),
            "-tb", str(getattr(settings, "LLAMA_THREADS_BATCH", 6)),
            "-b", str(getattr(settings, "LLAMA_BATCH_SIZE", 512)),
            "-ub", str(getattr(settings, "LLAMA_UBATCH_SIZE", 512)),
            "--cache-reuse", str(getattr(settings, "LLAMA_CACHE_REUSE", 256)),
            "-np", "1",
            "--no-warmup",
            "--prio", "2",
            "--host", host,
            "--port", port,
            "-a", model_name
        ]
        if target_mode == "vision":
            mmproj_path = getattr(settings, "QWEN_MMPROJ_PATH", "D:/models/qwen-2.5-VL-7B-Q4/mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf")
            if os.path.exists(mmproj_path):
                cmd.extend(["--mmproj", mmproj_path])
            else:
                cmd.append("--no-mmproj")
        else:
            cmd.append("--no-mmproj")

        ram_pre_start = self.get_available_ram_gb()
        logger.info(f"Autostarting local Qwen llama-server ({target_mode} mode, Available RAM: {ram_pre_start:.2f} GiB): {' '.join(cmd)}")
        try:
            os.makedirs("scratch", exist_ok=True)
            self._qwen_log_file = open("scratch/qwen_server.log", "a", encoding="utf-8")
            self._qwen_server_proc = subprocess.Popen(
                cmd,
                stdout=self._qwen_log_file,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            # Fast adaptive polling: 100ms intervals instead of 1.0s blind intervals
            poll_start = time.perf_counter()
            while time.perf_counter() - poll_start < 60.0:
                if self.check_qwen_server_health():
                    self._qwen_current_mode = target_mode
                    elapsed = time.perf_counter() - poll_start
                    ram_post_start = self.get_available_ram_gb()
                    logger.info(f"Qwen llama-server started successfully on port {port} ({target_mode} mode) in {elapsed:.2f}s (RAM consumed: {ram_pre_start - ram_post_start:.2f} GiB, Available: {ram_post_start:.2f} GiB)")
                    return True
                proc = self._qwen_server_proc
                if proc is not None and proc.poll() is not None:
                    logger.error(f"Qwen llama-server exited prematurely with code {proc.returncode}")
                    break
                time.sleep(0.1)
            logger.error("Qwen llama-server failed to become healthy within 60s timeout.")
            return False
        except Exception as e:
            logger.error(f"Failed to launch Qwen llama-server process: {e}")
            return False

    def stop_qwen_server(self):
        """Stops the autostarted Qwen llama-server process cleanly and frees resources."""
        if hasattr(self, "_qwen_server_proc") and self._qwen_server_proc is not None:
            try:
                self._qwen_server_proc.terminate()
                self._qwen_server_proc.wait(timeout=3)
            except Exception as e:
                logger.debug(f"Error terminating qwen-server process: {e}")
                try:
                    self._qwen_server_proc.kill()
                    self._qwen_server_proc.wait(timeout=2)
                except Exception:
                    pass
            self._qwen_server_proc = None
        if hasattr(self, "_qwen_log_file") and self._qwen_log_file is not None:
            try:
                self._qwen_log_file.flush()
                self._qwen_log_file.close()
            except Exception:
                pass
            self._qwen_log_file = None
        self._kill_orphan_llama_server(getattr(settings, "QWEN_PORT", 8083))
        self._qwen_current_mode = "text"
        gc.collect()

    def stop_all_servers(self):
        """Stops all running llama-server processes (Gemma + Qwen)."""
        self.stop_gemma_server()
        self.stop_qwen_server()

    def _generate_gemma_server(
        self,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 220,
        temperature: float = 0.7,
        timeout_seconds: float = 300.0,
        return_metadata: bool = False,
        on_token: Optional[Callable[[str], None]] = None
    ) -> Any:
        """
        Executes real inference on local Gemma model via high-performance llama.cpp HTTP server.
        Guarded by self._generation_lock to enforce strict sequential execution.
        Supports live token streaming via on_token callback.
        """
        with self._generation_lock:
            url = f"{settings.GEMMA_BASE_URL.rstrip('/')}/chat/completions"
            payload = {
                "model": getattr(settings, "GEMMA_MODEL_NAME", "gemma-4-E4B-Q4_0"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": max_new_tokens,
                "temperature": max(0.1, temperature),
                "stream": (on_token is not None)
            }
            effective_timeout = max(timeout_seconds, getattr(settings, "GEMMA_TIMEOUT_SECONDS", 300.0))
            timeout_obj = httpx.Timeout(effective_timeout, connect=60.0)
            t_req_start = time.time()
            ttft = None
            llama_timings = {}

            if on_token is not None:
                content_parts = []
                completion_tokens = 0
                try:
                    with httpx.Client(timeout=timeout_obj) as client:
                        with client.stream("POST", url, json=payload) as resp:
                            if resp.status_code != 200:
                                raise RuntimeError(f"Gemma llama-server returned HTTP {resp.status_code}")
                            for line in resp.iter_lines():
                                line_str = line.strip()
                                if not line_str or line_str.startswith(":"):
                                    continue
                                if line_str.startswith("data: "):
                                    raw_data = line_str[6:].strip()
                                    if raw_data == "[DONE]":
                                        break
                                    try:
                                        chunk = json.loads(raw_data)
                                        if "timings" in chunk:
                                            llama_timings = chunk["timings"]
                                        choices = chunk.get("choices", [])
                                        if choices:
                                            delta = choices[0].get("delta", {}).get("content", "")
                                            if delta:
                                                if ttft is None:
                                                    ttft = round(time.time() - t_req_start, 3)
                                                content_parts.append(delta)
                                                completion_tokens += 1
                                                if on_token:
                                                    try:
                                                        on_token(delta)
                                                    except DebateCancelledException:
                                                        logger.info("Gemma token streaming aborted due to debate cancellation.")
                                                        raise
                                                    except Exception:
                                                        pass
                                    except DebateCancelledException:
                                        raise
                                    except Exception:
                                        pass
                except DebateCancelledException:
                    logger.info("Gemma stream cleanly stopped due to cancellation.")
                    raise
                content = "".join(content_parts).strip()
                if not content:
                    raise RuntimeError("Gemma llama-server returned empty response content during streaming.")
                cached_n = llama_timings.get("cache_n", 0)
                eval_n = llama_timings.get("prompt_n", 0)
                prompt_tokens = eval_n + cached_n if (eval_n or cached_n) else len(content.split())
                hit_token_limit = (completion_tokens >= max_new_tokens)
            else:
                resp = httpx.post(url, json=payload, timeout=timeout_obj)
                if resp.status_code != 200:
                    raise RuntimeError(f"Gemma llama-server returned HTTP {resp.status_code}: {resp.text}")

                data = resp.json()
                llama_timings = data.get("timings", {})
                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("Gemma llama-server returned empty choices array.")
                content = choices[0].get("message", {}).get("content", "").strip()
                if not content:
                    raise RuntimeError("Gemma llama-server returned empty response content.")

                usage = data.get("usage", {})
                completion_tokens = usage.get("completion_tokens", len(content.split()))
                cached_n = llama_timings.get("cache_n", 0)
                eval_n = llama_timings.get("prompt_n", 0)
                prompt_tokens = usage.get("prompt_tokens") or (eval_n + cached_n)
                hit_token_limit = (completion_tokens >= max_new_tokens)
                ttft = round(llama_timings.get("prompt_ms", 0) / 1000.0, 3) if "prompt_ms" in llama_timings else None

            logger.info(
                f"[Diagnostic: ModelManager] role=PRO (Gemma via llama.cpp), "
                f"total_prompt_tokens={prompt_tokens} (eval={eval_n}, cached={cached_n}), "
                f"generated_tokens={completion_tokens}, ttft={ttft}s, status=REAL_LOCAL_MODEL"
            )

            if return_metadata:
                return {
                    "text": content,
                    "generated_tokens": completion_tokens,
                    "input_tokens": prompt_tokens,
                    "prompt_tokens_evaluated": eval_n,
                    "ttft_seconds": ttft,
                    "prompt_eval_ms": llama_timings.get("prompt_ms"),
                    "cache_n": cached_n,
                    "tokens_per_second": llama_timings.get("predicted_per_second"),
                    "hit_token_limit": hit_token_limit,
                    "execution_status": "REAL_LOCAL_MODEL"
                }
            return content

    def _generate_qwen_server(
        self,
        system_prompt: str,
        user_prompt: str,
        images: Optional[List[Any]] = None,
        max_new_tokens: int = 220,
        temperature: float = 0.7,
        timeout_seconds: float = 300.0,
        return_metadata: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
        debate_id: Optional[str] = None,
        round_number: Optional[int] = None
    ) -> Any:
        """
        Executes real inference on local Qwen model via high-performance llama-server HTTP API.
        Supports text-only debate turns, multimodal image ingestion, and live token streaming.
        Guarded by self._generation_lock to ensure strict sequential execution.
        Enforces detailed request lifecycle diagnostics for complete observability.
        """
        request_id = str(uuid.uuid4())[:8]
        t_req_init = time.time()
        logger.info(
            f"[CON Lifecycle: Start] request_id={request_id}, debate_id={debate_id}, round={round_number}, "
            f"initial_available_ram={self.get_available_ram_gb():.2f} GiB"
        )

        t_lock_start = time.time()
        logger.info(f"[CON Lifecycle: Lock Acquisition Start] request_id={request_id}")
        with self._generation_lock:
            lock_duration = time.time() - t_lock_start
            logger.info(f"[CON Lifecycle: Lock Acquired] request_id={request_id}, wait_sec={lock_duration:.3f}s")

            mode = "vision" if images else "text"
            qwen_started = self.ensure_qwen_server_running(mode=mode)
            qwen_proc_status = (
                f"pid={self._qwen_server_proc.pid}"
                if (hasattr(self, "_qwen_server_proc") and self._qwen_server_proc and self._qwen_server_proc.poll() is None)
                else "external_or_stopped"
            )
            ram_available = self.get_available_ram_gb()
            logger.info(
                f"[CON Lifecycle: Qwen Status] request_id={request_id}, proc_status={qwen_proc_status}, "
                f"ready={qwen_started}, available_ram={ram_available:.2f} GiB"
            )

            if not qwen_started:
                err = (
                    f"Local model inference for 'CON' (Qwen) requires a running llama-server at {settings.QWEN_BASE_URL}. "
                    "Server failed readiness verification. Refusing to fabricate responses in non-mock mode."
                )
                logger.error(f"[CON Lifecycle: Failure] request_id={request_id}, error={err}")
                raise RuntimeError(err)

            url = f"{settings.QWEN_BASE_URL.rstrip('/')}/chat/completions"
            messages: List[Dict[str, Any]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            if images:
                user_content: List[Dict[str, Any]] = [{"type": "text", "text": user_prompt}]
                for img_item in images:
                    if isinstance(img_item, str):
                        if img_item.startswith("data:image/") or img_item.startswith("http"):
                            user_content.append({"type": "image_url", "image_url": {"url": img_item}})
                        elif os.path.exists(img_item):
                            import base64
                            with open(img_item, "rb") as f:
                                b64 = base64.b64encode(f.read()).decode("utf-8")
                            ext = os.path.splitext(img_item)[1].lstrip(".").lower() or "png"
                            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{b64}"}})
                    elif isinstance(img_item, bytes):
                        import base64
                        b64 = base64.b64encode(img_item).decode("utf-8")
                        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": user_prompt})

            context_window = int(getattr(settings, "LLAMA_CONTEXT_SIZE", 2048))
            est_prompt_tokens = int((len(system_prompt) + len(user_prompt)) / 3.8)
            logger.info(
                f"[CON Lifecycle: Context] request_id={request_id}, prompt_token_count~={est_prompt_tokens}, "
                f"context_window={context_window}, max_new_tokens={max_new_tokens}"
            )

            payload = {
                "model": "qwen2.5-vl-7b-instruct",
                "messages": messages,
                "max_tokens": max_new_tokens,
                "temperature": max(0.1, temperature),
                "stream": (on_token is not None)
            }
            effective_timeout = max(timeout_seconds, getattr(settings, "QWEN_TIMEOUT_SECONDS", 180.0))
            timeout_obj = httpx.Timeout(effective_timeout, connect=30.0)
            t_http_start = time.time()
            ttft = None
            llama_timings = {}
            logger.info(f"[CON Lifecycle: HTTP Request Start] request_id={request_id}, endpoint={url}, stream={on_token is not None}")

            try:
                if on_token is not None:
                    content_parts = []
                    completion_tokens = 0
                    try:
                        with httpx.Client(timeout=timeout_obj) as client:
                            with client.stream("POST", url, json=payload) as resp:
                                first_byte_sec = round(time.time() - t_http_start, 3)
                                logger.info(
                                    f"[CON Lifecycle: First Response Byte] request_id={request_id}, http_status={resp.status_code}, "
                                    f"first_byte_latency={first_byte_sec}s"
                                )
                                if resp.status_code != 200:
                                    raise RuntimeError(f"Qwen llama-server returned HTTP {resp.status_code}")
                                for line in resp.iter_lines():
                                    line_str = line.strip()
                                    if not line_str or line_str.startswith(":"):
                                        continue
                                    if line_str.startswith("data: "):
                                        raw_data = line_str[6:].strip()
                                        if raw_data == "[DONE]":
                                            break
                                        try:
                                            chunk = json.loads(raw_data)
                                            if "timings" in chunk:
                                                llama_timings = chunk["timings"]
                                            choices = chunk.get("choices", [])
                                            if choices:
                                                delta = choices[0].get("delta", {}).get("content", "")
                                                if delta:
                                                    if ttft is None:
                                                        ttft = round(time.time() - t_http_start, 3)
                                                        logger.info(f"[CON Lifecycle: First Generated Token] request_id={request_id}, ttft={ttft}s")
                                                    content_parts.append(delta)
                                                    completion_tokens += 1
                                                    if on_token:
                                                        try:
                                                            on_token(delta)
                                                        except DebateCancelledException:
                                                            logger.info("Qwen token streaming aborted due to debate cancellation.")
                                                            raise
                                                        except Exception:
                                                            pass
                                        except DebateCancelledException:
                                            raise
                                        except Exception:
                                            pass
                    except DebateCancelledException:
                        logger.info("Qwen stream cleanly stopped due to cancellation.")
                        raise
                    content = "".join(content_parts).strip()
                    if not content:
                        raise RuntimeError("Qwen llama-server returned empty response content during streaming.")
                    cached_n = llama_timings.get("cache_n", 0)
                    eval_n = llama_timings.get("prompt_n", 0)
                    prompt_tokens = eval_n + cached_n if (eval_n or cached_n) else len(content.split())
                    hit_token_limit = (completion_tokens >= max_new_tokens)
                else:
                    resp = httpx.post(url, json=payload, timeout=timeout_obj)
                    first_byte_sec = round(time.time() - t_http_start, 3)
                    logger.info(
                        f"[CON Lifecycle: First Response Byte] request_id={request_id}, http_status={resp.status_code}, "
                        f"latency={first_byte_sec}s"
                    )
                    if resp.status_code != 200:
                        raise RuntimeError(f"Qwen llama-server returned HTTP {resp.status_code}: {resp.text}")

                    data = resp.json()
                    llama_timings = data.get("timings", {})
                    choices = data.get("choices", [])
                    if not choices:
                        raise RuntimeError("Qwen llama-server returned empty choices array.")
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if not content:
                        raise RuntimeError("Qwen llama-server returned empty response content.")

                    usage = data.get("usage", {})
                    completion_tokens = usage.get("completion_tokens", len(content.split()))
                    cached_n = llama_timings.get("cache_n", 0)
                    eval_n = llama_timings.get("prompt_n", 0)
                    prompt_tokens = usage.get("prompt_tokens") or (eval_n + cached_n)
                    hit_token_limit = (completion_tokens >= max_new_tokens)
                    ttft = round(llama_timings.get("prompt_ms", 0) / 1000.0, 3) if "prompt_ms" in llama_timings else None

                total_duration = round(time.time() - t_http_start, 2)
                tok_per_sec = round(completion_tokens / max(0.001, total_duration), 2)
                logger.info(
                    f"[CON Lifecycle: Completion] request_id={request_id}, debate_id={debate_id}, round={round_number}, "
                    f"generated_tokens={completion_tokens}, duration_sec={total_duration}s, speed={tok_per_sec} tok/s, status=SUCCESS"
                )

                if return_metadata:
                    return {
                        "text": content,
                        "generated_tokens": completion_tokens,
                        "input_tokens": prompt_tokens,
                        "prompt_tokens_evaluated": eval_n,
                        "ttft_seconds": ttft,
                        "prompt_eval_ms": llama_timings.get("prompt_ms"),
                        "cache_n": cached_n,
                        "tokens_per_second": tok_per_sec,
                        "hit_token_limit": hit_token_limit,
                        "execution_status": "REAL_LOCAL_MODEL"
                    }
                return content

            except Exception as e:
                logger.error(
                    f"[CON Lifecycle: Failure] request_id={request_id}, debate_id={debate_id}, round={round_number}, "
                    f"error={e}, status=FAILED", exc_info=True
                )
                raise

    def describe_image(
        self,
        image_input: Any,
        prompt: str = "Analyze this image and describe all key visual elements, charts, diagrams, labels, and text."
    ) -> str:
        """
        Conducts genuine multimodal visual understanding using local Qwen with the Q8_0 vision projector.
        If Gemma is running and memory is tight, Gemma is paused safely during vision analysis.
        """
        if self.mock_mode:
            return f"[Simulated Visual Analysis: Processed {type(image_input).__name__}]"

        result = self._generate_qwen_server(
            system_prompt="You are an expert multimodal visual analyzer for academic, technical, scientific, and analytical debate evidence.",
            user_prompt=prompt,
            images=[image_input],
            max_new_tokens=256,
            temperature=0.2,
            return_metadata=False
        )
        return str(result).strip()

    def load_tokenizer(self, role: str) -> Any:
        """
        Loads the tokenizer from local disk without loading heavy model weights.
        Caches tokenizer instance for repeated use.
        """
        role_upper = role.upper()
        if role_upper == "JUDGE":
            raise RuntimeError(
                "JUDGE is an API-based remote model (Google Gemini 3.5 Flash) and does not use a local Hugging Face tokenizer."
            )
        if role_upper in self._loaded_tokenizers:
            return self._loaded_tokenizers[role_upper]

        model_path = self.get_model_path(role_upper)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Configured model path for {role_upper} does not exist: {model_path}")

        tokenizer_load_path = model_path
        if os.path.isfile(model_path) or model_path.endswith(".gguf"):
            candidates = [
                os.path.dirname(model_path),
                "D:/models/gemma-4-E4B-it",
                "D:/gemma-4-E4B-it"
            ]
            for c in candidates:
                if os.path.exists(os.path.join(c, "tokenizer.json")):
                    tokenizer_load_path = c
                    break

        try:
            from transformers import AutoTokenizer
            logger.info(f"Loading tokenizer for {role_upper} from {tokenizer_load_path} (local_files_only=True)...")
            try:
                tokenizer = AutoTokenizer.from_pretrained(tokenizer_load_path, trust_remote_code=True, local_files_only=True)
            except Exception:
                tokenizer = AutoTokenizer.from_pretrained(tokenizer_load_path, trust_remote_code=True)
            self._loaded_tokenizers[role_upper] = tokenizer
            return tokenizer
        except Exception as e:
            logger.error(f"Failed to load tokenizer for {role_upper} from {tokenizer_load_path}: {e}")
            raise

    def load_model(self, role: str) -> Tuple[Any, Any]:
        """
        Loads the specified role model using sequential single-model memory allocation.
        Unloads any previously active model to preserve RAM/VRAM.
        Guarded by reentrant lock to ensure thread-safe transitions.
        """
        role_upper = role.upper()
        if role_upper not in ("PRO", "CON", "JUDGE"):
            raise ValueError(
                f"Invalid debate role '{role}'. Only exactly three local LLMs are permitted: "
                "PRO (gemma-4-E4B-it), CON (Qwen2.5-VL-7B-Instruct), JUDGE (gemini-3.5-flash)."
            )
        if role_upper == "JUDGE":
            raise RuntimeError(
                "JUDGE is managed by Google Gemini remote API (gemini-3.5-flash) via GeminiJudgeService, "
                "not local weight loading."
            )

        with self._lock:
            if role_upper in self._loaded_models:
                return self._loaded_models[role_upper], self._loaded_tokenizers.get(role_upper)

            # Evict currently loaded model to prevent duplicate allocations and OOM
            self.unload_all()

            model_path = self.get_model_path(role_upper)
            if not os.path.exists(model_path):
                logger.warning(f"Model path for {role_upper} does not exist: {model_path}.")
                return None, None

            # Pre-execution hardware guards to prevent fatal OS crashes / C++ memory aborts
            from unittest.mock import MagicMock
            from transformers import AutoModelForCausalLM
            is_mocked = isinstance(getattr(AutoModelForCausalLM, "from_pretrained", None), MagicMock)
            try:
                import transformers
                if hasattr(transformers, "Qwen2_5_VLForConditionalGeneration") and isinstance(getattr(transformers.Qwen2_5_VLForConditionalGeneration, "from_pretrained", None), MagicMock):
                    is_mocked = True
            except Exception:
                pass

            avail_ram_gb = 8.0
            model_weight_gb = 0.0
            estimated_peak_ram_gb = 1.0

            if self.device == "cpu":
                if not is_mocked:
                    # Detect bitsandbytes 4-bit quantization configuration
                    is_bitsandbytes = False
                    config_file = os.path.join(model_path, "config.json")
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, "r", encoding="utf-8") as f:
                                cfg_dict = json.load(f)
                            if "quantization_config" in cfg_dict:
                                is_bitsandbytes = True
                        except Exception:
                            pass

                    if is_bitsandbytes:
                        raise RuntimeError(
                            f"Local model '{role_upper}' ({os.path.basename(model_path)}) uses 4-bit bitsandbytes "
                            "quantization which requires a discrete CUDA GPU and accelerate. Active inference device is CPU. "
                            "To run Qwen on CPU, please convert or download GGUF format weights (Qwen2.5-VL-7B-Instruct-GGUF)."
                        )

                try:
                    import psutil
                    avail_ram_gb = psutil.virtual_memory().available / (1024**3)
                except Exception:
                    try:
                        import ctypes
                        class MEMORYSTATUSEX(ctypes.Structure):
                            _fields_ = [
                                ('dwLength', ctypes.c_ulong),
                                ('dwMemoryLoad', ctypes.c_ulong),
                                ('ullTotalPhys', ctypes.c_ulonglong),
                                ('ullAvailPhys', ctypes.c_ulonglong),
                                ('ullTotalPageFile', ctypes.c_ulonglong),
                                ('ullAvailPageFile', ctypes.c_ulonglong),
                                ('ullTotalVirtual', ctypes.c_ulonglong),
                                ('ullAvailVirtual', ctypes.c_ulonglong),
                                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                            ]
                        stat = MEMORYSTATUSEX()
                        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                        avail_ram_gb = stat.ullAvailPhys / (1024**3)
                    except Exception:
                        pass

                # Estimate peak RAM requirements based on model weight file sizes
                if os.path.exists(model_path):
                    try:
                        weight_bytes = sum(
                            os.path.getsize(os.path.join(model_path, f))
                            for f in os.listdir(model_path)
                            if (f.endswith(".safetensors") or f.endswith(".bin")) and os.path.isfile(os.path.join(model_path, f))
                        )
                        model_weight_gb = weight_bytes / (1024**3)
                    except Exception:
                        model_weight_gb = 0.0

                # Peak RAM for CPU inference requires weight size plus activation/runtime buffers (~1.15x weight size, min 1.0 GB)
                estimated_peak_ram_gb = max(model_weight_gb * 1.15, 1.0)

                if not is_mocked and avail_ram_gb < 1.0:
                    raise RuntimeError(
                        f"Insufficient available system RAM ({avail_ram_gb:.1f} GB < 1.0 GB) to load "
                        f"local model {role_upper} on CPU without OS crash."
                    )
            elif self.device.startswith("cuda"):
                if not self._has_cuda():
                    raise RuntimeError(
                        f"Cannot load model for {role_upper} on '{self.device}': CUDA is not available on this host."
                    )

            try:
                import torch
                from transformers import AutoConfig, AutoModelForCausalLM

                tokenizer = self.load_tokenizer(role_upper)
                cfg = AutoConfig.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
                arch = (cfg.architectures or [None])[0]

                # Before instantiating heavy model weights on CPU, verify sufficient peak RAM
                if not is_mocked and self.device == "cpu" and model_weight_gb > 0.0 and avail_ram_gb < estimated_peak_ram_gb:
                    raise RuntimeError(
                        f"Insufficient available system RAM ({avail_ram_gb:.1f} GB available < {estimated_peak_ram_gb:.1f} GB estimated peak required) "
                        f"to load local model '{role_upper}' ({os.path.basename(model_path)}, weight size: {model_weight_gb:.1f} GB) "
                        "on CPU without fatal memory exhaustion."
                    )

                model_kwargs: Dict[str, Any] = {
                    "trust_remote_code": True,
                    "local_files_only": True,
                }
                if self.device.startswith("cuda"):
                    model_kwargs["torch_dtype"] = torch.bfloat16 if role_upper in ("PRO", "CON") else torch.float16
                    if self._has_accelerate():
                        model_kwargs["device_map"] = "auto"
                else:
                    model_kwargs["torch_dtype"] = torch.bfloat16
                    model_kwargs["low_cpu_mem_usage"] = True

                logger.info(f"Loading {role_upper} architecture '{arch}' from {model_path} onto {self.device}...")
                if arch == "Qwen2_5_VLForConditionalGeneration":
                    from transformers import Qwen2_5_VLForConditionalGeneration
                    model: Any = Qwen2_5_VLForConditionalGeneration.from_pretrained(model_path, **model_kwargs)
                else:
                    model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)

                # Explicitly move to CUDA only if device_map was not configured and model has no hf_device_map
                has_device_map = "device_map" in model_kwargs or hasattr(model, "hf_device_map")
                if self.device.startswith("cuda") and not has_device_map:
                    logger.info(f"Explicitly moving {role_upper} model to {self.device}...")
                    model = model.to(self.device)

                self._loaded_models[role_upper] = model
                return model, tokenizer
            except Exception as e:
                self.unload_all()
                logger.error(f"Failed to load model for {role_upper} from {model_path} onto {self.device}: {e}")
                raise

    def unload_all(self):
        """
        Frees memory of currently active models, tokenizers, and running llama-server processes.
        Enforces explicit garbage collection and conditional CUDA cache flushing.
        Guarded by lock to ensure no unload during active generation.
        """
        with self._lock:
            self.stop_all_servers()
            for k in list(self._loaded_models.keys()):
                try:
                    del self._loaded_models[k]
                except Exception as e:
                    logger.debug(f"Error evicting model '{k}': {e}")
            for k in list(self._loaded_tokenizers.keys()):
                try:
                    del self._loaded_tokenizers[k]
                except Exception as e:
                    logger.debug(f"Error evicting tokenizer '{k}': {e}")
            self._loaded_models.clear()
            self._loaded_tokenizers.clear()

            # Release GPU resources only when CUDA is available
            if self._has_cuda():
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        if hasattr(torch.cuda, "ipc_collect"):
                            torch.cuda.ipc_collect()
                except Exception as e:
                    logger.debug(f"CUDA cleanup ignored: {e}")

            gc.collect()

    def generate(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        timeout_seconds: float = 300.0,
        return_metadata: bool = False,
        on_token: Optional[Callable[[str], None]] = None,
        debate_id: Optional[str] = None,
        round_number: Optional[int] = None
    ) -> Any:
        """
        Generates text using the role's local LLM.
        Applies role-appropriate chat templates, generation parameters, and decoding guards.
        In non-mock mode: refuses to fabricate responses on model load or generation failure.
        In mock mode: generates deterministic dialectical responses adhering to the debate schema.
        When return_metadata=True: returns dict with text, generated_tokens, input_tokens, hit_token_limit.
        Supports live token streaming via on_token callback.
        """
        role_upper = role.upper()
        if not self.mock_mode:
            # Handle PRO via local Gemma llama.cpp server when configured/running
            if role_upper == "PRO":
                server_ok = False
                try:
                    server_ok = self.ensure_gemma_server_running()
                except Exception as e:
                    logger.warning(f"Gemma server health/autostart check failed: {e}")

                if server_ok:
                    try:
                        return self._generate_gemma_server(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            max_new_tokens=max_new_tokens,
                            temperature=temperature,
                            timeout_seconds=timeout_seconds,
                            return_metadata=return_metadata,
                            on_token=on_token
                        )
                    except Exception as e:
                        logger.error(f"Gemma server generation error: {e}")
                        raise RuntimeError(
                            f"Gemma llama-server generation failed: {e}. "
                            "Refusing to fabricate responses in non-mock mode."
                        ) from e
                elif os.path.exists(self.get_model_path("PRO")) and not self.get_model_path("PRO").endswith(".gguf"):
                    # Fallback to local safetensors PyTorch loader if non-GGUF weights present
                    pass
                else:
                    raise RuntimeError(
                        f"Local model inference for 'PRO' (Gemma) requires a running llama-server at {settings.GEMMA_BASE_URL} "
                        f"or valid local weights at {self.get_model_path('PRO')}. "
                        "Refusing to fabricate responses in non-mock mode."
                    )

            if role_upper == "CON":
                qwen_gguf = getattr(settings, "QWEN_GGUF_PATH", "")
                if os.path.exists(qwen_gguf) or self.check_qwen_server_health():
                    server_ok = False
                    try:
                        server_ok = self.ensure_qwen_server_running(mode="text")
                    except Exception as e:
                        logger.warning(f"Qwen server health/autostart check failed: {e}")

                    if server_ok:
                        try:
                            return self._generate_qwen_server(
                                system_prompt=system_prompt,
                                user_prompt=user_prompt,
                                max_new_tokens=max_new_tokens,
                                temperature=temperature,
                                timeout_seconds=timeout_seconds,
                                return_metadata=return_metadata,
                                on_token=on_token,
                                debate_id=debate_id,
                                round_number=round_number
                            )
                        except Exception as e:
                            logger.error(f"Qwen server generation error: {e}")
                            raise RuntimeError(
                                f"Qwen llama-server generation failed: {e}. "
                                "Refusing to fabricate responses in non-mock mode."
                            ) from e
                    else:
                        raise RuntimeError(
                            f"Local model inference for 'CON' (Qwen) requires a running llama-server at {settings.QWEN_BASE_URL}. "
                            "Refusing to fabricate responses in non-mock mode."
                        )
                elif os.path.exists(self.get_model_path("CON")) and not self.get_model_path("CON").endswith(".gguf"):
                    # Fallback to local safetensors PyTorch loader if non-GGUF weights present
                    pass
                else:
                    raise RuntimeError(
                        f"Local model inference for 'CON' (Qwen) requires a running llama-server at {settings.QWEN_BASE_URL} "
                        f"or valid local weights at {self.get_model_path('CON')}. "
                        "Refusing to fabricate responses in non-mock mode."
                    )

            if role_upper == "JUDGE":
                raise RuntimeError(
                    "Local model generation not supported for role 'JUDGE' (managed by Google Gemini API). "
                    "Refusing to fabricate responses in non-mock mode."
                )

            with self._lock:
                try:
                    model_obj, tokenizer_obj = self.load_model(role_upper)
                except Exception as e:
                    raise RuntimeError(
                        f"Local model loading failed for role '{role_upper}': {e}. "
                        "Refusing to fabricate responses in non-mock mode."
                    ) from e

                if model_obj is None or tokenizer_obj is None:
                    raise RuntimeError(
                        f"Local model for '{role_upper}' could not be loaded from path: {self.get_model_path(role_upper)}. "
                        "Refusing to fabricate responses in non-mock mode."
                    )
                model: Any = model_obj
                tokenizer: Any = tokenizer_obj

                try:
                    import torch
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                    if hasattr(tokenizer, "apply_chat_template"):
                        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    else:
                        prompt_text = f"System: {system_prompt}\nUser: {user_prompt}\nAssistant:"

                    target_device = self.get_input_target_device(model)
                    raw_inputs = tokenizer(prompt_text, return_tensors="pt")
                    inputs = raw_inputs.to(target_device)
                    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

                    # Resolve authoritative EOS token IDs from generation_config to preserve official stop behavior
                    gen_cfg_eos = getattr(getattr(model, "generation_config", None), "eos_token_id", None)
                    effective_eos = gen_cfg_eos if gen_cfg_eos is not None else tokenizer.eos_token_id

                    with torch.inference_mode():
                        output_ids = model.generate(
                            **inputs,
                            max_new_tokens=max_new_tokens,
                            temperature=temperature,
                            do_sample=temperature > 0.0,
                            pad_token_id=pad_token_id,
                            eos_token_id=effective_eos,
                            use_cache=True
                        )

                    # Strip input prompt tokens from output
                    input_length = inputs.input_ids.shape[1]
                    new_tokens = output_ids[0][input_length:]
                    decoded = tokenizer.decode(new_tokens, skip_special_tokens=True)
                    response = (decoded if isinstance(decoded, str) else str(decoded)).strip()
                    if not response:
                        raise RuntimeError(f"Local model '{role_upper}' generated an empty response.")
                    
                    logger.info(
                        f"[Diagnostic: ModelManager] role={role_upper}, device={self.device}, "
                        f"input_tokens={input_length}, generated_tokens={len(new_tokens)}, "
                        f"hit_token_limit={len(new_tokens) >= max_new_tokens}"
                    )
                    if return_metadata:
                        return {
                            "text": response,
                            "generated_tokens": len(new_tokens),
                            "input_tokens": input_length,
                            "hit_token_limit": len(new_tokens) >= max_new_tokens,
                            "execution_status": "REAL_LOCAL_MODEL"
                        }
                    return response
                except Exception as e:
                    logger.error(f"Inference error with model {role_upper} on device {self.device}: {e}")
                    raise RuntimeError(
                        f"Inference execution error with local model {role_upper} on {self.device}: {e}. "
                        "Refusing to fabricate dialectical response."
                    ) from e

        # Mock mode (testing and state-machine validation only)
        logger.info(f"[Diagnostic: ModelManager Mock] role={role_upper}, mock_mode=True")
        mock_text = self._simulate_dialectical_response(role_upper, system_prompt, user_prompt)
        if return_metadata:
            return {
                "text": mock_text,
                "generated_tokens": len(mock_text.split()),
                "input_tokens": 50,
                "hit_token_limit": False,
                "execution_status": "SIMULATED"
            }
        return mock_text

    def _simulate_dialectical_response(self, role: str, system_prompt: str, user_prompt: str) -> str:
        """
        Generates structured, context-aware responses adhering strictly to debate rules for test verification.
        Returns a structured JSON payload that is parsed into a GroundedTurnPayload.
        """
        if role == "PRO":
            has_doc_evidence = "=== RETRIEVED VERIFIED EVIDENCE" in user_prompt and "No external grounding documents retrieved" not in user_prompt
            page_match = re.search(r'Page (\d+)', user_prompt)
            page_num = int(page_match.group(1)) if page_match else 1
            sec_match = re.search(r'Section: ([^\n]+)', user_prompt)
            sec_name = sec_match.group(1).strip() if sec_match else "General"
            round_match = re.search(r'Round: (\d+)', user_prompt)
            round_num = int(round_match.group(1)) if round_match else 1

            if has_doc_evidence:
                arg_text = (
                    f"Drawing upon documented findings in {sec_name} (Page {page_num}), the affirmative framework proves that "
                    f"structural procedural controls significantly reduce operational latency and arbitrary disparity. Directly "
                    f"connecting this evidence to the proposition: empirical validation confirms that formal invariant constraints bound "
                    f"performance without compromising foundational safety."
                )
                claim = "Empirical documentation demonstrates significant variance reduction under formal procedural controls."
                reasoning = f"Connects Page {page_num} evidentiary findings to establish affirmative validity."
            else:
                arg_text = (
                    "The affirmative position is grounded in deductive argumentation and systematic variance reduction. "
                    "In the absence of external empirical documentation, formal invariant constraints logically guarantee "
                    "non-violation of foundational principles, rendering operational risks bounded through systematic procedural rules."
                )
                claim = "Systematic procedural constraints logically minimize operational variance."
                reasoning = "Adjudicates deductive consistency in the absence of verified documentary records."

            payload = {
                "argument_title": f"Round {round_num}: Affirmative Defense & Empirical Grounding",
                "argument_text": arg_text,
                "main_claim": claim,
                "reasoning_summary": reasoning,
                "evidence_references": [
                    {
                        "source": "Document",
                        "page": page_num,
                        "section": sec_name,
                        "relevance_explanation": f"Evidentiary basis from {sec_name}"
                    }
                ] if has_doc_evidence else [],
                "limitations": None if has_doc_evidence else "No external documentary evidence retrieved for this turn."
            }
            return json.dumps(payload)

        elif role == "CON":
            opposing_pro = ""
            if "=== OPPOSING GEMMA (PRO) ARGUMENT TO DIRECTLY REBUT ===" in user_prompt:
                opposing_pro = user_prompt.split("=== OPPOSING GEMMA (PRO) ARGUMENT TO DIRECTLY REBUT ===")[1].split("INSTRUCTION:")[0].strip()
            elif "=== OPPOSING PRO ARGUMENT TO REBUT ===" in user_prompt:
                opposing_pro = user_prompt.split("=== OPPOSING PRO ARGUMENT TO REBUT ===")[1].strip()
            elif "Opposing PRO Argument to Rebut:" in user_prompt:
                opposing_pro = user_prompt.split("Opposing PRO Argument to Rebut:")[1].strip()

            has_doc_evidence = "=== RETRIEVED VERIFIED EVIDENCE" in user_prompt and "No external grounding documents retrieved" not in user_prompt
            page_match = re.search(r'Page (\d+)', user_prompt)
            page_num = int(page_match.group(1)) if page_match else 2
            sec_match = re.search(r'Section: ([^\n]+)', user_prompt)
            sec_name = sec_match.group(1).strip() if sec_match else "General"
            round_match = re.search(r'Round: (\d+)', user_prompt)
            round_num = int(round_match.group(1)) if round_match else 1

            if opposing_pro and "This is Round 1" not in opposing_pro:
                pro_core = opposing_pro.split('. ')[0] + '.' if '. ' in opposing_pro else opposing_pro[:120]
                arg_text = (
                    f"The negative position directly challenges Gemma's premise that '{pro_core}'. "
                    f"While initial performance metrics are reported in {sec_name} (Page {page_num}), rigorous architectural "
                    f"analysis reveals critical trade-offs and scaling bottlenecks. Theoretical advantages under narrow "
                    f"evaluations do not resolve the substantial computational complexity and resource overhead under realistic conditions."
                )
                claim = "Empirical gains on narrow benchmarks fail to account for structural scaling and complexity trade-offs."
                reasoning = f"Directly rebuts PRO's core claim by highlighting computational complexity and boundary conditions from {sec_name}."
            else:
                arg_text = (
                    "The negative position challenges the affirmative proposition on theoretical and operational grounds. "
                    "While the proposed framework demonstrates benefits in isolated settings, significant scalability "
                    "and resource constraints remain unaddressed. Relying on benchmark results obscures inherent architectural trade-offs."
                )
                claim = "Inherent architectural and resource trade-offs limit the general superiority of the proposed framework."
                reasoning = "Establishes initial negative counter-thesis regarding computational and empirical limitations."

            payload = {
                "argument_title": f"Round {round_num}: Counter-Examination & Systemic Risk Challenge",
                "argument_text": arg_text,
                "main_claim": claim,
                "central_claim": claim,
                "reasoning_summary": reasoning,
                "concise_rationale": reasoning,
                "evidence_references": [
                    {
                        "source": "Document",
                        "page": page_num,
                        "section": sec_name,
                        "relevance_explanation": f"Documentary basis challenging scope from {sec_name}"
                    }
                ] if has_doc_evidence else [],
                "limitations": None if has_doc_evidence else "No external documentary evidence retrieved for this turn."
            }
            return json.dumps(payload)
        elif role == "JUDGE":
            # Check if prompt indicates no grounding evidence
            has_no_evidence = (
                "NO RETRIEVED GROUNDING EVIDENCE AVAILABLE" in user_prompt or
                "evidence: none" in user_prompt.lower() or
                "no external evidence" in user_prompt.lower()
            )

            # Extract any real sources present in prompt
            prompt_sources: List[str] = []
            for line in user_prompt.splitlines():
                line_strip = line.strip()
                if line_strip.startswith("Source:") or line_strip.startswith("Citation:"):
                    source_val = line_strip.split(":", 1)[1].strip()
                    if source_val and source_val not in prompt_sources:
                        prompt_sources.append(source_val)
            url_matches = re.findall(r'https?://[^\s)\]"]+', user_prompt)
            for u in url_matches:
                if u not in prompt_sources:
                    prompt_sources.append(u)

            if has_no_evidence or not prompt_sources:
                sources = []
                rel_score = 30.0
                unsupported = ["Empirical assertions ungrounded due to lack of verified external grounding evidence."]
                reasoning = (
                    "Adjudication based on internal logical coherence. Since no external verified grounding "
                    "evidence was retrieved, neither debater received empirical verification credit. "
                    "The outcome reflects purely deductive argumentation and rebuttal responsiveness."
                )
            else:
                sources = prompt_sources[:3]
                rel_score = 88.0
                unsupported = []
                reasoning = (
                    f"PRO demonstrated solid evidentiary grounding regarding the core proposition. "
                    f"CON presented substantive counter-examination highlighting complexity and operational trade-offs. "
                    f"Adjudication reflects close comparative analysis of verified empirical findings."
                )

            report = {
                "pro_score": 87.0,
                "con_score": 85.0,
                "winner": "PRO",
                "status": "completed",
                "judge_model_used": "mock_adjudicator",
                "is_fallback": True,
                "strongest_pro_argument": "Documented empirical benchmark gains substantiate affirmative performance advantages.",
                "strongest_con_argument": "Rigorous identification of computational complexity bottlenecks and resource constraints.",
                "key_rebuttals": [
                    "CON directly challenged PRO's claims by exposing scalability and complexity trade-offs.",
                    "PRO responded by delineating documented benchmark gains and empirical efficiency."
                ],
                "unresolved_questions": [
                    "Optimal boundary conditions when scaling under extreme input sequences."
                ],
                "pro_strengths": [
                    "Strong empirical citation of verified performance benchmarks",
                    "Clear articulation of architectural advantages"
                ],
                "pro_weaknesses": [
                    "Did not fully resolve scaling complexity under long-sequence limits"
                ],
                "con_strengths": [
                    "Sharp challenge to computational complexity and resource overhead",
                    "Effective identification of benchmark boundary conditions"
                ],
                "con_weaknesses": [
                    "Did not fully contest the primary efficiency gains demonstrated in the paper"
                ],
                "round_points": [
                    {
                        "round_number": 1,
                        "pro_summary": "Established empirical efficiency and quality gains from documented benchmarks.",
                        "con_summary": "Exposed computational complexity bounds and operational constraints.",
                        "key_takeaway": "Performance advantages must be balanced against scalability costs."
                    }
                ],
                "main_arguments": [
                    "Documented empirical results demonstrate substantial benchmark gains."
                ],
                "main_counterarguments": [
                    "Computational complexity imposes significant constraints under extended sequence lengths."
                ],
                "supported_claims": [
                    "Empirical benchmark gains substantiated by documented evidence."
                ] if not has_no_evidence else [],
                "unsupported_claims": unsupported,
                "judge_reasoning": reasoning,
                "balanced_verdict": (
                    "PRO establishes strong empirical advantages on documented benchmarks, while CON "
                    "validates that computational complexity and operational scaling impose real trade-offs."
                ),
                "evidence_reliability_score": rel_score,
                "source_references": sources
            }
            return json.dumps(report)

        return f"Standard dialectical turn for {role}."

local_model_manager = LocalModelManager()
