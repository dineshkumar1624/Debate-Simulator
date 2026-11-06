"""
Optimization I — End-to-End Workflow Integrity Test Suite.

Audits the AI Debate Simulator after Optimizations F, G, and H against 12 mandatory scenarios:
1. Scenario 1: A valid debate completes with the requested number of rounds.
2. Scenario 2: Each round contains expected PRO and CON turns in correct order.
3. Scenario 3: Judge evaluation runs strictly after final CON turn is committed.
4. Scenario 4: Truncated response undergoes bounded recovery.
5. Scenario 5: Failed model load produces failed debate status, never fake success.
6. Scenario 6: Failed debate persists failure status and error message in database.
7. Scenario 7: Document-backed debate uses stored document context in prompt.
8. Scenario 8: General-topic debate obeys citation discipline (no fabricated sources in evaluation).
9. Scenario 9: Gemini API failure triggers local impartial judge fallback / structured failure.
10. Scenario 10: PRO-to-CON model sequential switching maintains integrity across rounds.
11. Scenario 11: Persisted database history matches serialized session schema.
12. Scenario 12: Entire pipeline executes on CPU (INFERENCE_DEVICE=cpu).
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import pytest
import torch
from unittest.mock import patch, MagicMock

from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel, DebateRoundModel, JudgeEvaluationModel
from app.models.document import DocumentModel, DocumentChunkModel
from app.schemas.debate import (
    DebateSessionSchema,
    DebateConfigSchema,
    DebateRoundSchema,
    DebateTurnSchema,
    DebateSynthesisSchema,
    EvidenceItemSchema,
)
from app.schemas.judge import JudgeReportSchema, JudgeRoundPoint
from app.graph.debate_graph import debate_graph
from app.graph.state import DebateGraphState
from app.graph.nodes import (
    initialize_debate,
    retrieve_pro_evidence,
    pro_agent_node,
    save_pro_message,
    retrieve_con_evidence,
    con_agent_node,
    save_con_message,
    compile_complete_transcript,
    judge_agent_node,
    validate_judge_output,
    save_result,
)
from app.agents.pro_agent import pro_agent
from app.agents.con_agent import con_agent
from app.agents.judge_agent import judge_agent
from app.services.gemini_judge_service import gemini_judge_service
from app.services.rag_service import rag_service
from app.services.response_validator import ResponseValidator, response_validator, ValidationResult
from app.llm.model_manager import local_model_manager, LocalModelManager
from app.core.config import settings


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Ensure database tables exist and mock mode is active for safe offline testing."""
    Base.metadata.create_all(bind=engine)
    local_model_manager.mock_mode = True
    yield
    local_model_manager.mock_mode = True


@pytest.fixture
def debate_cleanup():
    created_ids = []
    yield created_ids
    with SessionLocal() as db:
        for d_id in created_ids:
            db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == d_id).delete()
            db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == d_id).delete()
            db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == d_id).delete()
            db.query(DebateModel).filter(DebateModel.id == d_id).delete()
        db.commit()


def create_initial_debate_record(db, debate_id: str, topic: str, rounds: int = 2) -> DebateModel:
    debate = DebateModel(
        id=debate_id,
        topic=topic,
        debater_a_model="gemma-4-E4B-it",
        debater_b_model="Qwen2.5-VL-7B-Instruct",
        judge_model="gemini-3.8-flash",
        rounds=rounds,
        evidence_mode=True,
        strict_fact_checking=True,
        source_scope="general_topic",
        status="debating"
    )
    db.add(debate)
    db.commit()
    return debate


# --------------------------------------------------------------------------
# Scenario 1: A valid debate completes with the requested number of rounds
# --------------------------------------------------------------------------
def test_scenario_1_valid_debate_completes_with_requested_rounds(debate_cleanup):
    debate_id = f"audit-sc1-{uuid.uuid4()}"
    debate_cleanup.append(debate_id)

    with SessionLocal() as db:
        create_initial_debate_record(db, debate_id, "Should AI be regulated?", rounds=2)

    initial_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": "Should AI be regulated?",
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
        "resume_target": None,
        "status": "debating",
        "error": None
    }

    final_state = debate_graph.invoke(initial_state)

    assert final_state["status"] == "completed"
    assert len(final_state["transcript"]) == 4  # 2 rounds * 2 turns
    assert final_state["judge_report"] is not None
    assert final_state["judge_report"]["status"] == "completed"

    with SessionLocal() as db:
        debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert debate is not None
        assert debate.status == "completed"
        assert debate.error_message is None
        rounds = db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == debate_id).all()
        assert len(rounds) == 2
        for r in rounds:
            assert r.status == "completed"


# --------------------------------------------------------------------------
# Scenario 2: Each round contains expected PRO and CON turns in correct order
# --------------------------------------------------------------------------
def test_scenario_2_turns_alternate_strictly_pro_then_con(debate_cleanup):
    debate_id = f"audit-sc2-{uuid.uuid4()}"
    debate_cleanup.append(debate_id)

    with SessionLocal() as db:
        create_initial_debate_record(db, debate_id, "Should homework be mandatory?", rounds=2)

    initial_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": "Should homework be mandatory?",
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
        "resume_target": None,
        "status": "debating",
        "error": None
    }

    final_state = debate_graph.invoke(initial_state)
    transcript = final_state["transcript"]

    assert len(transcript) == 4
    # Round 1
    assert transcript[0]["round_number"] == 1 and transcript[0]["role"] == "PRO" and transcript[0]["speaker"] == "DEBATER_A"
    assert transcript[1]["round_number"] == 1 and transcript[1]["role"] == "CON" and transcript[1]["speaker"] == "DEBATER_B"
    # Round 2
    assert transcript[2]["round_number"] == 2 and transcript[2]["role"] == "PRO" and transcript[2]["speaker"] == "DEBATER_A"
    assert transcript[3]["round_number"] == 2 and transcript[3]["role"] == "CON" and transcript[3]["speaker"] == "DEBATER_B"

    # Verify database persistence order matches transcript
    with SessionLocal() as db:
        messages = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.round_number, DebateMessageModel.created_at).all()
        assert len(messages) == 4
        assert [m.role for m in messages] == ["PRO", "CON", "PRO", "CON"]
        assert [m.round_number for m in messages] == [1, 1, 2, 2]


# --------------------------------------------------------------------------
# Scenario 3: Judge evaluation runs strictly after final CON turn is committed
# --------------------------------------------------------------------------
def test_scenario_3_judge_evaluation_strictly_after_final_con(debate_cleanup):
    debate_id = f"audit-sc3-{uuid.uuid4()}"
    debate_cleanup.append(debate_id)

    with SessionLocal() as db:
        create_initial_debate_record(db, debate_id, "Should renewable energy be subsidized?", rounds=1)

    eval_invoked_con_committed = []

    def mock_evaluate_debate(topic, transcript, evidence_citations=None, max_retries=2):
        # Verify in DB that final CON turn is already committed before judge evaluates
        with SessionLocal() as db:
            con_msg = db.query(DebateMessageModel).filter(
                DebateMessageModel.debate_id == debate_id,
                DebateMessageModel.round_number == 1,
                DebateMessageModel.role == "CON"
            ).first()
            eval_invoked_con_committed.append(con_msg is not None)
        return JudgeReportSchema(
            pro_score=85.0,
            con_score=83.0,
            winner="PRO",
            status="completed",
            pro_strengths=["Clear factual presentation."],
            pro_weaknesses=[],
            con_strengths=["Valid cost concerns."],
            con_weaknesses=[],
            round_points=[JudgeRoundPoint(
                round_number=1,
                pro_summary="Clean energy transition necessity",
                con_summary="Economic transition burdens",
                key_takeaway="Empirical analysis favors clean transition"
            )],
            main_arguments=["Subsidies accelerate clean transition"],
            main_counterarguments=["Market disruption concerns"],
            supported_claims=["Solar cost has fallen over 80%."],
            unsupported_claims=[],
            judge_reasoning="PRO provided grounded transition timelines.",
            balanced_verdict="PRO demonstrated superior empirical support.",
            evidence_reliability_score=88.0,
            source_references=[]
        )

    initial_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": "Should renewable energy be subsidized?",
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
        "resume_target": None,
        "status": "debating",
        "error": None
    }

    with patch.object(judge_agent, "evaluate_debate", side_effect=mock_evaluate_debate):
        final_state = debate_graph.invoke(initial_state)

    assert len(eval_invoked_con_committed) == 1
    assert eval_invoked_con_committed[0] is True, "Judge was invoked before final CON turn was committed in database"
    assert final_state["status"] == "completed"


# --------------------------------------------------------------------------
# Scenario 4: Truncated response undergoes bounded recovery
# --------------------------------------------------------------------------
def test_scenario_4_truncated_response_bounded_recovery():
    # 1. Test validator identifies truncation cleanly
    truncated_text = (
        "Target: PRO claims AI tools accelerate synthesis.\n"
        "Counterarguments: While productivity gains are reported in controlled trials, student retention fails when the"
    )
    initial_val = ResponseValidator.validate(truncated_text, role="CON", max_tokens_configured=32, actual_tokens_generated=32)
    assert initial_val.is_valid is False
    assert initial_val.is_truncated is True
    assert initial_val.finish_reason == "length"

    # 2. Test bounded recovery completes the sentence
    mock_mm = MagicMock()
    mock_mm.generate.return_value = " student fails to retain core scientific concepts."

    recovered_text, final_val = ResponseValidator.attempt_recovery(
        role="CON",
        text=truncated_text,
        system_prompt="sys",
        user_prompt="usr",
        validation=initial_val,
        model_manager=mock_mm,
        max_continuation_tokens=36
    )

    assert final_val.is_valid is True
    assert final_val.recovery_successful is True
    assert "student fails to retain core scientific concepts." in recovered_text
    assert mock_mm.generate.call_count == 1


# --------------------------------------------------------------------------
# Scenario 5: Failed model load produces failed debate status, never fake success
# --------------------------------------------------------------------------
def test_scenario_5_failed_model_load_produces_failed_status(debate_cleanup):
    debate_id = f"audit-sc5-{uuid.uuid4()}"
    debate_cleanup.append(debate_id)

    with SessionLocal() as db:
        create_initial_debate_record(db, debate_id, "Should nuclear power be expanded?", rounds=2)

    state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": "Should nuclear power be expanded?",
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 2,
        "current_speaker": "PRO",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": {
            "speaker": "DEBATER_A",
            "role": "PRO",
            "round_number": 1,
            "title": "Failed Load Turn",
            "content": "",
            "confidence": 0.0,
            "is_valid": False,
            "is_truncated": False,
            "validation_errors": ["Model failed to load due to insufficient RAM or missing checkpoint"],
            "finish_reason": "malformed"
        },
        "current_con_turn": None,
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "transcript": [],
        "judge_report": None,
        "resume_target": None,
        "status": "debating",
        "error": None
    }

    # Execute save_pro_message with failed turn
    out_save = save_pro_message(state)
    assert out_save["status"] == "failed"
    assert "failed completion validation" in out_save["error"]

    state.update(out_save)
    final_save = save_result(state)
    assert final_save["status"] == "failed"
    assert final_save["winner"] == "FAILED"

    # Verify database state refuses fake success
    with SessionLocal() as db:
        debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert debate is not None
        assert debate.status == "failed"
        assert "failed completion validation" in debate.error_message


# --------------------------------------------------------------------------
# Scenario 6: Failed debate persists failure status and error message in database
# --------------------------------------------------------------------------
def test_scenario_6_failed_debate_persists_failure_in_database(debate_cleanup):
    debate_id = f"audit-sc6-{uuid.uuid4()}"
    debate_cleanup.append(debate_id)

    with SessionLocal() as db:
        create_initial_debate_record(db, debate_id, "Should social media be restricted for minors?", rounds=2)

    state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": "Should social media be restricted for minors?",
        "document_ids": [],
        "source_scope": "general_topic",
        "current_round": 1,
        "max_rounds": 2,
        "current_speaker": "PRO",
        "current_pro_evidence": [],
        "current_con_evidence": [],
        "pro_evidence_context": "",
        "con_evidence_context": "",
        "current_pro_turn": {
            "speaker": "DEBATER_A",
            "role": "PRO",
            "round_number": 1,
            "title": "Failed PRO Turn",
            "content": "Incomplete sentence without end",
            "confidence": 0.0,
            "is_valid": False,
            "is_truncated": True,
            "validation_errors": ["Response ended prematurely with incomplete sentence"],
            "finish_reason": "length"
        },
        "current_con_turn": None,
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "transcript": [],
        "judge_report": None,
        "resume_target": None,
        "status": "debating",
        "error": None
    }

    # Execute save_pro_message and save_result
    save_pro_out = save_pro_message(state)
    state.update(save_pro_out)
    save_result(state)

    with SessionLocal() as db:
        debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        assert debate is not None
        assert debate.status == "failed"
        assert debate.error_message is not None
        assert "incomplete sentence" in debate.error_message.lower()

        eval_rec = db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).first()
        assert eval_rec is not None
        assert eval_rec.status == "failed"
        assert eval_rec.winner == "FAILED"
        assert eval_rec.pro_score == 0.0
        assert eval_rec.con_score == 0.0


# --------------------------------------------------------------------------
# Scenario 7: Document-backed debate uses stored document context in prompt
# --------------------------------------------------------------------------
def test_scenario_7_document_backed_debate_uses_stored_document_context(debate_cleanup):
    debate_id = f"audit-sc7-{uuid.uuid4()}"
    doc_id = f"audit-doc-{uuid.uuid4()}"
    debate_cleanup.append(debate_id)

    with SessionLocal() as db:
        create_initial_debate_record(db, debate_id, "Should high-speed rail be federally funded?", rounds=2)
        doc = DocumentModel(
            id=doc_id,
            name="rail_study.txt",
            file_type="txt",
            file_size="1 KB",
            status="ready"
        )
        chunk = DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=0,
            content="High-speed rail investments show a 3.4x return on regional economic mobility according to DOT reports.",
            page_number=1
        )
        db.add(doc)
        db.add(chunk)
        db.commit()

    try:
        mock_evidence = [{
            "id": "chunk-1",
            "content": "High-speed rail investments show a 3.4x return on regional economic mobility according to DOT reports.",
            "source": "rail_study.txt",
            "page": 1,
            "document_id": doc_id
        }]

        with patch.object(rag_service, "retrieve_evidence_for_turn", return_value=mock_evidence):
            state: DebateGraphState = {
                "debate_id": debate_id,
                "topic": "Should high-speed rail be federally funded?",
                "document_ids": [doc_id],
                "source_scope": "document",
                "current_round": 1,
                "max_rounds": 2,
                "current_speaker": "PRO",
                "latest_con_argument": None
            }
            ev_state = retrieve_pro_evidence(state)
            assert "3.4x return" in ev_state["pro_evidence_context"]
            assert ev_state["current_pro_evidence"][0]["document_id"] == doc_id
    finally:
        with SessionLocal() as db:
            db.query(DocumentChunkModel).filter(DocumentChunkModel.document_id == doc_id).delete()
            db.query(DocumentModel).filter(DocumentModel.id == doc_id).delete()
            db.commit()


# --------------------------------------------------------------------------
# Scenario 8: General-topic debate obeys citation discipline
# --------------------------------------------------------------------------
def test_scenario_8_general_topic_debate_obeys_citation_discipline():
    # Simulate a raw Judge response that hallucinated citations in a general-topic debate
    hallucinated_raw = {
        "pro_score": 88.0,
        "con_score": 85.0,
        "winner": "PRO",
        "status": "completed",
        "pro_strengths": ["Well argued"],
        "pro_weaknesses": [],
        "con_strengths": ["Good points"],
        "con_weaknesses": [],
        "round_points": [],
        "main_arguments": ["AI benefits"],
        "main_counterarguments": ["AI risks"],
        "supported_claims": ["AI improves productivity"],
        "unsupported_claims": [],
        "judge_reasoning": "Strong reasoning",
        "balanced_verdict": "PRO won",
        "evidence_reliability_score": 95.0,
        "source_references": ["https://fake-citation.org/paper.pdf", "Nature 2026 Hallucinated Article"]
    }

    transcript = [
        {"speaker": "DEBATER_A", "role": "PRO", "round_number": 1, "title": "Arg", "content": "AI is good.", "evidence": []},
        {"speaker": "DEBATER_B", "role": "CON", "round_number": 1, "title": "Arg", "content": "AI is risky.", "evidence": []}
    ]

    # No evidence citations pool provided (general-topic without retrieved grounding)
    cleaned = gemini_judge_service._apply_citation_discipline(hallucinated_raw, transcript, evidence_citations=[])

    # Hallucinated citations must be completely purged
    assert cleaned["source_references"] == [], "Citation discipline failed to purge fabricated sources"
    # Evidence reliability score must be capped at 50.0 for ungrounded debates
    assert cleaned["evidence_reliability_score"] <= 50.0
    # Unsupported claims must record lack of verified grounding
    assert any("grounding" in str(u).lower() or "unsupported" in str(u).lower() for u in cleaned["unsupported_claims"])


# --------------------------------------------------------------------------
# Scenario 9: Gemini API failure triggers local impartial judge fallback / structured failure
# --------------------------------------------------------------------------
def test_scenario_9_gemini_api_failure_handled_safely():
    # 1. When calling gemini_judge_service directly and Gemini API raises an exception
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("ResourceExhausted: 429 Quota Exceeded")

    with patch.object(gemini_judge_service, "get_client", return_value=mock_client):
        with patch.object(gemini_judge_service, "validate_configuration", return_value="dummy_key"):
            report = gemini_judge_service.evaluate_debate(
                topic="Should space exploration be privatized?",
                transcript=[{"speaker": "DEBATER_A", "role": "PRO", "content": "Space exploration fosters innovation."}],
                evidence_citations=[],
                max_retries=1
            )

    assert report.status == "failed"
    assert report.winner == "FAILED"
    assert report.pro_score == 0.0
    assert report.con_score == 0.0
    assert "ResourceExhausted" in report.error_message
    assert report.source_references == []

    # 2. When offline mock mode is active, judge_agent falls back to local impartial adjudication
    local_model_manager.mock_mode = True
    with patch.object(gemini_judge_service, "_client", None):
        offline_report = judge_agent.evaluate_debate(
            topic="Should space exploration be privatized?",
            transcript=[
                {"speaker": "DEBATER_A", "role": "PRO", "round_number": 1, "title": "Affirmative", "content": "Private space fosters capital investment.", "evidence": []},
                {"speaker": "DEBATER_B", "role": "CON", "round_number": 1, "title": "Opposition", "content": "Private space prioritizes profit over public science.", "evidence": []}
            ],
            evidence_citations=[]
        )
        assert offline_report.status == "completed"
        assert offline_report.winner in ["PRO", "CON", "TIE", "INCONCLUSIVE"]
        assert offline_report.pro_score > 0
        assert offline_report.con_score > 0


# --------------------------------------------------------------------------
# Scenario 10: PRO-to-CON model sequential switching maintains integrity
# --------------------------------------------------------------------------
def test_scenario_10_sequential_model_switching_maintains_integrity():
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
            # 1. Start with no loaded model
            assert len(mgr._loaded_models) == 0

            # 2. Load PRO model
            with patch("transformers.AutoModelForCausalLM.from_pretrained", return_value=mock_pro_model):
                m_pro, _ = mgr.load_model("PRO")
                assert m_pro == mock_pro_model
                assert len(mgr._loaded_models) == 1
                assert "PRO" in mgr._loaded_models
                assert "CON" not in mgr._loaded_models

            # 3. Load CON model: PRO must be evicted prior to CON being assigned
            with patch("transformers.Qwen2_5_VLForConditionalGeneration.from_pretrained", return_value=mock_con_model):
                m_con, _ = mgr.load_model("CON")
                assert m_con == mock_con_model
                assert len(mgr._loaded_models) == 1
                assert "CON" in mgr._loaded_models
                assert "PRO" not in mgr._loaded_models

    # 4. Clean teardown unloads all models
    mgr.unload_all()
    assert len(mgr._loaded_models) == 0


# --------------------------------------------------------------------------
# Scenario 11: Persisted database history matches serialized session schema
# --------------------------------------------------------------------------
def test_scenario_11_persisted_database_matches_serialized_session_schema(debate_cleanup):
    debate_id = f"audit-sc11-{uuid.uuid4()}"
    debate_cleanup.append(debate_id)

    with SessionLocal() as db:
        debate = create_initial_debate_record(db, debate_id, "Should carbon taxes be universally mandated?", rounds=1)
        debate.status = "completed"

        msg_pro = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Carbon Pricing Imperative",
            content="Internalizing carbon costs provides market incentive for rapid decarbonization.",
            confidence=93.5,
            evidence_references=[{"id": "ev-1", "claim": "Emissions drop", "source": "EPA", "verdict": "supported", "confidenceScore": 95.0}]
        )
        msg_con = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_B",
            role="CON",
            title="Regressive Economic Burden",
            content="Universal carbon taxes disproportionately penalize low-income working families.",
            confidence=91.0,
            evidence_references=[]
        )
        rnd = DebateRoundModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            status="completed"
        )
        evaluation = JudgeEvaluationModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            pro_score=87.0,
            con_score=84.0,
            winner="PRO",
            status="completed",
            pro_strengths=["Clear economic modeling"],
            pro_weaknesses=[],
            con_strengths=["Highlighted distributional equity"],
            con_weaknesses=[],
            key_points=[{"round": 1, "pro_point": "Carbon price", "con_point": "Tax regressivity", "winner": "PRO"}],
            judge_reasoning="PRO established structural market necessity.",
            balanced_verdict="PRO defended market efficiency effectively.",
            evidence_reliability_score=90.0,
            raw_payload={"status": "completed"}
        )
        db.add_all([msg_pro, msg_con, rnd, evaluation])
        db.commit()

        # Re-query debate with eager associations
        db_debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()

        # Format session schema identically to API serializer
        config = DebateConfigSchema(
            topic=db_debate.topic,
            debaterAModel=db_debate.debater_a_model,
            debaterBModel=db_debate.debater_b_model,
            judgeModel=db_debate.judge_model,
            rounds=db_debate.rounds,
            evidenceMode=db_debate.evidence_mode,
            strictFactChecking=db_debate.strict_fact_checking,
            documentId=db_debate.document_id,
            sourceScope=db_debate.source_scope
        )

        sorted_messages = sorted(db_debate.messages, key=lambda m: (m.round_number, 0 if m.role == "PRO" else 1))
        turns = [
            DebateTurnSchema(
                speaker=m.speaker,
                role=m.role,
                content=m.content,
                timestamp=m.created_at.strftime("%I:%M:%S %p") if m.created_at else "Now",
                title=m.title,
                confidence=m.confidence,
                evidence=[EvidenceItemSchema(**ev) for ev in (m.evidence_references or [])]
            )
            for m in sorted_messages
        ]

        synthesis = DebateSynthesisSchema(
            summary=db_debate.evaluation.judge_reasoning,
            keyConsensus=db_debate.evaluation.pro_strengths,
            keyContentions=db_debate.evaluation.con_strengths,
            evidenceReliabilityScore=db_debate.evaluation.evidence_reliability_score,
            balancedVerdict=db_debate.evaluation.balanced_verdict
        )

        session = DebateSessionSchema(
            id=db_debate.id,
            topic=db_debate.topic,
            createdAt="Today",
            status=db_debate.status,
            config=config,
            rounds=[DebateRoundSchema(roundNumber=1, turns=turns)],
            synthesis=synthesis
        )

        assert session.id == debate_id
        assert session.status == "completed"
        assert len(session.rounds) == 1
        assert len(session.rounds[0].turns) == 2
        assert session.rounds[0].turns[0].role == "PRO"
        assert session.rounds[0].turns[1].role == "CON"
        assert session.synthesis.balancedVerdict == "PRO defended market efficiency effectively."


# --------------------------------------------------------------------------
# Scenario 12: Entire pipeline executes on CPU (INFERENCE_DEVICE=cpu)
# --------------------------------------------------------------------------
def test_scenario_12_cpu_execution_compatibility():
    assert settings.INFERENCE_DEVICE == "cpu", f"INFERENCE_DEVICE expected 'cpu', got '{settings.INFERENCE_DEVICE}'"

    mgr = LocalModelManager()
    assert mgr.device == "cpu"
    assert mgr.device_setting == "cpu"

    for role in ["PRO", "CON", "JUDGE"]:
        input_device = mgr.get_input_target_device(role)
        assert input_device == torch.device("cpu"), f"Role {role} input target device must be CPU, got {input_device}"
