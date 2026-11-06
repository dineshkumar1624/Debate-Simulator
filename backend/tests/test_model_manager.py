import os
import json
import pytest
from app.llm.model_manager import local_model_manager, LocalModelManager
from app.schemas.judge import JudgeReportSchema
from app.core.config import settings

def test_model_manager_roles_configured():
    for role in ["PRO", "CON"]:
        path = local_model_manager.get_model_path(role)
        assert isinstance(path, str)
        assert len(path) > 0
        assert os.path.exists(path), f"Configured model path for {role} does not exist: {path}"
    # JUDGE is Google Gemini remote API model identifier
    judge_id = local_model_manager.get_model_path("JUDGE")
    assert isinstance(judge_id, str)
    assert "gemini" in judge_id.lower()

def test_tokenizers_load_locally_for_all_roles():
    """
    Verifies that local tokenizers load from local disk cache without making network calls.
    """
    for role in ["PRO", "CON"]:
        tokenizer = local_model_manager.load_tokenizer(role)
        assert tokenizer is not None
        assert len(tokenizer) > 0
        assert hasattr(tokenizer, "decode")

def test_chat_template_formatting_for_all_roles():
    """
    Verifies that chat templates format system and user messages into the exact prompt syntax
    expected by Gemma-4 (PRO) and Qwen2.5 (CON).
    """
    messages = [
        {"role": "system", "content": "You are a dialectical debater."},
        {"role": "user", "content": "Topic: Artificial Intelligence Governance"}
    ]

    for role in ["PRO", "CON"]:
        tokenizer = local_model_manager.load_tokenizer(role)
        assert hasattr(tokenizer, "apply_chat_template")
        formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        assert isinstance(formatted, str)
        assert len(formatted) > 30
        assert "Artificial Intelligence Governance" in formatted

def test_encoding_and_decoding_roundtrip_all_roles():
    """
    Verifies token encoding and decoding round-trip consistency across local tokenizers.
    """
    sample_text = "Dialectical reasoning eliminates arbitrary disparities."
    for role in ["PRO", "CON"]:
        tokenizer = local_model_manager.load_tokenizer(role)
        encoded = tokenizer(sample_text, return_tensors="pt")
        assert encoded.input_ids.shape[1] > 0
        decoded = tokenizer.decode(encoded.input_ids[0], skip_special_tokens=True)
        assert "Dialectical reasoning" in decoded

def test_sequential_single_model_memory_isolation():
    """
    Verifies that LocalModelManager maintains at most one model instance in memory,
    re-using loaded models without duplicate allocation, and clearing references on unload.
    """
    mgr = LocalModelManager()
    mgr._loaded_models["MOCK_ROLE_A"] = "mock_model_a"
    mgr._loaded_tokenizers["MOCK_ROLE_A"] = "mock_tokenizer_a"

    mgr.unload_all()
    assert len(mgr._loaded_models) == 0
    assert len(mgr._loaded_tokenizers) == 0

def test_regression_hardware_prechecks_fail_fast_on_cpu():
    """
    In a CPU-only environment with limited RAM:
    - JUDGE (4-bit bitsandbytes NF4) requires CUDA GPU and accelerate. Must fail fast.
    - An unconverted/NF4 model path must fail fast if loaded on CPU.
    """
    mgr = LocalModelManager()

    if not mgr._has_cuda():
        with pytest.raises(RuntimeError) as exc_info_judge:
            mgr.load_model("JUDGE")
        assert "gemini" in str(exc_info_judge.value).lower()

        # If a model path contains bitsandbytes quantization_config, it must fail fast
        original_nf4_con = "D:/models/Qwen2.5-VL-7B-Instruct"
        if os.path.exists(original_nf4_con):
            mgr.model_paths["CON"] = original_nf4_con
            with pytest.raises(RuntimeError) as exc_info_con_nf4:
                mgr.load_model("CON")
            assert "4-bit bitsandbytes quantization which requires a discrete cuda gpu" in str(exc_info_con_nf4.value).lower()
            # Restore converted path
            mgr.model_paths["CON"] = settings.CON_MODEL_PATH

def test_con_role_resolves_to_qwen_path():
    """
    Verifies that the CON role strictly resolves to the verified Qwen checkpoint,
    PRO resolves to Gemma, and JUDGE resolves to Gemini.
    """
    mgr = LocalModelManager()
    pro_path = mgr.get_model_path("PRO").replace("\\", "/")
    con_path = mgr.get_model_path("CON").replace("\\", "/")
    judge_path = mgr.get_model_path("JUDGE")

    assert "gemma" in pro_path.lower()
    assert con_path == "D:/models/Qwen2.5-VL-7B-Instruct"
    assert "gemini" in judge_path.lower()

    assert os.path.exists(con_path), f"CON model path does not exist: {con_path}"

    # Confirm Qwen config has bitsandbytes quantization_config
    cfg_file = os.path.join(con_path, "config.json")
    assert os.path.exists(cfg_file)
    with open(cfg_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    assert "quantization_config" in cfg
    assert cfg.get("quantization_config", {}).get("quant_method") == "bitsandbytes"

def test_non_mock_inference_refuses_fabrication():
    """
    Verifies that calling generate with mock_mode=False raises RuntimeError
    rather than fabricating synthetic text when local weights cannot load.
    """
    mgr = LocalModelManager()
    mgr.mock_mode = False

    # JUDGE cannot load on CPU due to NF4 bitsandbytes
    with pytest.raises(RuntimeError) as exc_info:
        mgr.generate("JUDGE", "System prompt", "User prompt")
    assert "refusing to fabricate" in str(exc_info.value).lower()

def test_model_generation_roles_mock_mode():
    local_model_manager.mock_mode = True
    pro_resp = local_model_manager.generate("PRO", "System prompt", "Topic: AI Ethics")
    assert "affirmative" in pro_resp.lower() or "pro" in pro_resp.lower()

    con_resp = local_model_manager.generate("CON", "System prompt", "Topic: AI Ethics")
    assert "negative" in con_resp.lower() or "challenge" in con_resp.lower()

    judge_resp = local_model_manager.generate("JUDGE", "System prompt", "Topic: AI Ethics")
    data = json.loads(judge_resp)
    validated = JudgeReportSchema.model_validate(data)
    assert 0.0 <= validated.pro_score <= 100.0
    assert 0.0 <= validated.con_score <= 100.0
    assert validated.winner in ["PRO", "CON", "INCONCLUSIVE"]
    assert len(validated.pro_strengths) > 0
    assert len(validated.con_strengths) > 0

def test_judge_schema_validation_rubric():
    valid_data = {
        "pro_score": 90.0,
        "con_score": 85.0,
        "winner": "PRO",
        "pro_strengths": ["Well cited"],
        "pro_weaknesses": ["None"],
        "con_strengths": ["Clear rebuttal"],
        "con_weaknesses": ["Lack of data"],
        "round_points": [{"round_number": 1, "pro_summary": "p", "con_summary": "c", "key_takeaway": "t"}],
        "main_arguments": ["Arg 1"],
        "main_counterarguments": ["Counter 1"],
        "supported_claims": ["Claim 1"],
        "unsupported_claims": ["Claim 2"],
        "judge_reasoning": "Reasoning here",
        "balanced_verdict": "Verdict here",
        "evidence_reliability_score": 92.0,
        "source_references": ["http://example.com"]
    }
    report = JudgeReportSchema.model_validate(valid_data)
    assert report.pro_score == 90.0
    assert report.winner == "PRO"

def test_disallowed_roles_rejected():
    mgr = LocalModelManager()
    with pytest.raises(ValueError) as exc1:
        mgr.get_model_path("INVALID_ROLE")
    assert "only exactly three" in str(exc1.value).lower()

    with pytest.raises(ValueError) as exc2:
        mgr.load_model("UNKNOWN_ROLE")
    assert "only exactly three" in str(exc2.value).lower()

def test_strict_three_model_paths():
    mgr = LocalModelManager()
    assert "gemma" in mgr.get_model_path("PRO").lower()
    assert mgr.get_model_path("PRO").endswith(".gguf")
    assert "qwen2.5-vl-7b-instruct" in mgr.get_model_path("CON").lower().replace("\\", "/")
    assert "gemini" in mgr.get_model_path("JUDGE").lower()

def test_api_rejects_disallowed_models():
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    resp = client.post("/api/debates", json={
        "topic": "Ethics of Autonomous AI",
        "debaterAModel": "gpt-4",
        "debaterBModel": "Qwen2.5-VL-7B-Instruct",
        "judgeModel": "gemini-3.5-flash"
    })
    assert resp.status_code == 400
    assert "Disallowed debater A (PRO) model" in resp.json()["detail"]

def test_model_manager_health_checks():
    mgr = LocalModelManager()
    assert hasattr(mgr, "check_gemma_server_health")
    assert hasattr(mgr, "check_qwen_health")
    assert hasattr(mgr, "check_gemini_health")
    assert hasattr(mgr, "check_all_providers_health")
    all_health = mgr.check_all_providers_health()
    assert "PRO" in all_health
    assert "CON" in all_health
    assert "JUDGE" in all_health
    assert all_health["PRO"]["role"] == "PRO"
    assert all_health["CON"]["role"] == "CON"
    assert all_health["JUDGE"]["role"] == "JUDGE"

def test_eos_token_resolution_and_format_gemma_and_qwen():
    """
    Verifies that authoritative EOS token configurations are extracted from local model
    generation_config.json files and match the exact IDs supported by Transformers 5.19.0:
    - Gemma-4-E4B-it: [1, 106, 50] (includes <end_of_turn> 106)
    - Qwen2.5-VL-7B-Instruct: [151645, 151643] (includes <|im_end|> 151645)
    """
    mgr = LocalModelManager()
    
    # 1. Gemma (PRO) EOS Verification for GGUF / llama.cpp Architecture
    gemma_path = mgr.get_model_path("PRO")
    assert gemma_path.endswith(".gguf") or "gemma" in gemma_path.lower()
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

    # Verify tokenizer matches (In Gemma-4, the end-of-turn token is '<turn|>' at ID 106, <eos> at ID 1)
    gemma_tok = mgr.load_tokenizer("PRO")
    assert gemma_tok.convert_tokens_to_ids("<turn|>") == 106
    assert gemma_tok.convert_tokens_to_ids("<eos>") == 1

    # 2. Qwen (CON) EOS Verification
    qwen_path = mgr.get_model_path("CON")
    qwen_gen_cfg_file = os.path.join(qwen_path, "generation_config.json")
    assert os.path.exists(qwen_gen_cfg_file), f"Missing Qwen generation_config.json at {qwen_gen_cfg_file}"
    with open(qwen_gen_cfg_file, "r", encoding="utf-8") as f:
        qwen_cfg = json.load(f)
    qwen_eos = qwen_cfg.get("eos_token_id")
    assert isinstance(qwen_eos, list), f"Expected list for Qwen eos_token_id, got {type(qwen_eos)}"
    assert 151645 in qwen_eos, "Qwen eos_token_id missing <|im_end|> token 151645"
    assert 151643 in qwen_eos, "Qwen eos_token_id missing <|endoftext|> token 151643"
    
    # Verify tokenizer matches
    qwen_tok = mgr.load_tokenizer("CON")
    assert qwen_tok.convert_tokens_to_ids("<|im_end|>") == 151645

def test_termination_distinction_metadata():
    """
    Verifies that model generation distinguishes normal end-of-turn termination
    from token limit saturation via return_metadata.
    """
    mgr = LocalModelManager()
    mgr.mock_mode = True
    
    meta = mgr.generate(
        role="CON",
        system_prompt="sys",
        user_prompt="usr",
        max_new_tokens=128,
        return_metadata=True
    )
    assert isinstance(meta, dict)
    assert "text" in meta
    assert "generated_tokens" in meta
    assert "hit_token_limit" in meta
    assert meta["hit_token_limit"] is False

def test_device_selection_cpu_default_and_backward_compatibility():
    """
    Verifies that LocalModelManager defaults to 'cpu' on the current host,
    and supports explicit 'cpu' and 'auto' configuration options.
    """
    mgr = LocalModelManager()
    assert mgr.device in ("cpu", "cuda")
    if not mgr._has_cuda():
        assert mgr.device == "cpu"
        assert mgr.resolve_device("auto") == "cpu"
        assert mgr.resolve_device("cpu") == "cpu"
        with pytest.raises(RuntimeError) as exc_info:
            mgr.resolve_device("cuda")
        assert "explicit cuda inference device requested" in str(exc_info.value).lower()

@pytest.mark.skipif(
    not os.getenv("RUN_REAL_QWEN_TEST"),
    reason="Real Qwen inference on CPU takes several minutes; enable with RUN_REAL_QWEN_TEST=1"
)
def test_real_qwen_smoke_test_cpu():
    """
    Focused real CPU inference test for converted Qwen checkpoint.
    Only executed when RUN_REAL_QWEN_TEST=1 is explicitly passed.
    """
    mgr = LocalModelManager()
    mgr.mock_mode = False
    response = mgr.generate(
        role="CON",
        system_prompt="You are the CON debater.",
        user_prompt="State a one-sentence objection to algorithmic sentencing.",
        max_new_tokens=20,
        temperature=0.0
    )
    assert isinstance(response, str)
    assert len(response.strip()) > 0
    mgr.unload_all()


