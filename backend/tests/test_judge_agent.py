import uuid
import json
import pytest
from unittest.mock import patch
from app.agents.judge_agent import judge_agent
from app.schemas.judge import JudgeReportSchema
from app.graph.nodes import save_result
from app.graph.state import DebateGraphState
from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel, DebateRoundModel, JudgeEvaluationModel
from app.llm.model_manager import local_model_manager

@pytest.fixture(autouse=True)
def setup_db_and_mock():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield

def test_judge_evaluation_with_grounding_evidence():
    """
    Verifies Judge evaluates complete transcript and grounding evidence without inventing citations.
    """
    topic = "Should autonomous AI agents face strict liability for medical misdiagnosis?"
    transcript = [
        {
            "speaker": "DEBATER_A",
            "role": "PRO",
            "round_number": 1,
            "title": "Strict Liability Enforces Deterministic Safety",
            "content": "Strict liability compels developers to adopt formal verification methods, eliminating preventable harm.",
            "evidence": [
                {
                    "source": "Document: Medical_AI_Safety.pdf",
                    "url": "https://clinical-ai.org/safety-standards-2026",
                    "text": "Formal verification of neural networks reduces diagnostic boundary errors by 41%."
                }
            ]
        },
        {
            "speaker": "DEBATER_B",
            "role": "CON",
            "round_number": 1,
            "title": "Strict Liability Stifles Diagnostic Innovation",
            "content": "Strict liability imposes crushing liability risks on edge-case rare diseases, discouraging life-saving deployment.",
            "evidence": [
                {
                    "source": "Document: FDA_AI_Report.pdf",
                    "url": "https://fda.gov/reports/medical-ai-development",
                    "text": "Over-regulation in rare disease diagnostic tooling caused a 35% drop in clinical trials."
                }
            ]
        }
    ]

    citations = [
        {
            "source": "Document: Medical_AI_Safety.pdf",
            "url": "https://clinical-ai.org/safety-standards-2026",
            "text": "Formal verification reduces diagnostic errors by 41%."
        },
        {
            "source": "Document: FDA_AI_Report.pdf",
            "url": "https://fda.gov/reports/medical-ai-development",
            "text": "Over-regulation caused a 35% drop in clinical trials."
        }
    ]

    report = judge_agent.evaluate_debate(topic=topic, transcript=transcript, evidence_citations=citations)
    assert isinstance(report, JudgeReportSchema)
    assert report.status == "completed"
    assert report.winner in ["PRO", "CON", "INCONCLUSIVE"]
    assert 0.0 <= report.pro_score <= 100.0
    assert 0.0 <= report.con_score <= 100.0
    assert len(report.pro_strengths) > 0
    assert len(report.con_strengths) > 0
    assert len(report.round_points) > 0
    assert len(report.supported_claims) > 0
    assert report.evidence_reliability_score >= 50.0

    # Ensure source references only contain the passed valid sources
    for ref in report.source_references:
        assert ("clinical-ai.org" in ref or "fda.gov" in ref or "Medical_AI_Safety" in ref or "FDA_AI_Report" in ref)

def test_judge_evaluation_missing_evidence():
    """
    Verifies that when grounding evidence is absent, the Judge:
    - Never hallucinates citations or URLs.
    - Sets source_references to empty list [].
    - Lowers evidence_reliability_score (<= 50.0).
    - Flags ungrounded assertions in unsupported_claims.
    """
    topic = "Should speculative neural architecture research be subsidized?"
    transcript = [
        {
            "speaker": "DEBATER_A",
            "role": "PRO",
            "round_number": 1,
            "title": "Subsidies Catalyze Breakthroughs",
            "content": "Public funding for speculative AI research drives foundational breakthroughs.",
            "evidence": []
        },
        {
            "speaker": "DEBATER_B",
            "role": "CON",
            "round_number": 1,
            "title": "Capital Misallocation",
            "content": "Subsidies misallocate capital toward ungrounded speculative models without market accountability.",
            "evidence": []
        }
    ]

    report = judge_agent.evaluate_debate(topic=topic, transcript=transcript, evidence_citations=[])
    assert isinstance(report, JudgeReportSchema)
    assert report.status == "completed"
    # Never invent citations
    assert report.source_references == []
    # Reduced reliability score due to lack of evidence
    assert report.evidence_reliability_score <= 50.0
    # Unsupported claims must explicitly state missing evidence
    assert any("ungrounded" in s.lower() or "grounding" in s.lower() or "unsupported" in s.lower() or "evidence" in s.lower() for s in report.unsupported_claims)

def test_judge_malformed_output_bounded_retry_recovery():
    """
    Verifies that if the first LLM generation attempt is malformed JSON,
    the bounded retry loop recovers and succeeds on subsequent attempts.
    """
    topic = "Retry recovery test"
    transcript = [
        {"speaker": "DEBATER_A", "role": "PRO", "round_number": 1, "content": "Pro position", "evidence": []},
        {"speaker": "DEBATER_B", "role": "CON", "round_number": 1, "content": "Con rebuttal", "evidence": []}
    ]

    valid_json = json.dumps({
        "pro_score": 85.0,
        "con_score": 83.0,
        "winner": "PRO",
        "status": "completed",
        "pro_strengths": ["Clear thesis"],
        "pro_weaknesses": ["Minor gaps"],
        "con_strengths": ["Direct clash"],
        "con_weaknesses": ["Weak empirical grounding"],
        "round_points": [{"round_number": 1, "pro_summary": "P", "con_summary": "C", "key_takeaway": "T"}],
        "main_arguments": ["Main arg"],
        "main_counterarguments": ["Main counter"],
        "supported_claims": [],
        "unsupported_claims": ["No external grounding evidence was provided"],
        "judge_reasoning": "Reasoning evaluated on deductive logic.",
        "balanced_verdict": "Verdict synthesized.",
        "evidence_reliability_score": 30.0,
        "source_references": []
    })

    # First attempt returns invalid text; second attempt returns valid_json
    attempts = ["Malformed text that is definitely not json", valid_json]
    def fake_generate(*args, **kwargs):
        return attempts.pop(0)

    with patch.object(local_model_manager, "generate", side_effect=fake_generate):
        report = judge_agent.evaluate_debate(topic=topic, transcript=transcript, evidence_citations=[], max_retries=2)
        assert report.status == "completed"
        assert report.winner == "PRO"
        assert report.pro_score == 85.0

def test_judge_malformed_output_all_retries_fail():
    """
    Verifies that if all bounded retries fail, JudgeAgent returns a structured
    failed report with status='failed' and winner='FAILED', without crashing.
    """
    topic = "Failed retry test"
    transcript = [
        {"speaker": "DEBATER_A", "role": "PRO", "round_number": 1, "content": "Pro position", "evidence": []},
        {"speaker": "DEBATER_B", "role": "CON", "round_number": 1, "content": "Con rebuttal", "evidence": []}
    ]

    with patch.object(local_model_manager, "generate", return_value="Still not valid JSON"):
        report = judge_agent.evaluate_debate(topic=topic, transcript=transcript, evidence_citations=[], max_retries=2)
        assert report.status == "failed"
        assert report.winner == "FAILED"
        assert report.pro_score == 0.0
        assert report.con_score == 0.0
        assert report.error_message is not None and "failed" in report.error_message.lower()

def test_judge_failure_does_not_corrupt_persisted_messages():
    """
    Verifies that if the Judge evaluation fails, save_result marks the debate
    as 'evaluation_failed' while preserving all previously persisted debate
    messages and rounds in SQL intact.
    """
    debate_id = str(uuid.uuid4())
    topic = "Non-corruption verification"

    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=1, status="evaluating")
        db.add(deb)
        m1 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Pro R1",
            content="Critical affirmative argument to be preserved.",
            confidence=95.0,
            evidence_references=[]
        )
        m2 = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_B",
            role="CON",
            title="Con R1",
            content="Critical negative argument to be preserved.",
            confidence=92.0,
            evidence_references=[]
        )
        r1 = DebateRoundModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            status="completed"
        )
        db.add(m1)
        db.add(m2)
        db.add(r1)
        db.commit()

    failed_report = {
        "status": "failed",
        "winner": "FAILED",
        "pro_score": 0.0,
        "con_score": 0.0,
        "error_message": "Unrecoverable malformed output",
        "judge_reasoning": "Adjudication failed schema validation.",
        "balanced_verdict": "Evaluation invalid."
    }

    state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "document_ids": [],
        "source_scope": "document",
        "current_round": 1,
        "max_rounds": 1,
        "current_speaker": "JUDGE",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": None,
        "current_con_turn": None,
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "transcript": [],
        "judge_report": failed_report,
        "resume_target": None,
        "status": "evaluation_failed",
        "error": "Unrecoverable malformed output"
    }

    res = save_result(state)
    assert res["status"] == "evaluation_failed"

    with SessionLocal() as db:
        deb_rec = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert deb_rec is not None
        assert deb_rec.status == "evaluation_failed"
        assert deb_rec.error_message == "Unrecoverable malformed output"

        # Verify all messages are preserved intact
        msgs = db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == debate_id).all()
        assert len(msgs) == 2
        assert {m.role for m in msgs} == {"PRO", "CON"}
        assert any("Critical affirmative argument" in m.content for m in msgs)
        assert any("Critical negative argument" in m.content for m in msgs)

        # Verify round is preserved
        rounds = db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == debate_id).all()
        assert len(rounds) == 1

        # Verify Judge evaluation record reflects failure
        ev = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert ev is not None
        assert ev.status == "failed"
        assert ev.winner == "FAILED"
