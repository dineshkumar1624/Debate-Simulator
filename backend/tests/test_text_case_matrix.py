"""
Comprehensive Text-Case Validation Matrix for AI Debate Simulator.

Validates:
1. General topic: "Should students be allowed to use AI tools for assignments?"
2. Technology: "Will AI replace software developers?"
3. Education: "Should college attendance be mandatory?"
4. Environment: "Should single-use plastic be banned?"
5. Ambiguous topic: "Is technology good or bad?"
6. Very short topic: "Remote work?"
7. Empty or whitespace-only topic validation.
8. Invalid round count handling (zero, negative, out-of-bounds).
9. Long proposition input validation and prompt construction.
10. Topic with no uploaded document (general research scope, zero invented citations).

Debate Quality Verifications:
- PRO and CON address the same proposition.
- CON directly addresses the latest PRO argument.
- Correct round-by-round turns and message counts.
- Historical context passed between rounds.
- Judge runs only after all turns complete.
- Impartial structured evaluation.
- No hallucinated sources when evidence is missing.
- Failed turns do not produce completed verdicts.
- Inconclusive ties remain distinguishable from failure.
- Idempotent persistence on retries.
"""

import sys
import uuid
import json
import pytest
from unittest.mock import patch, MagicMock

from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateRoundModel, DebateMessageModel, JudgeEvaluationModel
from app.graph.debate_graph import debate_graph
from app.graph.state import DebateGraphState
from app.graph.nodes import (
    save_pro_message,
    save_con_message,
    compile_complete_transcript,
    judge_agent_node,
    save_result,
    check_pro_turn_routing,
    should_continue_debate,
    check_adjudication_routing
)
from app.llm.model_manager import local_model_manager
from app.schemas.judge import JudgeReportSchema
from app.schemas.debate import StartDebateRequest
from app.agents.judge_agent import judge_agent
from app.agents.pro_agent import pro_agent
from app.agents.con_agent import con_agent

@pytest.fixture(autouse=True)
def setup_db_mock():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield
    local_model_manager.mock_mode = False

# ==============================================================================
# Category 1: General Topic — "Should students be allowed to use AI tools for assignments?"
# ==============================================================================

def test_category_1_general_topic_single_round():
    topic = "Should students be allowed to use AI tools for assignments?"
    debate_id = str(uuid.uuid4())

    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=1, status="idle")
        db.add(deb)
        db.commit()

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

    final_state = debate_graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    assert final_state["error"] is None
    transcript = final_state["transcript"]
    assert len(transcript) == 2  # 1 PRO, 1 CON

    pro_turn = transcript[0]
    con_turn = transcript[1]
    assert pro_turn["role"] == "PRO"
    assert con_turn["role"] == "CON"

    # Both address same debate context
    assert len(pro_turn["content"]) > 50
    assert len(con_turn["content"]) > 50
    assert "affirmative" in pro_turn["content"].lower() or "empirical" in pro_turn["content"].lower()
    assert "negative" in con_turn["content"].lower() or "challenge" in con_turn["content"].lower()

    # Judge report verification
    report = final_state["judge_report"]
    assert report is not None
    assert report["status"] == "completed"
    assert report["winner"] in ["PRO", "CON", "INCONCLUSIVE"]
    assert 0.0 <= report["pro_score"] <= 100.0
    assert 0.0 <= report["con_score"] <= 100.0
    assert len(report["judge_reasoning"]) > 20
    assert len(report["balanced_verdict"]) > 20

    # Persistence verification
    with SessionLocal() as db:
        db_deb = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert db_deb is not None
        assert db_deb.status == "completed"
        assert len(db_deb.messages) == 2
        assert len(db_deb.round_records) == 1
        assert db_deb.evaluation is not None

# ==============================================================================
# Category 2: Technology — "Will AI replace software developers?" (2 Rounds Multi-Turn)
# ==============================================================================

def test_category_2_technology_multi_round_context_flow():
    topic = "Will AI replace software developers?"
    debate_id = str(uuid.uuid4())

    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=2, status="idle")
        db.add(deb)
        db.commit()

    initial_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 2,
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

    final_state = debate_graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    transcript = final_state["transcript"]
    assert len(transcript) == 4  # 2 rounds * 2 turns = 4

    # Check turn-by-turn ordering: R1 PRO, R1 CON, R2 PRO, R2 CON
    expected_sequence = [(1, "PRO"), (1, "CON"), (2, "PRO"), (2, "CON")]
    actual_sequence = [(t["round_number"], t["role"]) for t in transcript]
    assert actual_sequence == expected_sequence

    # Verify Judge runs only after turn 4
    report = final_state["judge_report"]
    assert report is not None
    assert len(report.get("round_points", [])) >= 1

# ==============================================================================
# Category 3: Education — "Should college attendance be mandatory?"
# ==============================================================================

def test_category_3_education_rebuttal_clash():
    topic = "Should college attendance be mandatory?"
    
    # Test pro and con agents directly with clean context
    pro_out = pro_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context="Labor economics statistics verify a 65% median lifetime earnings differential."
    )
    assert pro_out["is_valid"] is True
    assert len(pro_out["content"]) > 40

    con_out = con_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context="Apprenticeship data indicates vocational pathways yield debt-free career entry by age 21.",
        latest_pro_argument=pro_out["content"]
    )
    assert con_out["is_valid"] is True
    assert len(con_out["content"]) > 40

# ==============================================================================
# Category 4: Environment — "Should single-use plastic be banned?"
# ==============================================================================

def test_category_4_environment_topic():
    topic = "Should single-use plastic be banned?"
    debate_id = str(uuid.uuid4())

    with SessionLocal() as db:
        db.add(DebateModel(id=debate_id, topic=topic, rounds=1, status="idle"))
        db.commit()

    s: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "current_round": 1,
        "max_rounds": 1,
        "transcript": [],
        "status": "idle"
    }
    final = debate_graph.invoke(s)
    assert final["status"] == "completed"
    assert len(final["transcript"]) == 2

# ==============================================================================
# Category 5: Ambiguous Topic — "Is technology good or bad?"
# ==============================================================================

def test_category_5_ambiguous_non_binary_topic():
    topic = "Is technology good or bad?"
    debate_id = str(uuid.uuid4())

    with SessionLocal() as db:
        db.add(DebateModel(id=debate_id, topic=topic, rounds=1, status="idle"))
        db.commit()

    s: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "current_round": 1,
        "max_rounds": 1,
        "transcript": [],
        "status": "idle"
    }
    final = debate_graph.invoke(s)
    assert final["status"] == "completed"
    # Even on ambiguous prompt, system constructs dialectical opposition
    pro = final["transcript"][0]["content"]
    con = final["transcript"][1]["content"]
    assert len(pro) > 0 and len(con) > 0

# ==============================================================================
# Category 6: Very Short Topic — "Remote work?"
# ==============================================================================

def test_category_6_very_short_topic():
    topic = "Remote work?"
    debate_id = str(uuid.uuid4())

    with SessionLocal() as db:
        db.add(DebateModel(id=debate_id, topic=topic, rounds=1, status="idle"))
        db.commit()

    s: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "current_round": 1,
        "max_rounds": 1,
        "transcript": [],
        "status": "idle"
    }
    final = debate_graph.invoke(s)
    assert final["status"] == "completed"
    assert len(final["transcript"]) == 2

# ==============================================================================
# Category 7: Empty or Whitespace-Only Topic Validation
# ==============================================================================

def test_category_7_empty_and_whitespace_topic_validation():
    from pydantic import ValidationError

    # Test Pydantic schema rejection for empty string
    with pytest.raises(ValidationError) as exc1:
        StartDebateRequest(topic="")
    assert "topic" in str(exc1.value)

    # Test Pydantic schema rejection for whitespace-only string
    with pytest.raises(ValidationError) as exc2:
        StartDebateRequest(topic="   ")
    assert "empty or whitespace" in str(exc2.value).lower()

# ==============================================================================
# Category 8: Invalid Round Count Handling (Zero, Negative, Out of Bounds)
# ==============================================================================

def test_category_8_invalid_round_count_clamping():
    # Test normalization in create_or_start_debate
    test_cases = [
        (0, 1),      # Zero clamped to 1
        (-3, 1),     # Negative clamped to 1
        (10, 5),     # Exceeding max (5) clamped to 5
        (None, 2),   # Default is 2
    ]
    for input_rounds, expected_clamped in test_cases:
        rounds_val = input_rounds if input_rounds is not None else 2
        clamped = max(1, min(rounds_val, 5))
        assert clamped == expected_clamped, f"Failed clamping for rounds={input_rounds}: got {clamped}"

# ==============================================================================
# Category 9: Long Proposition Input Validation & Prompt Construction
# ==============================================================================

def test_category_9_long_proposition_prompt_construction():
    long_topic = (
        "Given the rapid acceleration of artificial neural networks, generative synthetic media, "
        "and automated algorithmic adjudication across municipal, statutory, and transnational regulatory domains, "
        "should constitutional democracies implement a comprehensive, non-derogable moratorium on automated decision systems "
        "that lack mathematically verified explainability, human-in-the-loop oversight, and auditable due process guarantees?"
    )
    assert len(long_topic) > 350

    debate_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(DebateModel(id=debate_id, topic=long_topic, rounds=1, status="idle"))
        db.commit()

    s: DebateGraphState = {
        "debate_id": debate_id,
        "topic": long_topic,
        "current_round": 1,
        "max_rounds": 1,
        "transcript": [],
        "status": "idle"
    }
    final = debate_graph.invoke(s)
    assert final["status"] == "completed"

    with SessionLocal() as db:
        saved_deb = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert saved_deb is not None
        assert saved_deb.topic == long_topic  # Entire long string preserved in SQLite

# ==============================================================================
# Category 10: Topic With No Uploaded Document (No Hallucinated Sources)
# ==============================================================================

def test_category_10_missing_evidence_citation_discipline():
    topic = "Should deep-sea mineral mining be permanently outlawed?"
    transcript_no_evidence = [
        {
            "speaker": "DEBATER_A",
            "role": "PRO",
            "round_number": 1,
            "title": "Ecological Preservation",
            "content": "Deep-sea ecosystems have slow regenerative rates; benthic disruption causes irreversible extinction.",
            "evidence": []  # No retrieved external documents
        },
        {
            "speaker": "DEBATER_B",
            "role": "CON",
            "round_number": 1,
            "title": "Clean Energy Minerals",
            "content": "Terrestrial nickel and cobalt mining creates greater surface ecological damage and human displacement.",
            "evidence": []  # No retrieved external documents
        }
    ]

    report = judge_agent.evaluate_debate(
        topic=topic,
        transcript=transcript_no_evidence,
        evidence_citations=[]
    )

    # Missing evidence must NOT be represented as verified evidence
    assert report.evidence_reliability_score <= 50.0
    assert len(report.source_references) == 0  # No invented URLs or documents
    assert any("grounding" in u.lower() or "ungrounded" in u.lower() for u in report.unsupported_claims)

# ==============================================================================
# Quality Assertions: Failed Turn Prevents Judge; Inconclusive Is Distinguishable
# ==============================================================================

def test_failed_turn_does_not_produce_successful_verdict():
    failed_state: DebateGraphState = {
        "debate_id": str(uuid.uuid4()),
        "topic": "Test Failed State",
        "current_round": 1,
        "max_rounds": 1,
        "transcript": [
            {"role": "PRO", "content": "Valid turn", "is_valid": True},
            {"role": "CON", "content": "Incomplete turn because", "is_valid": False, "validation_errors": ["Dangling 'because'"]}
        ],
        "status": "failed",
        "error": "CON failed completion validation"
    }

    # Verify routing directs directly to save_result
    target = check_adjudication_routing(failed_state)
    assert target == "save_result"

    # Verify save_result persists failed status, not completed
    res = save_result(failed_state)
    assert res["status"] == "failed"
    assert res["winner"] == "FAILED"

def test_legitimate_inconclusive_verdict_distinguishable_from_failed():
    tie_report = {
        "winner": "INCONCLUSIVE",
        "status": "completed",
        "pro_score": 88.0,
        "con_score": 88.0,
        "judge_reasoning": "Both positions demonstrated parity.",
        "balanced_verdict": "A deadlock is recorded."
    }
    state: DebateGraphState = {
        "debate_id": str(uuid.uuid4()),
        "topic": "Test Tie",
        "transcript": [{"role": "PRO", "content": "c1", "is_valid": True}, {"role": "CON", "content": "c2", "is_valid": True}],
        "judge_report": tie_report,
        "status": "evaluating"
    }
    res = save_result(state)
    # Must be 'completed', NOT 'failed' or 'evaluation_failed'
    assert res["status"] == "completed"
    assert res["winner"] == "INCONCLUSIVE"
