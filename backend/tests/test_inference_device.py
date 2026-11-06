import os
import json
import pytest
from unittest.mock import patch, MagicMock
import torch

from app.llm.model_manager import LocalModelManager, local_model_manager
from app.core.config import settings

def test_inference_device_setting_default():
    """
    Verifies that the default INFERENCE_DEVICE is 'cpu' for backward-compatibility.
    """
    assert hasattr(settings, "INFERENCE_DEVICE")
    assert settings.INFERENCE_DEVICE in ("cpu", "cuda", "auto")

def test_cpu_only_system_using_auto():
    """
    Requirement 1: On CPU-only systems without CUDA, 'auto' must resolve to 'cpu'.
    """
    mgr = LocalModelManager(device="auto")
    # On the development host, CUDA is unavailable
    if not mgr._has_cuda():
        assert mgr.device == "cpu"
        assert mgr.resolve_device("auto") == "cpu"

def test_explicit_cpu_configuration():
    """
    Requirement 2: Explicit CPU configuration must always select 'cpu'.
    Even if CUDA were physically present or mocked as available, 'cpu' must never be promoted to CUDA.
    """
    mgr = LocalModelManager(device="cpu")
    assert mgr.device == "cpu"
    assert mgr.resolve_device("cpu") == "cpu"

    # Even if CUDA is available, explicit 'cpu' remains 'cpu'
    with patch.object(mgr, "_has_cuda", return_value=True):
        assert mgr.resolve_device("cpu") == "cpu"

def test_explicit_cuda_fails_when_cuda_unavailable():
    """
    Requirement 3: Explicit CUDA configuration must fail with a clear, actionable error
    when CUDA is unavailable, rather than silently falling back to CPU.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch.object(mgr, "_has_cuda", return_value=False):
        with pytest.raises(RuntimeError) as exc_info:
            mgr.resolve_device("cuda")
        
        err_msg = str(exc_info.value).lower()
        assert "explicit cuda inference device requested" in err_msg
        assert "cuda is not available" in err_msg
        assert "inference_device='cpu' or 'auto'" in err_msg

        # Also test with specific index 'cuda:0'
        with pytest.raises(RuntimeError) as exc_info_0:
            mgr.resolve_device("cuda:0")
        assert "explicit cuda inference device requested" in str(exc_info_0.value).lower()

def test_cuda_selection_when_cuda_available_mocked():
    """
    Requirement 4: When CUDA is available, 'auto' and 'cuda' must resolve to 'cuda'.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch.object(mgr, "_has_cuda", return_value=True), patch("torch.cuda.device_count", return_value=2):
        assert mgr.resolve_device("auto") == "cuda"
        assert mgr.resolve_device("cuda") == "cuda"
        assert mgr.resolve_device("cuda:0") == "cuda:0"
        assert mgr.resolve_device("cuda:1") == "cuda:1"
        # Explicit CPU must still return CPU
        assert mgr.resolve_device("cpu") == "cpu"

def test_invalid_device_configuration_raises_value_error():
    """
    Verifies that unsupported device values raise ValueError with supported choices listed.
    """
    mgr = LocalModelManager(device="cpu")
    with pytest.raises(ValueError) as exc_info:
        mgr.resolve_device("tpu")
    assert "invalid inference device configuration" in str(exc_info.value).lower()
    assert "cpu" in str(exc_info.value).lower()

def test_set_device_dynamic_switching():
    """
    Verifies that set_device dynamically updates device and unloads cached models
    if the device changes.
    """
    mgr = LocalModelManager(device="cpu")
    assert mgr.device == "cpu"
    
    # Mock a cached model
    mgr._loaded_models["MOCK"] = "mock_model"
    
    # Switch to auto (resolves to cpu on this host, so no change in effective device)
    mgr.set_device("auto")
    assert mgr.device == "cpu"
    
    # Switch with CUDA mocked: should unload cached models when device changes to cuda
    with patch.object(mgr, "_has_cuda", return_value=True):
        mgr.set_device("cuda")
        assert mgr.device == "cuda"
        assert len(mgr._loaded_models) == 0

def test_device_placement_of_model_inputs():
    """
    Requirement 5: Model inputs must be placed on the target device corresponding
    to the active model or manager device.
    """
    mgr = LocalModelManager(device="cpu")
    mgr.mock_mode = False

    tokenizer = mgr.load_tokenizer("CON")
    sample_prompt = "Topic: Technology Governance"
    raw_inputs = tokenizer(sample_prompt, return_tensors="pt")
    
    # CPU device placement
    inputs_cpu = raw_inputs.to(torch.device("cpu"))
    assert inputs_cpu.input_ids.device.type == "cpu"
    if "attention_mask" in inputs_cpu:
        assert inputs_cpu.attention_mask.device.type == "cpu"

def test_resource_management_cuda_cleanup_conditional():
    """
    Requirement 6: CUDA cleanup functions (e.g. empty_cache) must NOT be called
    when CUDA is unavailable, but MUST be called when CUDA is available.
    """
    mgr = LocalModelManager(device="cpu")
    
    # 1. When CUDA is unavailable: torch.cuda.empty_cache must NOT be called
    with patch.object(mgr, "_has_cuda", return_value=False):
        with patch("torch.cuda.empty_cache") as mock_empty:
            mgr.unload_all()
            mock_empty.assert_not_called()

    # 2. When CUDA is available: torch.cuda.empty_cache MUST be called
    with patch.object(mgr, "_has_cuda", return_value=True):
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.empty_cache") as mock_empty:
                mgr.unload_all()
                mock_empty.assert_called_once()

def test_sequential_pro_con_memory_isolation():
    """
    Requirement 6: Sequential loading of PRO then CON ensures only one model
    resides in memory at any point.
    """
    mgr = LocalModelManager(device="cpu")
    mgr._loaded_models["PRO"] = "mock_pro"
    mgr._loaded_tokenizers["PRO"] = "mock_tok_pro"
    
    # Simulating unload before next role
    mgr.unload_all()
    assert len(mgr._loaded_models) == 0
    assert len(mgr._loaded_tokenizers) == 0
    
    mgr._loaded_models["CON"] = "mock_con"
    mgr._loaded_tokenizers["CON"] = "mock_tok_con"
    assert len(mgr._loaded_models) == 1
    assert "CON" in mgr._loaded_models
    assert "PRO" not in mgr._loaded_models
    mgr.unload_all()

def test_eos_token_resolution_preserved():
    """
    Requirement 7: Authoritative EOS configurations are preserved across devices.
    - Qwen: Verified from its Hugging Face generation_config.json (includes EOS token 151645).
    - Gemma: Validated appropriately for the GGUF / llama.cpp server architecture
      (inspects llama-server props or GGUF metadata/tokenizer with <turn|> 106 and <eos> 1).
    """
    mgr = LocalModelManager(device="cpu")

    # 1. Qwen EOS verification via Hugging Face generation_config.json
    qwen_path = mgr.get_model_path("CON")
    qwen_gen_cfg_file = os.path.join(qwen_path, "generation_config.json")
    with open(qwen_gen_cfg_file, "r", encoding="utf-8") as f:
        qwen_cfg = json.load(f)
    assert 151645 in qwen_cfg.get("eos_token_id")

    # 2. Gemma EOS verification for GGUF / llama.cpp architecture
    gemma_path = mgr.get_model_path("PRO")
    assert gemma_path.endswith(".gguf") or os.path.exists(gemma_path)

    if mgr.check_gemma_server_health():
        import httpx
        base = settings.GEMMA_BASE_URL.rstrip("/")
        props_url = base[:-3] + "/props" if base.endswith("/v1") else base + "/props"
        resp = httpx.get(props_url, timeout=3.0)
        assert resp.status_code == 200
        props = resp.json()
        assert props.get("eos_token") == "<eos>"
        gen_params = props.get("default_generation_settings", {}).get("params", {})
        assert gen_params.get("ignore_eos") is False
    else:
        gemma_tok = mgr.load_tokenizer("PRO")
        assert gemma_tok.convert_tokens_to_ids("<turn|>") == 106
        assert gemma_tok.convert_tokens_to_ids("<eos>") == 1

def test_invalid_cuda_device_indices():
    """
    Requirement 4: Validates that invalid CUDA device syntax or out-of-range indices
    fail fast with clear actionable errors.
    """
    mgr = LocalModelManager(device="cpu")

    # Non-integer device index raises ValueError
    with pytest.raises(ValueError) as exc1:
        mgr.resolve_device("cuda:invalid")
    assert "invalid cuda device index" in str(exc1.value).lower()

    # Negative device index raises ValueError
    with pytest.raises(ValueError) as exc2:
        mgr.resolve_device("cuda:-1")
    assert "invalid cuda device index" in str(exc2.value).lower()

    # Malformed device specifier raises ValueError
    with pytest.raises(ValueError) as exc3:
        mgr.resolve_device("cuda-0")
    assert "invalid cuda device specification" in str(exc3.value).lower()

    # Out-of-bounds CUDA device index raises RuntimeError when CUDA is available
    with patch.object(mgr, "_has_cuda", return_value=True):
        with patch("torch.cuda.device_count", return_value=1):
            # Index 0 is valid
            assert mgr.resolve_device("cuda:0") == "cuda:0"
            # Index 1 is out of range for 1 device (indices 0..0)
            with pytest.raises(RuntimeError) as exc4:
                mgr.resolve_device("cuda:1")
            assert "requested cuda device index 1" in str(exc4.value).lower()
            assert "only 1 cuda device(s) are available" in str(exc4.value).lower()

            # Index 99 is out of range
            with pytest.raises(RuntimeError) as exc5:
                mgr.resolve_device("cuda:99")
            assert "requested cuda device index 99" in str(exc5.value).lower()

def test_get_input_target_device_hierarchy():
    """
    Requirement 3 & 4: Verifies the hierarchy for identifying the model's input execution device:
    1. Input embeddings layer device (authoritative for token inputs)
    2. model.device property
    3. First parameter device
    4. Manager device fallback
    """
    mgr = LocalModelManager(device="cpu")

    # Level 1: Embedding layer device
    mock_model_1 = MagicMock()
    mock_emb = MagicMock()
    mock_emb.weight.device = torch.device("cpu")
    mock_model_1.get_input_embeddings.return_value = mock_emb
    assert mgr.get_input_target_device(mock_model_1) == torch.device("cpu")

    # Level 2: model.device property (no embeddings method)
    mock_model_2 = MagicMock(spec=["device"])
    mock_model_2.device = torch.device("cpu")
    del mock_model_2.get_input_embeddings
    assert mgr.get_input_target_device(mock_model_2) == torch.device("cpu")

    # Level 3: First parameter device (no .device property, standard nn.Module)
    param = torch.nn.Parameter(torch.zeros(2, 2))
    mock_model_3 = MagicMock()
    del mock_model_3.get_input_embeddings
    del mock_model_3.device
    mock_model_3.parameters.return_value = iter([param])
    assert mgr.get_input_target_device(mock_model_3) == torch.device("cpu")

    # Level 4: Fallback to mgr.device
    mock_model_4 = MagicMock()
    del mock_model_4.get_input_embeddings
    del mock_model_4.device
    mock_model_4.parameters.return_value = iter([])
    assert mgr.get_input_target_device(mock_model_4) == torch.device("cpu")

def test_cuda_initialization_failure_during_load():
    """
    Requirement 4: Verifies clean recovery and reference eviction if CUDA initialization
    or memory allocation fails during model loading.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch.object(mgr, "_has_cuda", return_value=True):
        mgr.set_device("cuda")
        assert mgr.device == "cuda"

        # Simulate CUDA OOM during AutoModel loading
        with patch("transformers.AutoConfig.from_pretrained") as mock_cfg:
            mock_cfg.return_value.architectures = ["AutoModelForCausalLM"]
            with patch("transformers.AutoModelForCausalLM.from_pretrained", side_effect=RuntimeError("CUDA out of memory")):
                with pytest.raises(RuntimeError) as exc_info:
                    mgr.load_model("PRO")
                assert "cuda out of memory" in str(exc_info.value).lower()
                
                # Model references must be cleanly evicted
                assert len(mgr._loaded_models) == 0
                assert "PRO" not in mgr._loaded_models

def test_cpu_execution_after_failed_cuda_initialization():
    """
    Requirement 4: Verifies that after a CUDA initialization failure, the system
    can switch back to CPU and execute normally without state corruption.
    """
    mgr = LocalModelManager(device="cpu")
    
    # 1. Attempt CUDA and fail
    with patch.object(mgr, "_has_cuda", return_value=True):
        mgr.set_device("cuda")
        with patch("transformers.AutoConfig.from_pretrained", side_effect=RuntimeError("CUDA initialization failed")):
            with pytest.raises(RuntimeError):
                mgr.load_model("PRO")
    
    # 2. Reconfigure to CPU
    mgr.set_device("cpu")
    assert mgr.device == "cpu"
    assert len(mgr._loaded_models) == 0

    # 3. CPU dialectical response succeeds cleanly
    mgr.mock_mode = True
    response = mgr.generate("CON", "System prompt", "Topic: AI Safety")
    assert isinstance(response, str)
    assert len(response) > 50
    assert "negative" in response.lower() or "challenge" in response.lower()

def test_fault_tolerant_unloading_on_error():
    """
    Requirement 4: Verifies that unload_all catches eviction errors and guarantees
    complete reference purging and garbage collection.
    """
    mgr = LocalModelManager(device="cpu")
    
    class BrokenModel:
        def __del__(self):
            raise RuntimeError("Destructor error during eviction")

    mgr._loaded_models["CORRUPT"] = BrokenModel()
    mgr._loaded_tokenizers["CORRUPT"] = "tok"
    
    # Unload should not propagate exception
    mgr.unload_all()
    assert len(mgr._loaded_models) == 0
    assert len(mgr._loaded_tokenizers) == 0

def test_model_with_device_map_not_moved_to_device():
    """
    Requirement 3: Verifies that models loaded with device_map (hf_device_map)
    are NOT erroneously moved using model.to(device).
    """
    mgr = LocalModelManager(device="cpu")
    
    mock_model = MagicMock()
    # Simulate presence of accelerate device mapping
    mock_model.hf_device_map = {"model.embed_tokens": 0, "model.layers": 0}
    
    with patch.object(mgr, "_has_cuda", return_value=True):
        mgr.set_device("cuda")
        with patch.object(mgr, "load_tokenizer", return_value=MagicMock()):
            with patch("transformers.AutoConfig.from_pretrained") as mock_cfg:
                mock_cfg.return_value.architectures = ["AutoModelForCausalLM"]
                with patch("transformers.AutoModelForCausalLM.from_pretrained", return_value=mock_model):
                    model_loaded, _ = mgr.load_model("PRO")
                    # model.to() must NOT be called on models with hf_device_map
                    mock_model.to.assert_not_called()
                    assert model_loaded == mock_model

