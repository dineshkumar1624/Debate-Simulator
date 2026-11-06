import pytest
from unittest.mock import patch, MagicMock
from app.llm.model_manager import local_model_manager, LocalModelManager
from app.agents.pro_agent import pro_agent
from app.core.config import settings

def test_gemma_server_health_check():
    """Verifies that check_gemma_server_health returns a boolean and never raises exceptions."""
    is_healthy = local_model_manager.check_gemma_server_health()
    assert isinstance(is_healthy, bool)

def test_gemma_server_generate_mocked():
    """Verifies that _generate_gemma_server parses standard OpenAI-compatible completions correctly."""
    mgr = LocalModelManager()
    fake_response = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 123456789,
        "model": "gemma-4-E4B-Q4_0",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"argument_title": "Affirmative Defense", "argument_text": "Procedural consistency guarantees equity.", "central_claim": "Procedural consistency", "concise_rationale": "Fairness requires uniformity", "evidence_references": [], "limitations": null}'
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 45,
            "completion_tokens": 28,
            "total_tokens": 73
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response

    with patch("httpx.post", return_value=mock_resp):
        res = mgr._generate_gemma_server(
            system_prompt="You are PRO.",
            user_prompt="Explain equity.",
            max_new_tokens=64,
            return_metadata=True
        )

        assert isinstance(res, dict)
        assert res["execution_status"] == "REAL_LOCAL_MODEL"
        assert res["generated_tokens"] == 28
        assert res["input_tokens"] == 45
        assert res["hit_token_limit"] is False
        assert "Procedural consistency guarantees equity." in res["text"]

def test_gemma_server_generate_http_error():
    """Verifies that non-200 HTTP responses raise a clear RuntimeError."""
    mgr = LocalModelManager()
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "Service Unavailable: Model Loading"

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(RuntimeError) as exc_info:
            mgr._generate_gemma_server("System", "User")
        assert "returned HTTP 503" in str(exc_info.value)

def test_gemma_server_generate_empty_content():
    """Verifies that empty response content raises a RuntimeError."""
    mgr = LocalModelManager()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"choices": [{"message": {"content": "   "}}]}

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(RuntimeError) as exc_info:
            mgr._generate_gemma_server("System", "User")
        assert "empty response content" in str(exc_info.value)

def test_pro_agent_generate_turn_structure():
    """Verifies that ProAgent generates a complete and valid turn payload."""
    turn = pro_agent.generate_turn(
        topic="Universal Basic Income ensures economic resilience during automation transitions.",
        round_number=1,
        max_rounds=2,
        evidence_context="Economic studies indicate income floors stimulate local commerce.",
        latest_con_argument=None,
        max_new_tokens=64
    )

    assert turn["role"] == "PRO"
    assert turn["speaker"] == "DEBATER_A"
    assert turn["round_number"] == 1
    assert len(turn["content"]) > 10
    assert turn["execution_status"] in ("REAL_LOCAL_MODEL", "SIMULATED")
    assert "main_claim" in turn
    assert "evidence_references" in turn
