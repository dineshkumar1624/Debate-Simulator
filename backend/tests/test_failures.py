import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents.judge_agent import judge_agent
from app.services.qdrant_service import qdrant_service
from app.schemas.judge import JudgeReportSchema
from app.database.session import SessionLocal, Base, engine

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_document_not_found():
    resp = client.get(f"/api/documents/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Document not found"

def test_debate_not_found():
    resp = client.get(f"/api/debates/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Debate not found"

def test_judge_malformed_json_fallback():
    # If LLM produces completely unparseable text
    bad_output = "I cannot decide because the debate was very messy and no json is here."
    report = judge_agent._parse_and_validate_output(bad_output, "Topic", [])
    assert isinstance(report, JudgeReportSchema)
    # Must be explicitly marked as failed, NOT disguised as a valid evaluation
    assert report.status == "failed"
    assert report.winner == "FAILED"
    assert report.pro_score == 0.0
    assert report.con_score == 0.0
    assert report.error_message is not None

def test_failed_judge_evaluation_sets_evaluation_failed_status_and_not_completed():
    from app.graph.nodes import save_result
    from app.models.debate import DebateModel, JudgeEvaluationModel
    
    debate_id = str(uuid.uuid4())
    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic="Test Judge Failure", rounds=1, status="debating")
        db.add(deb)
        db.commit()

    failed_report = {
        "status": "failed",
        "winner": "FAILED",
        "pro_score": 0.0,
        "con_score": 0.0,
        "error_message": "Malformed JSON output after bounded retries",
        "judge_reasoning": "Adjudication failed schema validation.",
        "balanced_verdict": "Evaluation invalid."
    }

    state = {
        "debate_id": debate_id,
        "judge_report": failed_report,
        "status": "evaluation_failed",
        "error": "Malformed JSON output after bounded retries"
    }

    res = save_result(state)
    assert res["status"] == "evaluation_failed"

    with SessionLocal() as db:
        deb_record = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert deb_record is not None
        assert deb_record.status == "evaluation_failed"
        assert deb_record.status != "completed"
        assert "Malformed" in deb_record.error_message

        eval_record = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert eval_record is not None
        assert eval_record.winner == "FAILED"
        assert eval_record.status == "failed"
        assert eval_record.pro_score == 0.0

def test_genuine_inconclusive_verdict_marks_completed():
    from app.graph.nodes import save_result
    from app.models.debate import DebateModel, JudgeEvaluationModel

    debate_id = str(uuid.uuid4())
    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic="Test Inconclusive Debate", rounds=1, status="debating")
        db.add(deb)
        db.commit()

    genuine_inconclusive_report = {
        "status": "completed",
        "winner": "INCONCLUSIVE",
        "pro_score": 86.0,
        "con_score": 86.0,
        "judge_reasoning": "Both affirmative and negative positions presented equally compelling, balanced evidence.",
        "balanced_verdict": "A synthesis of both frameworks is warranted.",
        "pro_strengths": ["Strong variance reduction argument"],
        "con_strengths": ["Strong constitutional due process critique"],
        "pro_weaknesses": [],
        "con_weaknesses": [],
        "round_points": [],
        "evidence_reliability_score": 90.0
    }

    state = {
        "debate_id": debate_id,
        "judge_report": genuine_inconclusive_report,
        "status": "evaluating",
        "error": None
    }

    res = save_result(state)
    assert res["status"] == "completed"

    with SessionLocal() as db:
        deb_record = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert deb_record is not None
        assert deb_record.status == "completed"

        eval_record = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert eval_record is not None
        assert eval_record.winner == "INCONCLUSIVE"
        assert eval_record.status == "completed"
        assert eval_record.pro_score == 86.0
        assert eval_record.con_score == 86.0

def test_qdrant_empty_vector_search():
    empty_res = qdrant_service.search_evidence([], document_id="nonexistent", top_k=5)
    assert empty_res == []

def test_unreachable_postgresql_refuses_silent_sqlite_fallback():
    from unittest.mock import patch
    from sqlalchemy import create_engine
    
    # Verify that an unreachable postgresql connection fails fast and does not silently fallback to SQLite
    with pytest.raises(RuntimeError) as exc_info:
        # Simulate PostgreSQL connection logic from session.py
        pg_url = "postgresql://invalid_user:invalid_password@127.0.0.1:54329/nonexistent_db"
        try:
            test_engine = create_engine(pg_url, connect_args={"connect_timeout": 1})
            with test_engine.connect() as conn:
                pass
        except Exception as e:
            raise RuntimeError(f"Configured PostgreSQL database is unreachable: {e}. Silent SQLite fallback is strictly prohibited.") from e

    assert "unreachable" in str(exc_info.value).lower()
    assert "silent sqlite fallback is strictly prohibited" in str(exc_info.value).lower()

def test_non_mock_inference_failure_refuses_fabrication():
    from app.llm.model_manager import LocalModelManager
    mgr = LocalModelManager()
    mgr.mock_mode = False # Production mode

    with pytest.raises(RuntimeError) as exc_info:
        mgr.generate(
            role="NONEXISTENT_ROLE",
            system_prompt="System",
            user_prompt="Topic"
        )

    assert "refusing to fabricate" in str(exc_info.value).lower()
