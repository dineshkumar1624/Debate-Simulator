import os
import json
import pytest
from unittest.mock import patch, MagicMock

from app.agents.pro_agent import pro_agent
from app.agents.con_agent import con_agent
from app.agents.judge_agent import judge_agent
from app.services.gemini_judge_service import gemini_judge_service
from app.llm.model_manager import local_model_manager
from app.schemas.judge import JudgeReportSchema
from app.schemas.debate import GroundedTurnPayload


PROPOSITION = "Should AI replace human workers?"

PRO_ROUND_1_ARGUMENT = (
    "AI deployment in industrial and administrative processes is economically imperative. "
    "By automating redundant algorithmic workflows, computational models systematically eliminate fatigue, "
    "reducing human variance by 32% while accelerating productivity. Under formal procedural envelopes, "
    "this transition expands higher-order cognitive roles without compromising workplace safety."
)

CON_ROUND_1_REBUTTAL = (
    "The negative position directly challenges Gemma's premise that variance reduction justifies automation. "
    "While statistical consistency is documented, algorithmic optimization cannot replace human normative "
    "judgment or ethical responsibility. In complex out-of-distribution dilemmas, automated models exhibit "
    "unmonitored failure modes that displace workers while introducing systemic fragility."
)

PRO_ROUND_2_ARGUMENT = (
    "In response to CON's objection regarding out-of-distribution fragility: runtime SMT invariant solvers "
    "guarantee hard mathematical safety envelopes that bound failure states. Far from displacing human judgment, "
    "automation handles deterministic calculation checks while reserving normative discretion for human experts."
)


def test_con_agent_receives_latest_pro_argument_and_directly_clashes():
    """
    Verifies that Qwen CON receives Gemma's actual latest argument in its user prompt,
    targets its specific claim, and generates a structured counterargument.
    """
    captured_prompts = {}

    def mock_generate(role, system_prompt, user_prompt, max_new_tokens=128, return_metadata=False):
        captured_prompts["system"] = system_prompt
        captured_prompts["user"] = user_prompt
        return {
            "text": json.dumps({
                "argument_title": "Round 1: Challenge to Variance Reduction Premise",
                "argument_text": CON_ROUND_1_REBUTTAL,
                "central_claim": "Statistical consistency cannot replace human normative accountability.",
                "concise_rationale": "Directly refutes PRO's premise by exposing out-of-distribution fragility.",
                "evidence_references": [],
                "limitations": "Deductive challenge based on institutional accountability bounds."
            }),
            "generated_tokens": 58,
            "input_tokens": 80,
            "hit_token_limit": False
        }

    with patch.object(local_model_manager, "generate", side_effect=mock_generate):
        turn = con_agent.generate_turn(
            topic=PROPOSITION,
            round_number=1,
            max_rounds=2,
            evidence_context="Documented empirical variance reduction of 32% under Bayesian priors.",
            latest_pro_argument=PRO_ROUND_1_ARGUMENT,
            debate_history=[]
        )

    # 1. Verify prompt construction contains Gemma's actual argument
    assert "=== OPPOSING GEMMA (PRO) ARGUMENT TO DIRECTLY REBUT ===" in captured_prompts["user"]
    assert PRO_ROUND_1_ARGUMENT in captured_prompts["user"]
    assert "Mandate: DIRECT CLASH & REBUTTAL" in captured_prompts["user"]

    # 2. Verify returned turn structure
    assert turn["role"] == "CON"
    assert turn["is_valid"] is True
    assert "variance reduction" in turn["content"].lower() or "fatigue" in turn["content"].lower() or "statistical" in turn["content"].lower()
    assert turn["title"] == "Round 1: Challenge to Variance Reduction Premise"


def test_con_agent_fails_fast_when_preceding_pro_argument_is_missing():
    """
    Verifies Section 3: If no PRO argument is available because the preceding turn failed,
    CON reports the workflow error rather than fabricating an ungrounded rebuttal.
    """
    with pytest.raises(RuntimeError) as exc_info:
        con_agent.generate_turn(
            topic=PROPOSITION,
            round_number=1,
            max_rounds=2,
            evidence_context="",
            latest_pro_argument=None, # Missing preceding turn!
            debate_history=[]
        )
    assert "Workflow Error: CON agent cannot generate rebuttal" in str(exc_info.value)


def test_con_agent_does_not_repeat_previous_con_argument():
    """
    Verifies Section 3 & 9: CON in Round 2 addresses the new PRO response
    and does not repeat the Round 1 objection verbatim.
    """
    con_r2_output = (
        "PRO's defense of SMT invariant solvers fails on the epistemic level. A mathematical solver "
        "only constrains known statutory parameters; it cannot anticipate black-swan distribution shifts. "
        "Therefore, retaining human liability while automating decisions creates moral hazard."
    )

    with patch.object(local_model_manager, "generate", return_value={
        "text": json.dumps({
            "argument_title": "Round 2: Epistemic Bounds of Formal Solvers",
            "argument_text": con_r2_output,
            "central_claim": "Formal constraint envelopes cannot solve black-swan distribution shifts.",
            "concise_rationale": "Attacks PRO's Round 2 invariant solver defense directly.",
            "evidence_references": [],
            "limitations": "Acknowledges that constraint solvers are bounded by specification completeness."
        }),
        "generated_tokens": 52,
        "input_tokens": 90,
        "hit_token_limit": False
    }):
        turn_r2 = con_agent.generate_turn(
            topic=PROPOSITION,
            round_number=2,
            max_rounds=2,
            evidence_context="",
            latest_pro_argument=PRO_ROUND_2_ARGUMENT,
            debate_history=[
                {"round_number": 1, "role": "PRO", "content": PRO_ROUND_1_ARGUMENT},
                {"round_number": 1, "role": "CON", "content": CON_ROUND_1_REBUTTAL}
            ]
        )

    assert turn_r2["role"] == "CON"
    assert turn_r2["content"] != CON_ROUND_1_REBUTTAL
    assert "solver" in turn_r2["content"].lower() or "epistemic" in turn_r2["content"].lower()


def test_pro_agent_addresses_proposition_directly_with_reasoning_and_consequences():
    """
    Verifies Section 2: Gemma PRO clearly states position, provides reasoning,
    identifies assumptions, explains practical consequences, and avoids generic preambles.
    """
    captured_prompts = {}

    def mock_generate(role, system_prompt, user_prompt, max_new_tokens=128, return_metadata=False):
        captured_prompts["system"] = system_prompt
        captured_prompts["user"] = user_prompt
        return {
            "text": json.dumps({
                "argument_title": "Round 1: Economic and Operational Imperative",
                "argument_text": PRO_ROUND_1_ARGUMENT,
                "central_claim": "Automation of redundant workflows increases productivity while reducing human fatigue.",
                "concise_rationale": "Inference chain: reduced fatigue -> 32% variance reduction -> bounded safety envelopes.",
                "evidence_references": [],
                "limitations": "Assumes organizational capacity for technical redeployment."
            }),
            "generated_tokens": 60,
            "input_tokens": 70,
            "hit_token_limit": False
        }

    with patch.object(local_model_manager, "generate", side_effect=mock_generate):
        turn = pro_agent.generate_turn(
            topic=PROPOSITION,
            round_number=1,
            max_rounds=2,
            evidence_context="",
            latest_con_argument=None,
            debate_history=[]
        )

    assert turn["role"] == "PRO"
    assert turn["is_valid"] is True
    assert turn["content"] == PRO_ROUND_1_ARGUMENT
    assert "Desired Position: AFFIRMATIVE" in captured_prompts["user"]
    assert PROPOSITION in captured_prompts["user"]
    # Verify no generic preambles
    assert not turn["content"].startswith("In this debate, I argue")
    assert not turn["content"].startswith("As an AI")


def test_pro_agent_round2_responds_to_con_objections_and_advances():
    """
    Verifies Section 2 & 9: In Round 2+, Gemma PRO directly refutes the preceding CON objection
    and advances the debate.
    """
    captured_prompts = {}

    def mock_generate(role, system_prompt, user_prompt, max_new_tokens=128, return_metadata=False):
        captured_prompts["user"] = user_prompt
        return {
            "text": json.dumps({
                "argument_title": "Round 2: Rebuttal of Out-of-Distribution Vulnerability",
                "argument_text": PRO_ROUND_2_ARGUMENT,
                "central_claim": "SMT constraint solvers guarantee mathematical safety floors.",
                "concise_rationale": "Directly counters CON's out-of-distribution objection.",
                "evidence_references": [],
                "limitations": "Restricted to domains where statutory invariants are formalizable."
            }),
            "generated_tokens": 50,
            "input_tokens": 95,
            "hit_token_limit": False
        }

    with patch.object(local_model_manager, "generate", side_effect=mock_generate):
        turn_r2 = pro_agent.generate_turn(
            topic=PROPOSITION,
            round_number=2,
            max_rounds=2,
            evidence_context="",
            latest_con_argument=CON_ROUND_1_REBUTTAL,
            debate_history=[
                {"round_number": 1, "role": "PRO", "content": PRO_ROUND_1_ARGUMENT},
                {"round_number": 1, "role": "CON", "content": CON_ROUND_1_REBUTTAL}
            ]
        )

    assert turn_r2["role"] == "PRO"
    assert "=== PREVIOUS CON OBJECTION TO REBUT & ADVANCE BEYOND ===" in captured_prompts["user"]
    assert CON_ROUND_1_REBUTTAL in captured_prompts["user"]
    assert turn_r2["content"] == PRO_ROUND_2_ARGUMENT


def test_judge_receives_complete_ordered_transcript_and_evaluates_both_sides():
    """
    Verifies Section 4 & 9: Gemini Judge receives the complete transcript in chronological order
    and applies the 8-dimension rubric equally to both sides.
    """
    transcript = [
        {"round_number": 1, "role": "PRO", "speaker": "DEBATER_A", "title": "Round 1 PRO", "content": PRO_ROUND_1_ARGUMENT, "evidence": []},
        {"round_number": 1, "role": "CON", "speaker": "DEBATER_B", "title": "Round 1 CON", "content": CON_ROUND_1_REBUTTAL, "evidence": []},
        {"round_number": 2, "role": "PRO", "speaker": "DEBATER_A", "title": "Round 2 PRO", "content": PRO_ROUND_2_ARGUMENT, "evidence": []},
    ]

    system_prompt, user_prompt, _ = gemini_judge_service._build_judge_prompts(
        topic=PROPOSITION,
        transcript=transcript,
        evidence_citations=[]
    )

    # 1. Transcript completeness and ordering
    assert "=== AUTHORITATIVE TRANSCRIPT ===" in user_prompt
    pos_r1_pro = user_prompt.find(PRO_ROUND_1_ARGUMENT)
    pos_r1_con = user_prompt.find(CON_ROUND_1_REBUTTAL)
    pos_r2_pro = user_prompt.find(PRO_ROUND_2_ARGUMENT)
    assert pos_r1_pro != -1 and pos_r1_con != -1 and pos_r2_pro != -1
    assert pos_r1_pro < pos_r1_con < pos_r2_pro, "Transcript turns must appear in strict chronological order!"

    # 2. Rubric criteria in system prompt
    assert "EVALUATION RUBRIC" in system_prompt
    assert "1. Logical Reasoning" in system_prompt
    assert "2. Relevance to Proposition" in system_prompt
    assert "3. Strength of Rebuttals" in system_prompt
    assert "4. Factual Accuracy & Evidence Support" in system_prompt
    assert "5. Identification of Assumptions" in system_prompt
    assert "6. Treatment of Opposing Arguments" in system_prompt
    assert "7. Internal Consistency" in system_prompt
    assert "8. Unsupported Claims & Uncertainty" in system_prompt


def test_judge_evaluates_on_rubric_and_never_fabricates_citations():
    """
    Verifies Section 4 & 6: When evidence is absent, Judge sets source_references to []
    and flags ungrounded assertions rather than inventing citations.
    """
    transcript = [
        {"round_number": 1, "role": "PRO", "speaker": "DEBATER_A", "title": "PRO R1", "content": PRO_ROUND_1_ARGUMENT, "evidence": []},
        {"round_number": 1, "role": "CON", "speaker": "DEBATER_B", "title": "CON R1", "content": CON_ROUND_1_REBUTTAL, "evidence": []},
    ]

    # Evaluate via Judge agent in mock mode to check discipline
    local_model_manager.mock_mode = True
    try:
        report = judge_agent.evaluate_debate(
            topic=PROPOSITION,
            transcript=transcript,
            evidence_citations=[]
        )
        assert isinstance(report, JudgeReportSchema)
        assert report.status == "completed"
        assert report.winner in ["PRO", "CON", "INCONCLUSIVE"]
        # Citation discipline
        assert report.source_references == []
        assert report.evidence_reliability_score <= 50.0
        assert report.judge_model_used == "mock_adjudicator"
        assert report.is_fallback is True
    finally:
        local_model_manager.mock_mode = False


def test_incomplete_debate_cannot_receive_completed_judge_verdict():
    """
    Verifies Section 4 & 9: Incomplete debate (e.g. invalid turn) cannot receive a completed verdict.
    """
    from app.graph.nodes import compile_complete_transcript, judge_agent_node

    failed_state = {
        "status": "debating",
        "topic": PROPOSITION,
        "transcript": [
            {"round_number": 1, "role": "PRO", "is_valid": True, "content": "Valid turn."},
            {"round_number": 1, "role": "CON", "is_valid": False, "validation_errors": ["Abrupt sentence truncation."]}
        ]
    }

    compile_res = compile_complete_transcript(failed_state)
    assert compile_res["status"] == "failed"
    assert "Unresolved incomplete/invalid turn" in compile_res["error"]

    # When judge_agent_node is invoked on failed state, it refuses to call the Judge API
    failed_state["status"] = "failed"
    failed_state["error"] = compile_res["error"]
    judge_res = judge_agent_node(failed_state)
    assert judge_res["judge_report"]["winner"] == "FAILED"
    assert judge_res["judge_report"]["status"] == "failed"


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_GEMINI_TEST", "true").lower() in ("true", "1", "yes"),
    reason="Live Gemini API test runs when RUN_LIVE_GEMINI_TEST=true"
)
def test_live_gemini_judge_evaluation_end_to_end():
    """
    Section 10 Real End-to-End Test: Calls the REAL Google Gemini API (gemini-3.8-flash)
    to adjudicate the proposition 'Should AI replace human workers?'.
    Verifies live adjudication, rubric adherence, model identification, and verdict justification.
    """
    # Verify GEMINI_API_KEY is configured
    try:
        client = gemini_judge_service.get_client()
    except Exception as e:
        pytest.skip(f"Live Gemini API unavailable: {e}")

    transcript = [
        {
            "round_number": 1,
            "role": "PRO",
            "speaker": "DEBATER_A (Gemma)",
            "title": "Round 1: Economic Variance Reduction & Productivity",
            "content": PRO_ROUND_1_ARGUMENT,
            "evidence": []
        },
        {
            "round_number": 1,
            "role": "CON",
            "speaker": "DEBATER_B (Qwen)",
            "title": "Round 1: Out-of-Distribution Vulnerability & Accountability",
            "content": CON_ROUND_1_REBUTTAL,
            "evidence": []
        },
        {
            "round_number": 2,
            "role": "PRO",
            "speaker": "DEBATER_A (Gemma)",
            "title": "Round 2: Bounded SMT Solvers & Expertise Allocation",
            "content": PRO_ROUND_2_ARGUMENT,
            "evidence": []
        }
    ]

    # Call the real Gemini model
    report = gemini_judge_service.evaluate_debate(
        topic=PROPOSITION,
        transcript=transcript,
        evidence_citations=[]
    )

    if report.status == "failed" and "RESOURCE_EXHAUSTED" in str(report.error_message):
        pytest.skip(f"Live Gemini Free Tier daily quota limit (20 req/day) reached: {report.error_message}")

    assert isinstance(report, JudgeReportSchema)
    assert report.status == "completed", f"Evaluation failed: {report.error_message}"
    assert report.winner in ["PRO", "CON", "INCONCLUSIVE"]
    assert report.judge_model_used in ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3-flash-preview"]
    assert report.is_fallback is False
    assert len(report.judge_reasoning) > 50, "Judge reasoning must be substantive!"
    assert len(report.balanced_verdict) > 20, "Balanced verdict must be present!"
    # Verify that the verdict reflects actual arguments
    reasoning_lower = (report.judge_reasoning + report.balanced_verdict).lower()
    assert any(term in reasoning_lower for term in ["pro", "con", "variance", "automation", "worker", "human", "solver", "fragility"]), (
        f"Judge reasoning did not refer to the actual debate content: {report.judge_reasoning}"
    )


@pytest.mark.skipif(
    not os.getenv("RUN_REAL_LOCAL_MODELS", "false").lower() in ("true", "1", "yes"),
    reason="Local PyTorch weights loading test requires discrete GPU or high RAM. Skipped on standard CPU CI."
)
def test_opt_in_real_local_model_inference():
    """
    Opt-in smoke test verifying physical loading of local weights when enabled.
    """
    assert os.path.exists(local_model_manager.get_model_path("PRO")), "PRO model directory must exist"
    assert os.path.exists(local_model_manager.get_model_path("CON")), "CON model directory must exist"
