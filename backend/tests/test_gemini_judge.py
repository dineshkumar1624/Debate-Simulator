"""
Integration and Unit Tests for Gemini 3.8 Flash Judge Integration.

Covers:
- Missing API key handling.
- Successful mocked Gemini API response.
- Valid structured Judge result conforming to JudgeReportSchema.
- Invalid or malformed JSON handling.
- Missing required Judge fields handling.
- Authentication failure fail-fast behavior (no useless retries).
- Rate-limiting (429) and transient error recovery with bounded backoff.
- Timeout error handling.
- Transient service failure (503) retry exhaustion.
- Guaranteeing failed judging never becomes a fake completed verdict.
- Ensuring the Judge runs only after the final CON response has been persisted.
- Ensuring PRO and CON roles and model paths remain completely unchanged.
"""

import json
import uuid
import pytest
from unittest.mock import MagicMock, patch
try:
    from google.genai import errors
except ImportError:
    class FakeAPIError(Exception):
        def __init__(self, code, message=None):
            self.code = code
            self.message = message
            super().__init__(f"APIError {code}: {message}")
    class FakeErrors:
        APIError = FakeAPIError
    errors = FakeErrors()

from app.core.config import settings
from app.schemas.judge import JudgeReportSchema
from app.services.gemini_judge_service import GeminiJudgeService, gemini_judge_service
from app.agents.judge_agent import judge_agent
from app.llm.model_manager import local_model_manager
from app.graph.debate_graph import debate_graph
from app.graph.state import DebateGraphState
from app.graph.nodes import validate_judge_output, save_result
from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel, DebateRoundModel, JudgeEvaluationModel

@pytest.fixture(autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    # Ensure clean gemini_judge_service state
    gemini_judge_service.set_client(None)

def _create_sample_transcript():
    return [
        {
            "speaker": "DEBATER_A",
            "role": "PRO",
            "round_number": 1,
            "title": "Empirical Variance Reduction",
            "content": "Algorithmic decision boundaries eliminate subjective sentencing disparities by 32%.",
            "evidence": [
                {
                    "source": "Document: Sentencing_AI_2026.pdf",
                    "url": "https://justice-ai.org/sentencing-variance",
                    "text": "Algorithmic decision boundaries reduce cross-circuit sentencing variance by 32%."
                }
            ]
        },
        {
            "speaker": "DEBATER_B",
            "role": "CON",
            "round_number": 1,
            "title": "Individualized Due Process",
            "content": "Statistical consistency masks catastrophic edge-case failures in novel fact patterns.",
            "evidence": [
                {
                    "source": "Document: Due_Process_Review.pdf",
                    "url": "https://law-review.edu/procedural-due-process",
                    "text": "Fixed constraint envelopes violate non-delegable judicial discretion requirements."
                }
            ]
        }
    ]

def _create_sample_citations():
    return [
        {
            "source": "Document: Sentencing_AI_2026.pdf",
            "url": "https://justice-ai.org/sentencing-variance",
            "text": "Algorithmic decision boundaries reduce cross-circuit sentencing variance by 32%."
        },
        {
            "source": "Document: Due_Process_Review.pdf",
            "url": "https://law-review.edu/procedural-due-process",
            "text": "Fixed constraint envelopes violate non-delegable judicial discretion requirements."
        }
    ]

def _create_valid_judge_dict():
    return {
        "pro_score": 88.0,
        "con_score": 85.5,
        "winner": "PRO",
        "status": "completed",
        "pro_strengths": ["Quantified 32% variance reduction", "Clear boundary definition"],
        "pro_weaknesses": ["Under-analyzed atypical edge cases"],
        "con_strengths": ["Strong constitutional due process critique"],
        "con_weaknesses": ["Lacked alternative baseline disparity solution"],
        "round_points": [
            {
                "round_number": 1,
                "pro_summary": "Defended mathematical consistency in sentencing.",
                "con_summary": "Argued for non-delegable human discretion under due process.",
                "key_takeaway": "Clash between statistical parity and individualized justice."
            }
        ],
        "main_arguments": ["Variance reduction across circuits"],
        "main_counterarguments": ["Non-delegable judicial discretion"],
        "supported_claims": ["Algorithmic envelopes reduce sentencing variance by 32%"],
        "unsupported_claims": ["Absolute eradication of all institutional bias"],
        "judge_reasoning": "PRO carried the debate on empirical precision while CON raised vital constitutional considerations.",
        "balanced_verdict": "PRO narrowly prevails based on evidentiary strength, with CON demonstrating important statutory safeguards.",
        "evidence_reliability_score": 90.0,
        "source_references": [
            "Document: Sentencing_AI_2026.pdf",
            "Document: Due_Process_Review.pdf"
        ]
    }

# --------------------------------------------------------------------------
# Test 1: Missing API Key Handling
# --------------------------------------------------------------------------
def test_missing_api_key_handling():
    service = GeminiJudgeService()
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with pytest.raises(ValueError) as exc_info:
            service.validate_configuration()
        assert "GEMINI_API_KEY is not configured" in str(exc_info.value)
        assert "aistudio.google.com" in str(exc_info.value)

        # evaluate_debate should gracefully return structured status='failed' without unhandled crash
        report = service.evaluate_debate(
            topic="Test Topic",
            transcript=_create_sample_transcript(),
            evidence_citations=_create_sample_citations()
        )
        assert report.status == "failed"
        assert report.winner == "FAILED"
        assert report.pro_score == 0.0
        assert report.con_score == 0.0
        assert "GEMINI_API_KEY is not configured" in report.error_message

# --------------------------------------------------------------------------
# Test 2: Successful Mocked Gemini API Response
# --------------------------------------------------------------------------
def test_successful_mocked_gemini_response():
    mock_client = MagicMock()
    mock_response = MagicMock()
    valid_data = _create_valid_judge_dict()
    mock_response.text = json.dumps(valid_data)
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiJudgeService()
    service.set_client(mock_client)

    report = service.evaluate_debate(
        topic="Should AI models adjudicate legal disputes?",
        transcript=_create_sample_transcript(),
        evidence_citations=_create_sample_citations()
    )

    assert isinstance(report, JudgeReportSchema)
    assert report.status == "completed"
    assert report.winner == "PRO"
    assert report.pro_score == 88.0
    assert report.con_score == 85.5
    assert len(report.pro_strengths) > 0
    assert len(report.con_strengths) > 0
    assert len(report.round_points) == 1
    assert report.evidence_reliability_score == 90.0
    assert "Sentencing_AI_2026.pdf" in report.source_references[0]

# --------------------------------------------------------------------------
# Test 3: Citation Discipline Enforcement
# --------------------------------------------------------------------------
def test_citation_discipline_filters_hallucinated_sources():
    mock_client = MagicMock()
    mock_response = MagicMock()
    data = _create_valid_judge_dict()
    # Add a fabricated citation that does not exist in debate transcript/evidence
    data["source_references"].append("Document: Fabricated_Fake_Source_2099.pdf")
    data["source_references"].append("https://fake-news-hallucination.xyz/bad")
    mock_response.text = json.dumps(data)
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiJudgeService()
    service.set_client(mock_client)

    report = service.evaluate_debate(
        topic="Citation discipline test",
        transcript=_create_sample_transcript(),
        evidence_citations=_create_sample_citations()
    )

    # Hallucinated citations must have been stripped
    assert report.status == "completed"
    for ref in report.source_references:
        assert "Fabricated_Fake_Source_2099" not in ref
        assert "fake-news-hallucination.xyz" not in ref

# --------------------------------------------------------------------------
# Test 4: Invalid or Malformed Response Handling
# --------------------------------------------------------------------------
def test_invalid_or_malformed_response_handling():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is definitely not valid JSON! Just plain unparseable text."
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiJudgeService()
    service.set_client(mock_client)

    report = service.evaluate_debate(
        topic="Malformed response test",
        transcript=_create_sample_transcript(),
        max_retries=1
    )

    assert report.status == "failed"
    assert report.winner == "FAILED"
    assert report.pro_score == 0.0
    assert report.con_score == 0.0
    assert "failed" in report.error_message.lower()

# --------------------------------------------------------------------------
# Test 5: Missing Required Judge Fields Handling
# --------------------------------------------------------------------------
def test_missing_required_fields_handling():
    mock_client = MagicMock()
    mock_response = MagicMock()
    # Incomplete payload missing required fields like pro_strengths, con_weaknesses, round_points
    incomplete_dict = {
        "pro_score": 80.0,
        "con_score": 75.0,
        "winner": "PRO"
    }
    mock_response.text = json.dumps(incomplete_dict)
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiJudgeService()
    service.set_client(mock_client)

    report = service.evaluate_debate(
        topic="Missing fields test",
        transcript=_create_sample_transcript(),
        max_retries=1
    )

    assert report.status == "failed"
    assert report.winner == "FAILED"
    assert "failed" in report.error_message.lower()

# --------------------------------------------------------------------------
# Test 6: Authentication Failure Fails Fast (No Useless Retries)
# --------------------------------------------------------------------------
def test_authentication_failure_fails_fast():
    mock_client = MagicMock()
    # Create real APIError representing 401 Unauthorized
    auth_error = errors.APIError(401, {"error": {"code": 401, "message": "API_KEY_INVALID"}})
    mock_client.models.generate_content.side_effect = auth_error

    service = GeminiJudgeService()
    service.set_client(mock_client)

    report = service.evaluate_debate(
        topic="Auth failure test",
        transcript=_create_sample_transcript(),
        max_retries=3
    )

    # Must fail immediately on attempt 1 without calling generate_content 4 times
    assert mock_client.models.generate_content.call_count == 1
    assert report.status == "failed"
    assert report.winner == "FAILED"
    assert "401" in report.error_message or "API_KEY_INVALID" in report.error_message

# --------------------------------------------------------------------------
# Test 7: Rate Limiting (429) With Bounded Retry Recovery
# --------------------------------------------------------------------------
def test_rate_limiting_with_bounded_retry_recovery():
    mock_client = MagicMock()
    rate_limit_error = errors.APIError(429, {"error": {"code": 429, "message": "RESOURCE_EXHAUSTED"}})
    valid_response = MagicMock()
    valid_response.text = json.dumps(_create_valid_judge_dict())

    # First attempt: 429 rate limit; Second attempt: Success
    mock_client.models.generate_content.side_effect = [rate_limit_error, valid_response]

    service = GeminiJudgeService()
    service.set_client(mock_client)

    with patch("time.sleep", return_value=None):  # Skip sleep duration in unit test
        report = service.evaluate_debate(
            topic="Rate limit test",
            transcript=_create_sample_transcript(),
            max_retries=2
        )

    assert mock_client.models.generate_content.call_count == 2
    assert report.status == "completed"
    assert report.winner == "PRO"
    assert report.pro_score == 88.0

# --------------------------------------------------------------------------
# Test 8: Timeout Handling With Retry
# --------------------------------------------------------------------------
def test_timeout_handling_with_retry():
    mock_client = MagicMock()
    valid_response = MagicMock()
    valid_response.text = json.dumps(_create_valid_judge_dict())

    # Attempt 1 times out; Attempt 2 succeeds
    mock_client.models.generate_content.side_effect = [TimeoutError("Request timed out after 120s"), valid_response]

    service = GeminiJudgeService()
    service.set_client(mock_client)

    with patch("time.sleep", return_value=None):
        report = service.evaluate_debate(
            topic="Timeout test",
            transcript=_create_sample_transcript(),
            max_retries=2
        )

    assert mock_client.models.generate_content.call_count == 2
    assert report.status == "completed"
    assert report.winner == "PRO"

# --------------------------------------------------------------------------
# Test 9: Transient Service Failure Retry Exhaustion
# --------------------------------------------------------------------------
def test_transient_service_failure_retry_exhaustion():
    mock_client = MagicMock()
    server_error = errors.APIError(503, {"error": {"code": 503, "message": "Service Unavailable"}})
    mock_client.models.generate_content.side_effect = server_error

    service = GeminiJudgeService()
    service.set_client(mock_client)

    with patch("time.sleep", return_value=None):
        report = service.evaluate_debate(
            topic="Server failure exhaustion test",
            transcript=_create_sample_transcript(),
            max_retries=2  # Initial + 2 retries = 3 attempts total
        )

    assert mock_client.models.generate_content.call_count == 3
    assert report.status == "failed"
    assert report.winner == "FAILED"
    assert "503" in report.error_message or "Service Unavailable" in report.error_message

# --------------------------------------------------------------------------
# Test 10: Failed Judging Never Becomes a Fake Completed Verdict
# --------------------------------------------------------------------------
def test_failed_judging_never_becomes_fake_completed_verdict():
    debate_id = str(uuid.uuid4())
    topic = "Failed judging verification"

    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=1, status="evaluating")
        db.add(deb)
        db.commit()

    failed_report = JudgeReportSchema(
        pro_score=0.0,
        con_score=0.0,
        winner="FAILED",
        status="failed",
        error_message="Gemini API rate limit exceeded after maximum retries",
        pro_strengths=[],
        pro_weaknesses=[],
        con_strengths=[],
        con_weaknesses=[],
        round_points=[],
        main_arguments=[],
        main_counterarguments=[],
        supported_claims=[],
        unsupported_claims=[],
        judge_reasoning="Evaluation failed due to service unavailability.",
        balanced_verdict="Evaluation Failed.",
        evidence_reliability_score=0.0,
        source_references=[]
    )

    state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 1,
        "current_speaker": "CON",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": None,
        "current_con_turn": None,
        "latest_pro_argument": "Pro arg",
        "latest_con_argument": "Con arg",
        "transcript": _create_sample_transcript(),
        "judge_report": failed_report.model_dump(),
        "status": "evaluating",
        "error": None
    }

    # Step 1: validate_judge_output must catch the failure and set status to 'evaluation_failed'
    val_out = validate_judge_output(state)
    assert val_out.get("status") == "evaluation_failed"
    assert val_out.get("error") == failed_report.error_message

    state.update(val_out)

    # Step 2: save_result must record evaluation_failed and winner='FAILED' in SQL
    save_result(state)

    with SessionLocal() as db:
        deb = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert deb.status == "evaluation_failed"
        persisted_eval = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert persisted_eval is not None
        assert persisted_eval.status == "failed"
        assert persisted_eval.winner == "FAILED"
        assert persisted_eval.pro_score == 0.0
        assert persisted_eval.con_score == 0.0

# --------------------------------------------------------------------------
# Test 11: Judge Runs Only After Final CON Response Persisted
# --------------------------------------------------------------------------
def test_judge_runs_only_after_final_con_persisted():
    """
    Verifies that in LangGraph, judge_agent is reached strictly via
    compile_complete_transcript, which in turn only triggers after save_con_message
    persists the final CON round.
    """
    debate_id = str(uuid.uuid4())
    topic = "Order of operations test"
    
    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=1, status="debating")
        db.add(deb)
        db.commit()

    execution_order = []

    def mock_judge_eval(*args, **kwargs):
        # Assert at the moment judge executes, final CON message exists in DB
        with SessionLocal() as db:
            con_msg = db.query(DebateMessageModel).filter(
                DebateMessageModel.debate_id == debate_id,
                DebateMessageModel.role == "CON"
            ).first()
            assert con_msg is not None, "Judge executed before final CON message was saved to database!"
        execution_order.append("judge_agent")
        return JudgeReportSchema.model_validate(_create_valid_judge_dict())

    initial_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 1,
        "current_speaker": "PRO",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": None,
        "current_con_turn": None,
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "transcript": [],
        "judge_report": None,
        "status": "idle",
        "error": None
    }

    local_model_manager.mock_mode = True
    with patch.object(judge_agent, "evaluate_debate", side_effect=mock_judge_eval):
        final_state = debate_graph.invoke(initial_state)

    assert "judge_agent" in execution_order

# --------------------------------------------------------------------------
# Test 12: PRO and CON Roles and Paths Remain Unchanged
# --------------------------------------------------------------------------
def test_pro_and_con_roles_and_paths_remain_unchanged():
    pro_path = local_model_manager.get_model_path("PRO").replace("\\", "/")
    con_path = local_model_manager.get_model_path("CON").replace("\\", "/")

    expected_gemma = getattr(settings, "GEMMA_MODEL_PATH", "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf").replace("\\", "/")
    expected_qwen = getattr(settings, "QWEN_MODEL_PATH", "D:/models/Qwen2.5-VL-7B-Instruct").replace("\\", "/")

    # PRO must resolve to the configured Gemma GGUF model path
    assert pro_path == expected_gemma or "gemma-4-e4b_q4_0-it.gguf" in pro_path.lower()
    assert pro_path.endswith(".gguf")
    assert "gemma" in pro_path.lower()

    # CON must resolve to the configured Qwen model path
    assert con_path == expected_qwen or "qwen2.5-vl-7b-instruct" in con_path.lower()
    assert "qwen" in con_path.lower()

    # Ensure LocalModelManager only allows PRO, CON, JUDGE
    with pytest.raises(ValueError):
        local_model_manager.get_model_path("INVALID_ROLE")
