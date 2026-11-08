import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "AI Debate Simulator"
    
    # Database
    DATABASE_URL: str = Field(
        default=os.getenv("DATABASE_URL", "sqlite:///./debate_simulator.db"),
        description="Database connection string. PostgreSQL is authoritative in production; SQLite is permitted only when explicitly configured for local development or testing."
    )
    
    # Qdrant Vector DB
    QDRANT_URL: str = Field(
        default=os.getenv("QDRANT_URL", ""),
        description="Optional remote Qdrant URL"
    )
    QDRANT_API_KEY: str = Field(
        default=os.getenv("QDRANT_API_KEY", ""),
        description="Optional Qdrant API Key"
    )
    QDRANT_STORAGE_PATH: str = Field(
        default=os.getenv("QDRANT_STORAGE_PATH", "./qdrant_data"),
        description="Local disk storage path for Qdrant client"
    )
    QDRANT_COLLECTION_NAME: str = "debate_knowledge"
    QDRANT_PORT: Optional[int] = Field(
        default=int(os.getenv("QDRANT_PORT")) if os.getenv("QDRANT_PORT") else None,
        description="Optional Qdrant port (defaults to 443 for https, 6333 for http)"
    )
    QDRANT_TIMEOUT: float = Field(
        default=float(os.getenv("QDRANT_TIMEOUT", "15.0")),
        description="Network timeout in seconds for remote Qdrant operations"
    )
    
    # Embeddings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    
    # =========================================================================
    # EXACT THREE STANDARDIZED MODELS CONFIGURATION
    # =========================================================================

    # MODEL 1: PRO AGENT — Google Gemma 4 E4B Instruct (Q4_0 GGUF via llama.cpp)
    GEMMA_MODEL_PATH: str = Field(
        default=os.getenv("GEMMA_MODEL_PATH", "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf"),
        description="Local path to Gemma Q4_0 GGUF weights"
    )
    GEMMA_BASE_URL: str = Field(
        default=os.getenv("GEMMA_BASE_URL", "http://127.0.0.1:8081/v1"),
        description="Base URL for local Gemma llama-server OpenAI-compatible API"
    )
    GEMMA_MODEL_NAME: str = Field(
        default=os.getenv("GEMMA_MODEL_NAME", "gemma-4-E4B-Q4_0"),
        description="Model identifier exposed by Gemma llama-server"
    )
    GEMMA_TIMEOUT_SECONDS: float = Field(
        default=float(os.getenv("GEMMA_TIMEOUT_SECONDS", "300.0")),
        description="Timeout in seconds for Gemma API requests"
    )
    GEMMA_AUTOSTART_SERVER: bool = Field(
        default=os.getenv("GEMMA_AUTOSTART_SERVER", "true").lower() in ("true", "1", "yes"),
        description="Whether to automatically launch llama-server for Gemma if not already running"
    )
    PRO_MODEL_PATH: str = Field(
        default=os.getenv("PRO_MODEL_PATH", os.getenv("GEMMA_MODEL_PATH", "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf")),
        description="Local filesystem path for PRO Gemma Q4_0 GGUF model"
    )

    # MODEL 2: CON AGENT — Alibaba Qwen2.5-VL-7B-Instruct
    QWEN_MODEL_PATH: str = Field(
        default=os.getenv("QWEN_MODEL_PATH", "D:/models/Qwen2.5-VL-7B-Instruct"),
        description="Local path to Qwen model"
    )
    QWEN_GGUF_PATH: str = Field(
        default=os.getenv("QWEN_GGUF_PATH", "D:/models/qwen-2.5-VL-7B-Q4/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf"),
        description="Local path to Qwen2.5-VL-7B Q4_K_M GGUF model for CPU inference via llama.cpp"
    )
    QWEN_MMPROJ_PATH: str = Field(
        default=os.getenv("QWEN_MMPROJ_PATH", "D:/models/qwen-2.5-VL-7B-Q4/mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf"),
        description="Local path to Qwen2.5-VL-7B Q8_0 multimodal vision projector GGUF"
    )
    QWEN_BASE_URL: str = Field(
        default=os.getenv("QWEN_BASE_URL", "http://127.0.0.1:8083/v1"),
        description="Base URL for local Qwen llama-server OpenAI-compatible API"
    )
    QWEN_PORT: int = Field(
        default=int(os.getenv("QWEN_PORT", "8083")),
        description="Local port for Qwen llama-server"
    )
    QWEN_AUTOSTART_SERVER: bool = Field(
        default=os.getenv("QWEN_AUTOSTART_SERVER", "true").lower() in ("true", "1", "yes"),
        description="Whether to automatically launch llama-server for Qwen if not already running"
    )
    QWEN_MODEL_NAME: str = Field(
        default=os.getenv("QWEN_MODEL_NAME", "Qwen2.5-VL-7B-Instruct"),
        description="Model identifier for Qwen CON debater"
    )
    QWEN_TIMEOUT_SECONDS: float = Field(
        default=float(os.getenv("QWEN_TIMEOUT_SECONDS", "300.0")),
        description="Timeout in seconds for Qwen API requests"
    )
    CON_MODEL_PATH: str = Field(
        default=os.getenv("CON_MODEL_PATH", "D:/models/Qwen2.5-VL-7B-Instruct"),
        description="Local path to CON LLM"
    )
    
    # Hybrid Dual-Server Memory Management
    DUAL_SERVER_MIN_MEMORY_GB: float = Field(
        default=float(os.getenv("DUAL_SERVER_MIN_MEMORY_GB", "1.0")),
        description="Minimum available host RAM (GiB) required to keep both servers resident"
    )
    CRITICAL_MEMORY_ABORT_GB: float = Field(
        default=float(os.getenv("CRITICAL_MEMORY_ABORT_GB", "0.5")),
        description="Critical memory threshold (GiB) to abort and evict servers safely"
    )
    SEQUENTIAL_SWAP_IF_LOW_RAM: bool = Field(
        default=os.getenv("SEQUENTIAL_SWAP_IF_LOW_RAM", "true").lower() in ("true", "1", "yes"),
        description="Whether to sequentially unload inactive server when RAM is constrained"
    )

    # =========================================================================
    # MODEL 3: JUDGE AGENT PROVIDERS (Google Gemini & NVIDIA NIM)
    # =========================================================================
    JUDGE_PROVIDER: str = Field(
        default=os.getenv("JUDGE_PROVIDER", "nvidia").strip().lower(),
        description="Active default Judge provider: 'nvidia' or 'gemini'"
    )

    # Provider 1: Google Gemini (Remote API)
    GEMINI_API_KEY: str = Field(
        default=os.getenv("GEMINI_API_KEY", ""),
        description="Google AI Studio Gemini API Key for Judge model"
    )
    GEMINI_MODEL_ID: str = Field(
        default=os.getenv("GEMINI_MODEL_ID", "gemini-3.5-flash"),
        description="Gemini model identifier for Judge adjudication"
    )
    GEMINI_TIMEOUT_SECONDS: float = Field(
        default=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "120.0")),
        description="Timeout in seconds for Gemini API requests"
    )
    GEMINI_MAX_RETRIES: int = Field(
        default=int(os.getenv("GEMINI_MAX_RETRIES", "3")),
        description="Maximum retry attempts for transient Gemini API errors"
    )

    # Provider 2: NVIDIA NIM API (Remote API)
    NVIDIA_API_KEY: str = Field(
        default=os.getenv("NVIDIA_API_KEY", ""),
        description="NVIDIA NIM API Key for Judge model"
    )
    NVIDIA_BASE_URL: str = Field(
        default=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        description="Base URL for NVIDIA NIM OpenAI-compatible API"
    )
    NVIDIA_JUDGE_MODEL: str = Field(
        default=os.getenv("NVIDIA_JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"),
        description="NVIDIA model identifier for Judge adjudication"
    )
    NVIDIA_TIMEOUT_SECONDS: float = Field(
        default=float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "60.0")),
        description="Timeout in seconds for NVIDIA NIM API requests"
    )
    NVIDIA_MAX_TOKENS: int = Field(
        default=int(os.getenv("NVIDIA_MAX_TOKENS", "8192")),
        description="Maximum tokens budget for NVIDIA NIM generation (including reasoning tokens)"
    )
    NVIDIA_MAX_RETRIES: int = Field(
        default=int(os.getenv("NVIDIA_MAX_RETRIES", "1")),
        description="Maximum retry attempts for transient NVIDIA NIM API errors"
    )
    
    # Local LLM Execution Profile
    ENABLE_LOCAL_LLM_INFERENCE: bool = Field(
        default=os.getenv("ENABLE_LOCAL_LLM_INFERENCE", "false").lower() in ("true", "1", "yes"),
        description="Whether to attempt real local PyTorch weights inference when hardware supports it"
    )
    INFERENCE_DEVICE: str = Field(
        default=os.getenv("INFERENCE_DEVICE", "cpu").strip().lower(),
        description="Target compute device for local model inference: 'cpu' (default), 'cuda', or 'auto'."
    )
    
    # General Debate Configuration
    DEFAULT_ROUNDS: int = 2
    MAX_ROUNDS: int = 5
    TOP_K_EVIDENCE: int = int(os.getenv("TOP_K_EVIDENCE", "3"))
    CON_MAX_NEW_TOKENS: int = Field(
        default=int(os.getenv("CON_MAX_NEW_TOKENS", "160")),
        description="Configurable max generation tokens for CON agent to optimize response time on CPU"
    )
    PRO_MAX_NEW_TOKENS: int = Field(
        default=int(os.getenv("PRO_MAX_NEW_TOKENS", "160")),
        description="Configurable max generation tokens for PRO agent"
    )
    LLAMA_CONTEXT_SIZE: int = Field(
        default=int(os.getenv("LLAMA_CONTEXT_SIZE", "2048")),
        description="Configurable context window size for local llama-server instances"
    )
    LLAMA_THREADS: int = Field(
        default=int(os.getenv("LLAMA_THREADS", "6")),
        description="Optimal autoregressive inference threads (6 threads on Intel i5-13500H to maximize throughput and avoid barrier stalls)"
    )
    LLAMA_THREADS_BATCH: int = Field(
        default=int(os.getenv("LLAMA_THREADS_BATCH", "6")),
        description="Optimal prompt evaluation batch threads (6 threads for peak 182.6 t/s prefill on Intel i5-13500H)"
    )
    LLAMA_BATCH_SIZE: int = Field(
        default=int(os.getenv("LLAMA_BATCH_SIZE", "512")),
        description="llama-server batch size"
    )
    LLAMA_UBATCH_SIZE: int = Field(
        default=int(os.getenv("LLAMA_UBATCH_SIZE", "512")),
        description="llama-server micro-batch size"
    )
    LLAMA_CACHE_REUSE: int = Field(
        default=int(os.getenv("LLAMA_CACHE_REUSE", "256")),
        description="KV cache reuse threshold"
    )
    
    # Intelligent Debate Context Management Settings
    PRO_CONTEXT_BUDGET_TOKENS: int = Field(
        default=int(os.getenv("PRO_CONTEXT_BUDGET_TOKENS", "900")),
        description="Maximum prompt context budget in tokens for PRO model"
    )
    CON_CONTEXT_BUDGET_TOKENS: int = Field(
        default=int(os.getenv("CON_CONTEXT_BUDGET_TOKENS", "1000")),
        description="Maximum prompt context budget in tokens for CON model"
    )
    ENABLE_PREFIX_CACHE_ALIGNMENT: bool = Field(
        default=os.getenv("ENABLE_PREFIX_CACHE_ALIGNMENT", "true").lower() == "true",
        description="Align static invariant prompt prefix first to maximize llama.cpp KV cache reuse"
    )
    ENABLE_ROLLING_DEBATE_SUMMARY: bool = Field(
        default=os.getenv("ENABLE_ROLLING_DEBATE_SUMMARY", "true").lower() == "true",
        description="Maintain compact rolling summary across rounds instead of raw transcript accumulation"
    )
    
    # Web Search & Multi-PDF Research Configuration
    SEARCH_PROVIDER: str = Field(
        default=os.getenv("SEARCH_PROVIDER", "duckduckgo"),
        description="Web search provider: duckduckgo, tavily, serpapi, or mock"
    )
    SEARCH_API_KEY: str = Field(
        default=os.getenv("SEARCH_API_KEY", ""),
        description="API key for external search provider if configured"
    )
    MAX_RESEARCH_PDFS: int = Field(
        default=int(os.getenv("MAX_RESEARCH_PDFS", "4")),
        description="Maximum number of research PDFs to download and extract per research request"
    )
    MAX_CONCURRENT_PDF_DOWNLOADS: int = Field(
        default=int(os.getenv("MAX_CONCURRENT_PDF_DOWNLOADS", "2")),
        description="Maximum concurrent PDF downloads per research request"
    )
    MAX_PDF_SIZE_BYTES: int = Field(
        default=int(os.getenv("MAX_PDF_SIZE_BYTES", str(20 * 1024 * 1024))),
        description="Maximum allowed size per individual research PDF in bytes (default: 20 MB)"
    )
    PDF_DOWNLOAD_TIMEOUT_SECONDS: float = Field(
        default=float(os.getenv("PDF_DOWNLOAD_TIMEOUT_SECONDS", "25.0")),
        description="Timeout in seconds for downloading research PDFs"
    )
    MAX_TOTAL_RESEARCH_BYTES: int = Field(
        default=int(os.getenv("MAX_TOTAL_RESEARCH_BYTES", str(60 * 1024 * 1024))),
        description="Maximum total bytes allowed across all research downloads per request (default: 60 MB)"
    )
    MAX_PDF_PAGES_TO_EXTRACT: int = Field(
        default=int(os.getenv("MAX_PDF_PAGES_TO_EXTRACT", "30")),
        description="Maximum number of pages to extract per research PDF"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    model_config = SettingsConfigDict(
        env_file=[
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")),
            "backend/.env",
            ".env",
        ],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
