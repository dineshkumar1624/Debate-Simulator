import os
import json
import pytest
import threading
from unittest.mock import patch, MagicMock
import torch

from app.llm.model_manager import LocalModelManager
from app.core.config import settings

def test_sequential_pro_to_con_loading_without_coexistence():
    """
    Lifecycle Audit 1: PRO-to-CON sequential loading guarantees that PRO and CON
    models never coexist in memory simultaneously.
    """
    mgr = LocalModelManager(device="cpu")
    
    mock_pro_model = MagicMock(name="mock_pro_model")
    mock_con_model = MagicMock(name="mock_con_model")
    mock_tokenizer = MagicMock(name="mock_tokenizer")

    def mock_cfg_side_effect(path, **kwargs):
        cfg = MagicMock()
        if "qwen" in path.lower():
            cfg.architectures = ["Qwen2_5_VLForConditionalGeneration"]
        else:
            cfg.architectures = ["AutoModelForCausalLM"]
        return cfg

    with patch.object(mgr, "load_tokenizer", return_value=mock_tokenizer):
        with patch("transformers.AutoConfig.from_pretrained", side_effect=mock_cfg_side_effect):
            with patch("transformers.AutoModelForCausalLM.from_pretrained", return_value=mock_pro_model):
                m_pro, _ = mgr.load_model("PRO")
                assert m_pro == mock_pro_model
                assert len(mgr._loaded_models) == 1
                assert "PRO" in mgr._loaded_models
                assert "CON" not in mgr._loaded_models

            # Now load CON: verify PRO is evicted prior to CON being assigned
            with patch("transformers.Qwen2_5_VLForConditionalGeneration.from_pretrained", return_value=mock_con_model):
                m_con, _ = mgr.load_model("CON")
                assert m_con == mock_con_model
                assert len(mgr._loaded_models) == 1
                assert "CON" in mgr._loaded_models
                assert "PRO" not in mgr._loaded_models

    mgr.unload_all()
    assert len(mgr._loaded_models) == 0

def test_repeated_load_unload_without_stale_references():
    """
    Lifecycle Audit 2: Repeated cycles of loading and unloading must completely
    evict internal dictionary references and prevent reference retention.
    """
    mgr = LocalModelManager(device="cpu")
    
    for cycle in range(5):
        mgr._loaded_models["MOCK_ROLE"] = f"model_instance_{cycle}"
        mgr._loaded_tokenizers["MOCK_ROLE"] = f"tokenizer_instance_{cycle}"
        assert len(mgr._loaded_models) == 1
        assert len(mgr._loaded_tokenizers) == 1
        
        mgr.unload_all()
        assert len(mgr._loaded_models) == 0
        assert len(mgr._loaded_tokenizers) == 0

def test_tokenizer_loading_exception_handling():
    """
    Lifecycle Audit 3: Exceptions during tokenizer loading must abort cleanly,
    trigger unload_all, and leave no partial state.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch("transformers.AutoTokenizer.from_pretrained", side_effect=FileNotFoundError("Corrupted tokenizer")):
        with pytest.raises(FileNotFoundError):
            mgr.load_model("PRO")
        assert len(mgr._loaded_models) == 0
        assert len(mgr._loaded_tokenizers) == 0

def test_model_loading_exception_handling():
    """
    Lifecycle Audit 3 & 4: Exceptions during model weights loading (e.g. corrupt shard)
    must invoke unload_all and purge any partial state.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch.object(mgr, "load_tokenizer", return_value=MagicMock()):
        with patch("transformers.AutoConfig.from_pretrained") as mock_cfg:
            mock_cfg.return_value.architectures = ["AutoModelForCausalLM"]
            with patch("transformers.AutoModelForCausalLM.from_pretrained", side_effect=RuntimeError("Safetensor error")):
                with pytest.raises(RuntimeError) as exc:
                    mgr.load_model("PRO")
                assert "safetensor error" in str(exc.value).lower()
                assert len(mgr._loaded_models) == 0

def test_device_placement_exception_handling():
    """
    Lifecycle Audit 3 & 4: Exceptions during model.to(device) placement must cleanly
    evict the model and purge cache.
    """
    mgr = LocalModelManager(device="cpu")
    mock_model = MagicMock(spec=torch.nn.Module)
    mock_model.to.side_effect = RuntimeError("CUDA device assertion triggered")
    
    with patch.object(mgr, "_has_cuda", return_value=True), patch.object(mgr, "_has_accelerate", return_value=False):
        mgr.set_device("cuda")
        with patch.object(mgr, "load_tokenizer", return_value=MagicMock()):
            with patch("transformers.AutoConfig.from_pretrained") as mock_cfg:
                mock_cfg.return_value.architectures = ["AutoModelForCausalLM"]
                with patch("transformers.AutoModelForCausalLM.from_pretrained", return_value=mock_model):
                    with pytest.raises(RuntimeError) as exc:
                        mgr.load_model("PRO")
                    assert "cuda device assertion" in str(exc.value).lower()
                    assert len(mgr._loaded_models) == 0

def test_partial_initialization_cleanup_on_cpu_insufficient_ram():
    """
    Lifecycle Audit 4: Hardware precheck for insufficient RAM fails fast before
    instantiating models, preserving clean memory state.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch("psutil.virtual_memory") as mock_vm:
        mock_vm.return_value.available = 500 * (1024**2)  # 0.5 GB available (< 1.0 GB limit)
        with pytest.raises(RuntimeError) as exc:
            mgr.load_model("PRO")
        assert "insufficient available system ram" in str(exc.value).lower()
        assert len(mgr._loaded_models) == 0

def test_cpu_operation_after_failed_cuda_initialization():
    """
    Lifecycle Audit 5: After a failed CUDA attempt, switching to CPU permits
    successful generation without state corruption.
    """
    mgr = LocalModelManager(device="cpu")
    
    # 1. Fail under CUDA
    with patch.object(mgr, "_has_cuda", return_value=True):
        mgr.set_device("cuda")
        with patch("transformers.AutoConfig.from_pretrained", side_effect=RuntimeError("CUDA out of memory")):
            with pytest.raises(RuntimeError):
                mgr.load_model("PRO")
    
    # 2. Recover to CPU
    mgr.set_device("cpu")
    assert mgr.device == "cpu"
    assert len(mgr._loaded_models) == 0
    
    # 3. Successful execution on CPU in mock mode
    mgr.mock_mode = True
    output = mgr.generate("PRO", "System prompt", "Topic: AI Governance")
    assert "affirmative" in output.lower()

def test_device_map_auto_prevents_to_call():
    """
    Lifecycle Audit 6: Verifies that models equipped with an hf_device_map
    are never moved with model.to(device).
    """
    mgr = LocalModelManager(device="cpu")
    mock_model = MagicMock()
    mock_model.hf_device_map = {"model.embed_tokens": 0, "model.layers": 0}
    
    with patch.object(mgr, "_has_cuda", return_value=True):
        mgr.set_device("cuda")
        with patch.object(mgr, "load_tokenizer", return_value=MagicMock()):
            with patch("transformers.AutoConfig.from_pretrained") as mock_cfg:
                mock_cfg.return_value.architectures = ["AutoModelForCausalLM"]
                with patch("transformers.AutoModelForCausalLM.from_pretrained", return_value=mock_model):
                    loaded_m, _ = mgr.load_model("PRO")
                    mock_model.to.assert_not_called()
                    assert loaded_m == mock_model

def test_input_device_resolution_all_architectures():
    """
    Lifecycle Audit 7: Verifies reliable input device identification across
    ordinary models, wrapped models, and sharded embedding architectures.
    """
    mgr = LocalModelManager(device="cpu")
    
    # Case A: Embedding layer specifies device
    model_a = MagicMock()
    emb = MagicMock()
    emb.weight.device = torch.device("cpu")
    model_a.get_input_embeddings.return_value = emb
    assert mgr.get_input_target_device(model_a) == torch.device("cpu")

    # Case B: Standard Hugging Face PreTrainedModel (.device property)
    model_b = MagicMock(spec=["device"])
    model_b.device = torch.device("cpu")
    del model_b.get_input_embeddings
    assert mgr.get_input_target_device(model_b) == torch.device("cpu")

    # Case C: Parameter-only PyTorch nn.Module (no .device)
    model_c = MagicMock()
    del model_c.get_input_embeddings
    del model_c.device
    param = torch.nn.Parameter(torch.zeros(1, 1))
    model_c.parameters.return_value = iter([param])
    assert mgr.get_input_target_device(model_c) == torch.device("cpu")

    # Case D: Empty model fallback
    model_d = MagicMock()
    del model_d.get_input_embeddings
    del model_d.device
    model_d.parameters.return_value = iter([])
    assert mgr.get_input_target_device(model_d) == torch.device("cpu")

def test_cuda_cleanup_exception_resilience():
    """
    Lifecycle Audit 8: Unload_all guarantees complete dictionary clearing and gc.collect
    even if torch.cuda.empty_cache raises an exception.
    """
    mgr = LocalModelManager(device="cpu")
    mgr._loaded_models["MOCK"] = "model"
    mgr._loaded_tokenizers["MOCK"] = "tokenizer"
    
    with patch.object(mgr, "_has_cuda", return_value=True):
        with patch("torch.cuda.is_available", return_value=True):
            with patch("torch.cuda.empty_cache", side_effect=RuntimeError("CUDA driver failure")):
                # Must not raise
                mgr.unload_all()
                assert len(mgr._loaded_models) == 0
                assert len(mgr._loaded_tokenizers) == 0

def test_cuda_device_count_query_exception_handling():
    """
    Lifecycle Audit 9: If torch.cuda.device_count() throws an exception,
    resolve_device fails with a clear, informative RuntimeError.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch.object(mgr, "_has_cuda", return_value=True):
        with patch("torch.cuda.device_count", side_effect=RuntimeError("Driver communication failed")):
            with pytest.raises(RuntimeError) as exc:
                mgr.resolve_device("cuda:0")
            assert "failed to query cuda device count" in str(exc.value).lower()
            assert "driver communication failed" in str(exc.value).lower()

def test_torch_cuda_is_available_exception_safety():
    """
    Lifecycle Audit 9 & 10: If torch.cuda.is_available() throws an exception,
    _has_cuda catches it safely and auto falls back to cpu.
    """
    mgr = LocalModelManager(device="cpu")
    
    with patch("torch.cuda.is_available", side_effect=RuntimeError("CUDA runtime broken")):
        assert mgr._has_cuda() is False
        assert mgr.resolve_device("auto") == "cpu"

def test_reentrant_lock_concurrency_and_reentrancy():
    """
    Lifecycle Audit 11: Verifies re-entrant safety (calling unload_all inside load_model)
    and concurrent access serialization via _lock.
    """
    mgr = LocalModelManager(device="cpu")
    
    # 1. Re-entrancy verification: calling unload_all while holding _lock must not deadlock
    with mgr._lock:
        mgr.unload_all()
        assert len(mgr._loaded_models) == 0

    # 2. Concurrency serialization test
    results = []
    def worker(role_name):
        with mgr._lock:
            mgr._loaded_models[role_name] = f"model_{role_name}"
            results.append(role_name)

    t1 = threading.Thread(target=worker, args=("PRO",))
    t2 = threading.Thread(target=worker, args=("CON",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    mgr.unload_all()

def test_judge_fallback_and_completion_rules_intact():
    """
    Lifecycle Audit 12: Judge local dialectical fallback and completion schema
    remain fully functional and schema-compliant.
    """
    mgr = LocalModelManager(device="cpu")
    mgr.mock_mode = True
    
    judge_output = mgr.generate(
        role="JUDGE",
        system_prompt="You are the judge.",
        user_prompt="Topic: Algorithmic Accountability\nPRO argument here\nCON argument here"
    )
    
    parsed = json.loads(judge_output)
    assert "pro_score" in parsed
    assert "con_score" in parsed
    assert "winner" in parsed
    assert parsed["winner"] in ("PRO", "CON", "INCONCLUSIVE")
    assert "judge_reasoning" in parsed

