import pytest
import uuid
from typing import Dict, Any
from unittest.mock import MagicMock, patch

from app.services.response_validator import ResponseValidator, response_validator, ValidationResult
from app.graph.nodes import (
    save_pro_message,
    save_con_message,
    compile_complete_transcript,
    judge_agent_node,
    check_pro_turn_routing,
    should_continue_debate,
    check_adjudication_routing,
    save_result
)
from app.graph.state import DebateGraphState
from app.database.session import SessionLocal
from app.models.debate import DebateModel, DebateRoundModel, DebateMessageModel, JudgeEvaluationModel


# ==============================================================================
# 1. Normal Complete PRO and CON Responses
# ==============================================================================

def test_normal_complete_con_response():
    """
    Verifies that a well-structured, complete CON response passes multi-criteria validation
    with finish_reason='stop' and zero errors.
    """
    complete_text = (
        "Target: The affirmative claims that AI tools provide essential cognitive scaffolding.\n"
        "Counterarguments:\n"
        "1. Unsupervised reliance reduces foundational memory encoding by 38% in secondary learners.\n"
        "2. Automated scaffolding fosters passive task-completion rather than genuine dialectical synthesis.\n"
        "Conclusion: Unbounded AI adoption undermines pedagogical foundations and should be strictly regulated."
    )
    result = ResponseValidator.validate(complete_text, role="CON", max_tokens_configured=128, actual_tokens_generated=72)
    assert result.is_valid is True
    assert result.is_truncated is False
    assert result.finish_reason == "stop"
    assert len(result.errors) == 0
    assert result.has_unfinished_sentence is False
    assert result.has_placeholder_citation is False


def test_normal_complete_pro_response():
    """
    Verifies that a well-structured PRO response with empirical grounding passes validation cleanly.
    """
    complete_pro = (
        "# The Affirmative Framework\n\n"
        "Cognitive scaffolding provided by generative models enables learners to bridge complex conceptual gaps. "
        "Empirical benchmarks demonstrate a 42% acceleration in post-graduate analytical throughput when "
        "guided by structured verification rubrics. Therefore, integrating bounded AI tools prepares students "
        "for modern technical demands while preserving academic rigor."
    )
    result = ResponseValidator.validate(complete_pro, role="PRO", max_tokens_configured=128, actual_tokens_generated=68)
    assert result.is_valid is True
    assert result.finish_reason == "stop"
    assert len(result.errors) == 0


# ==============================================================================
# 2. Output Ending Due to Generation Token Limit
# ==============================================================================

def test_output_ending_because_of_token_limit():
    """
    Verifies that when actual generated tokens hit the configured ceiling, finish_reason
    is correctly classified as 'length' and truncation is flagged.
    """
    truncated_text = (
        "Target: Refuting the affirmative claim on student productivity.\n"
        "Counterarguments: While productivity gains are reported in controlled trials, student retention fails when the"
    )
    result = ResponseValidator.validate(
        truncated_text,
        role="CON",
        max_tokens_configured=32,
        actual_tokens_generated=32
    )
    assert result.is_valid is False
    assert result.is_truncated is True
    assert result.finish_reason == "length"
    assert any("ends on dangling grammatical connector" in e or "terminal punctuation" in e for e in result.errors)


# ==============================================================================
# 3. Abrupt Mid-Sentence Ending
# ==============================================================================

def test_abrupt_mid_sentence_ending():
    """
    Verifies detection of outputs ending mid-sentence without terminal punctuation or on dangling connectors.
    """
    dangling_text = "The core limitation of algorithmic evaluation rests on the fundamental"
    result = ResponseValidator.validate(dangling_text, role="CON")
    assert result.is_valid is False
    assert result.has_unfinished_sentence is True
    assert result.is_truncated is True
    assert any("terminal punctuation" in e for e in result.errors)


# ==============================================================================
# 4. Malformed or Missing Required Response Fields
# ==============================================================================

def test_malformed_empty_response():
    """
    Verifies rejection of empty or whitespace-only response.
    """
    result = ResponseValidator.validate("   \n\t  ", role="CON")
    assert result.is_valid is False
    assert result.finish_reason == "empty"
    assert "Response content is empty." in result.errors


def test_malformed_heading_only_response():
    """
    Verifies rejection of responses containing only markdown headers with zero body text.
    """
    heading_only = "# Round 1 Opposition\n## Target\n## Counterarguments\n## Conclusion"
    result = ResponseValidator.validate(heading_only, role="CON")
    assert result.is_valid is False
    assert "Argument Body" in result.missing_sections
    assert any("consists entirely of section headings" in e for e in result.errors)


# ==============================================================================
# 5. Valid Short Response (Not Rejected For Conciseness)
# ==============================================================================

def test_valid_short_response():
    """
    Verifies that a concise but syntactically complete response (>= 15 words with punctuation)
    is accepted and not penalized simply for brevity.
    """
    concise_valid = (
        "We counter that unmonitored AI tools degrade fundamental critical reasoning. "
        "Rigorous empirical limits must precede classroom deployment."
    )
    result = ResponseValidator.validate(concise_valid, role="CON")
    assert result.is_valid is True
    assert result.finish_reason == "stop"
    assert len(result.errors) == 0


# ==============================================================================
# 6. Successful Bounded Recovery: Bounded Continuation
# ==============================================================================

def test_successful_bounded_recovery_continuation():
    """
    Verifies that an unfinished trailing clause is successfully completed via bounded continuation
    without repeating existing text.
    """
    incomplete_text = (
        "Target: PRO claims AI accelerates synthesis.\n"
        "Counterargument: Without foundational comprehension, synthesis is purely superficial and the"
    )
    initial_val = ResponseValidator.validate(incomplete_text, role="CON")
    assert initial_val.is_valid is False

    mock_mm = MagicMock()
    mock_mm.generate.return_value = " student fails to retain core scientific concepts."

    recovered_text, final_val = ResponseValidator.attempt_recovery(
        role="CON",
        text=incomplete_text,
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


# ==============================================================================
# 7. Successful Bounded Recovery: Placeholder Sanitization
# ==============================================================================

def test_successful_placeholder_sanitization():
    """
    Verifies that empty/placeholder citation patterns like [Schunk and Pajares](year_of_study)
    are cleanly sanitized without corrupting the surrounding argument.
    """
    text_with_placeholder = (
        "Empirical research by [Schunk and Pajares](year_of_study) establishes that self-efficacy "
        "is mediated by deliberate cognitive struggle, which automated tools circumvent."
    )
    sanitized, was_modified = ResponseValidator.sanitize_placeholders(text_with_placeholder)
    assert was_modified is True
    assert "year_of_study" not in sanitized
    assert "Schunk and Pajares" in sanitized

    # Validate that sanitized output now passes cleanly
    val = ResponseValidator.validate(sanitized, role="CON")
    assert val.is_valid is True
    assert val.has_placeholder_citation is False


# ==============================================================================
# 8. Failed Recovery
# ==============================================================================

def test_failed_recovery_marks_failure_honestly():
    """
    Verifies that when bounded continuation produces further invalid text or crashes,
    recovery is honestly marked as unsuccessful without fabricating content.
    """
    incomplete = "The opposition firmly notes that"
    initial_val = ResponseValidator.validate(incomplete, role="CON")

    mock_mm = MagicMock()
    # Mock model fails to complete or produces another dangling fragment
    mock_mm.generate.return_value = " because the"

    recovered_text, final_val = ResponseValidator.attempt_recovery(
        role="CON",
        text=incomplete,
        system_prompt="sys",
        user_prompt="usr",
        validation=initial_val,
        model_manager=mock_mm
    )

    assert final_val.recovery_attempted is True
    assert final_val.recovery_successful is False
    assert final_val.is_valid is False


# ==============================================================================
# 9. No Duplicate Messages or Rounds Created During Persistence
# ==============================================================================

def test_no_duplicate_messages_or_rounds():
    """
    Verifies that saving turn messages and rounds is completely idempotent.
    Repeated saves update existing records without creating duplicate rows.
    """
    test_debate_id = str(uuid.uuid4())
    with SessionLocal() as db:
        deb = DebateModel(id=test_debate_id, topic="Test Idempotence", status="debating")
        db.add(deb)
        db.commit()

    state: DebateGraphState = {
        "debate_id": test_debate_id,
        "topic": "Test Idempotence",
        "current_round": 1,
        "max_rounds": 2,
        "current_pro_turn": {
            "title": "Initial PRO Title",
            "content": "Initial complete substantive affirmative thesis statement with full evidence.",
            "confidence": 92.0,
            "is_valid": True,
            "is_truncated": False,
            "validation_errors": []
        },
        "current_pro_evidence": [],
        "transcript": [],
        "status": "debating"
    }

    # Save once
    res1 = save_pro_message(state)
    assert len(res1["transcript"]) == 1

    # Update turn payload and save again (simulating recovery update)
    state["transcript"] = res1["transcript"]
    state["current_pro_turn"]["content"] = "Updated recovered substantive affirmative thesis with full evidence."
    res2 = save_pro_message(state)

    # Transcript should still have exactly 1 item
    assert len(res2["transcript"]) == 1
    assert "Updated recovered" in res2["transcript"][0]["content"]

    with SessionLocal() as db:
        msgs = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == test_debate_id,
            DebateMessageModel.round_number == 1,
            DebateMessageModel.role == "PRO"
        ).all()
        assert len(msgs) == 1
        assert "Updated recovered" in msgs[0].content


# ==============================================================================
# 10. Non-Invocation of Judge on Incomplete Turn
# ==============================================================================

def test_non_invocation_of_judge_on_incomplete_turn():
    """
    Verifies that the Judge is NOT called when state is marked failed due to an incomplete turn.
    Instead, adjudication is bypassed and an honest failed report is returned without calling Gemini API.
    """
    state: DebateGraphState = {
        "debate_id": str(uuid.uuid4()),
        "topic": "Test AI",
        "current_round": 1,
        "max_rounds": 2,
        "transcript": [
            {
                "speaker": "DEBATER_A",
                "role": "PRO",
                "round_number": 1,
                "content": "Valid affirmative framework.",
                "is_valid": True
            },
            {
                "speaker": "DEBATER_B",
                "role": "CON",
                "round_number": 1,
                "content": "Truncated opposition that stopped mid-sentence because the",
                "is_valid": False,
                "validation_errors": ["Ends on dangling grammatical connector 'the'"]
            }
        ],
        "status": "failed",
        "error": "Round 1 CON failed completion validation"
    }

    # Verify check_adjudication_routing directs directly to save_result
    target = check_adjudication_routing(state)
    assert target == "save_result"

    # Even if judge_agent_node was directly reached, it refuses to call the Judge API
    with patch("app.agents.judge_agent.judge_agent.evaluate_debate") as mock_eval:
        judge_res = judge_agent_node(state)
        mock_eval.assert_not_called()
        report = judge_res["judge_report"]
        assert report["winner"] == "FAILED"
        assert report["status"] == "failed"
        assert ("incomplete" in report["error_message"].lower() or "failed" in report["error_message"].lower())


# ==============================================================================
# 11. Judge Scoring Impartiality
# ==============================================================================

def test_judge_scoring_impartiality_without_bias():
    """
    Verifies that the Judge evaluates debates purely on substantive merit without
    artificially forcing CON to win or altering scores to compensate for failures.
    """
    from app.agents.judge_agent import judge_agent
    from app.schemas.judge import JudgeReportSchema, JudgeRoundPoint

    # Mock Gemini Judge API response
    mock_report = JudgeReportSchema(
        winner="PRO",
        status="completed",
        pro_score=88.5,
        con_score=78.0,
        judge_reasoning="PRO provided superior empirical evidence and direct rebuttal responsiveness.",
        balanced_verdict="PRO demonstrated clearer causality.",
        pro_strengths=["Strong empirical grounding"],
        pro_weaknesses=["Could address long-term secondary risks"],
        con_strengths=["Identified real retention concerns"],
        con_weaknesses=["Did not counter PRO's workforce readiness evidence"],
        round_points=[JudgeRoundPoint(round_number=1, pro_summary="Scaffolding argument", con_summary="Retention challenge", key_takeaway="PRO prevailed on evidence")]
    )

    with patch.object(judge_agent, "evaluate_debate", return_value=mock_report):
        state: DebateGraphState = {
            "debate_id": str(uuid.uuid4()),
            "topic": "Test AI",
            "current_round": 1,
            "max_rounds": 1,
            "transcript": [
                {"speaker": "DEBATER_A", "role": "PRO", "round_number": 1, "content": "Complete affirmative argument.", "is_valid": True},
                {"speaker": "DEBATER_B", "role": "CON", "round_number": 1, "content": "Complete negative argument.", "is_valid": True}
            ],
            "status": "evaluating"
        }
        res = judge_agent_node(state)
        assert res["judge_report"]["winner"] == "PRO"
        assert res["judge_report"]["pro_score"] == 88.5
        assert res["judge_report"]["con_score"] == 78.0


# ==============================================================================
# 12. Empty Citation Placeholder Handling
# ==============================================================================

def test_empty_citation_placeholder_detection():
    """
    Verifies detection of diverse ungrounded citation placeholders.
    """
    cases = [
        "Referencing [Schunk and Pajares](year_of_study) in our analysis.",
        "According to [Smith et al.](insert_source), memory decays rapidly.",
        "As documented in [citation needed], the effect is pronounced.",
        "Recent studies [ ](http://example.com) indicate significant divergence.",
    ]
    for text in cases:
        val = ResponseValidator.validate(text, role="CON")
        assert val.has_placeholder_citation is True, f"Failed to detect placeholder in: {text}"


# ==============================================================================
# 13. Persistence Status Correctness On Failed Turn
# ==============================================================================

def test_persistence_status_correctness():
    """
    Verifies that when a turn fails validation and recovery is not successful,
    the debate and round records in SQLite are marked 'failed' instead of claiming 'completed'.
    """
    test_id = str(uuid.uuid4())
    with SessionLocal() as db:
        deb = DebateModel(id=test_id, topic="Test Failure Persistence", status="debating")
        db.add(deb)
        db.commit()

    failed_turn = {
        "title": "Failed Turn",
        "content": "Incomplete sentence terminating abruptly because",
        "confidence": 80.0,
        "is_valid": False,
        "is_truncated": True,
        "validation_errors": ["Ends on dangling grammatical connector 'because'"],
        "finish_reason": "malformed"
    }

    state: DebateGraphState = {
        "debate_id": test_id,
        "topic": "Test Failure Persistence",
        "current_round": 1,
        "max_rounds": 2,
        "current_con_turn": failed_turn,
        "current_con_evidence": [],
        "transcript": [],
        "status": "debating"
    }

    res = save_con_message(state)
    assert res["status"] == "failed"

    with SessionLocal() as db:
        deb_db = db.query(DebateModel).filter(DebateModel.id == test_id).first()
        assert deb_db.status == "failed"
        assert "failed completion validation" in deb_db.error_message

        rnd_db = db.query(DebateRoundModel).filter(
            DebateRoundModel.debate_id == test_id,
            DebateRoundModel.round_number == 1
        ).first()
        assert rnd_db.status == "failed"


# ==============================================================================
# 14. Routing Guards
# ==============================================================================

def test_workflow_routing_guards():
    """
    Verifies conditional routing decisions under normal vs failed states.
    """
    normal_pro_state: DebateGraphState = {"status": "debating"}
    assert check_pro_turn_routing(normal_pro_state) == "retrieve_con_evidence"

    failed_pro_state: DebateGraphState = {"status": "failed"}
    assert check_pro_turn_routing(failed_pro_state) == "save_result"

    normal_con_state: DebateGraphState = {"status": "debating", "current_round": 1, "max_rounds": 2}
    assert should_continue_debate(normal_con_state) == "increment_round"

    finished_con_state: DebateGraphState = {"status": "debating", "current_round": 2, "max_rounds": 2}
    assert should_continue_debate(finished_con_state) == "compile_complete_transcript"

    failed_con_state: DebateGraphState = {"status": "failed", "current_round": 1, "max_rounds": 2}
    assert should_continue_debate(failed_con_state) == "save_result"

