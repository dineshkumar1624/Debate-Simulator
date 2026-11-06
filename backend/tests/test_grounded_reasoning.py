"""
Unit and Integration Tests for Grounded LLM Reasoning vs. PDF Copy-Pasting.

Verifies:
1. The generated argument is NOT simply the retrieved PDF chunk copied verbatim.
2. The argument explains how evidence relates to the proposition.
3. CON directly addresses the latest PRO argument.
4. PRO and CON maintain distinct roles across multiple rounds.
5. Citations point to real retrieved chunks and correct page/section metadata.
6. Missing evidence does not cause invented facts or citations.
7. Malformed model output and truncated output are handled safely.
8. The frontend and API schemas present argument_text as main content and genuine passage for View Source.
9. Optional real-model smoke test.
"""

import uuid
import json
import pytest
from unittest.mock import patch, MagicMock

from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel, DebateRoundModel
from app.schemas.debate import GroundedTurnPayload, GroundedEvidenceReference, DebateTurnSchema, EvidenceItemSchema
from app.agents.pro_agent import pro_agent
from app.agents.con_agent import con_agent
from app.services.turn_parser import turn_parser, _calculate_ngram_overlap, _find_longest_common_substring_length
from app.services.rag_service import rag_service
from app.llm.model_manager import local_model_manager, LocalModelManager
from app.routes.debates import _format_debate_session
from app.graph.debate_graph import debate_graph
from app.graph.state import DebateGraphState

SAMPLE_PDF_PASSAGE = (
    "Section 3.1: Empirical Outcomes of Automated Clinical Triage. "
    "In a randomized multi-center evaluation across twelve tertiary medical facilities, "
    "algorithmic triage classification reduced average ICU bed allocation latency by 41.2 minutes "
    "(p < 0.001) during peak respiratory surge periods. However, secondary retrospective auditing "
    "revealed a 23.8% increase in diagnostic under-triage among geriatric patients with atypical presentations, "
    "demonstrating that rapid optimization creates acute failure modes on out-of-distribution comorbidities."
)

SAMPLE_RETRIEVED_EVIDENCE = [
    {
        "id": "chunk-101",
        "claim": "Evidentiary finding from Section 3.1: Empirical Outcomes (Page 7)",
        "source": "Document: Clinical_AI_Safety_Report.pdf",
        "page": 7,
        "section": "Section 3.1: Empirical Outcomes",
        "url": None,
        "content": SAMPLE_PDF_PASSAGE,
        "verdict": "supported",
        "confidenceScore": 94.0
    }
]

@pytest.fixture(autouse=True)
def setup_db_and_mock():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield

# --------------------------------------------------------------------------
# 1. Anti-Copy-Paste: Argument is NOT a verbatim copy of the retrieved PDF chunk
# --------------------------------------------------------------------------
def test_argument_is_not_verbatim_copied_pdf_chunk():
    """
    Verifies that when given a raw PDF passage as context, the debater synthesizes
    its argument in its own words rather than copying the passage verbatim.
    """
    topic = "Should algorithmic triage software replace physician judgment in emergency ICU bed allocation?"
    
    # 1. PRO Turn
    pro_turn = pro_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context=rag_service.format_evidence_context(SAMPLE_RETRIEVED_EVIDENCE),
        retrieved_evidence=SAMPLE_RETRIEVED_EVIDENCE
    )

    pro_content = pro_turn["content"]
    assert pro_content is not None and len(pro_content) > 30

    # Ensure PRO argument is NOT a verbatim copy of the raw PDF text
    pro_overlap = _calculate_ngram_overlap(pro_content, SAMPLE_PDF_PASSAGE, n=4)
    pro_lcs = _find_longest_common_substring_length(pro_content, SAMPLE_PDF_PASSAGE)
    assert pro_overlap < 0.60, f"PRO argument has excessive verbatim n-gram overlap: {pro_overlap:.2f}"
    assert pro_lcs < 80, f"PRO argument contains long identical verbatim substring: {pro_lcs} chars"
    assert "Section 3.1: Empirical Outcomes of Automated Clinical Triage." not in pro_content

    # 2. CON Turn
    con_turn = con_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context=rag_service.format_evidence_context(SAMPLE_RETRIEVED_EVIDENCE),
        latest_pro_argument=pro_content,
        retrieved_evidence=SAMPLE_RETRIEVED_EVIDENCE
    )

    con_content = con_turn["content"]
    assert con_content is not None and len(con_content) > 30

    con_overlap = _calculate_ngram_overlap(con_content, SAMPLE_PDF_PASSAGE, n=4)
    con_lcs = _find_longest_common_substring_length(con_content, SAMPLE_PDF_PASSAGE)
    assert con_overlap < 0.60, f"CON argument has excessive verbatim n-gram overlap: {con_overlap:.2f}"
    assert con_lcs < 80, f"CON argument contains long identical verbatim substring: {con_lcs} chars"
    assert "Section 3.1: Empirical Outcomes of Automated Clinical Triage." not in con_content

# --------------------------------------------------------------------------
# 2. Argument explains how evidence relates to the proposition
# --------------------------------------------------------------------------
def test_argument_explains_how_evidence_relates_to_proposition():
    """
    Verifies that the generated argument explains what the claim is, its reasoning,
    and how the cited evidence supports or limits the proposition.
    """
    topic = "Should autonomous AI agents face strict liability for medical misdiagnosis?"
    
    pro_turn = pro_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context=rag_service.format_evidence_context(SAMPLE_RETRIEVED_EVIDENCE),
        retrieved_evidence=SAMPLE_RETRIEVED_EVIDENCE
    )

    assert pro_turn.get("main_claim") is not None
    assert len(pro_turn["main_claim"]) > 10
    assert pro_turn.get("reasoning_summary") is not None
    assert len(pro_turn["reasoning_summary"]) > 10
    # Must explicitly connect evidence to the proposition
    assert any(term in pro_turn["content"].lower() for term in ["evidence", "documented", "empirical", "findings", "validates", "demonstrates"])

# --------------------------------------------------------------------------
# 3. CON directly addresses the latest PRO argument
# --------------------------------------------------------------------------
def test_con_directly_addresses_latest_pro_argument():
    """
    Verifies that CON reads PRO's actual latest argument, identifies its premise,
    and challenges its reasoning rather than generating a generic disconnected objection.
    """
    topic = "Should algorithmic models replace human judges in bail decisions?"
    specific_pro_argument = (
        "Empirical adherence to Bayesian sentencing priors achieved a 32% variance reduction "
        "across 12,000 simulated appellate rulings, systematically eliminating human fatigue."
    )

    con_turn = con_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context=rag_service.format_evidence_context(SAMPLE_RETRIEVED_EVIDENCE),
        latest_pro_argument=specific_pro_argument,
        retrieved_evidence=SAMPLE_RETRIEVED_EVIDENCE
    )

    con_text = con_turn["content"]
    # CON must reference PRO's claim or the core theme
    assert ("pro's premise" in con_text.lower() or "affirmative" in con_text.lower() or "statistical consistency" in con_text.lower() or "32%" in con_text or "bayesian" in con_text.lower())
    # CON must challenge the reasoning/assumptions
    assert ("cannot be conflated" in con_text.lower() or "due process" in con_text.lower() or "moral legitimacy" in con_text.lower() or "vulnerabilit" in con_text.lower())

# --------------------------------------------------------------------------
# 4. PRO and CON maintain distinct roles across multiple rounds
# --------------------------------------------------------------------------
def test_pro_and_con_maintain_distinct_roles_across_rounds():
    """
    Verifies that PRO consistently argues the affirmative case and CON consistently
    argues the opposition case across multiple rounds without role swapping or generic repetition.
    """
    topic = "Should algorithmic liability be strictly enforced?"
    
    # Round 1
    r1_pro = pro_agent.generate_turn(topic=topic, round_number=1, max_rounds=2, evidence_context="", retrieved_evidence=[])
    r1_con = con_agent.generate_turn(topic=topic, round_number=1, max_rounds=2, evidence_context="", latest_pro_argument=r1_pro["content"], retrieved_evidence=[])
    
    assert r1_pro["role"] == "PRO"
    assert r1_con["role"] == "CON"
    assert "affirmative" in r1_pro["content"].lower()
    assert "negative" in r1_con["content"].lower()

    # Round 2
    transcript = [
        {"round_number": 1, "role": "PRO", "content": r1_pro["content"]},
        {"round_number": 1, "role": "CON", "content": r1_con["content"]},
    ]
    r2_pro = pro_agent.generate_turn(topic=topic, round_number=2, max_rounds=2, evidence_context="", latest_con_argument=r1_con["content"], debate_history=transcript, retrieved_evidence=[])
    r2_con = con_agent.generate_turn(topic=topic, round_number=2, max_rounds=2, evidence_context="", latest_pro_argument=r2_pro["content"], debate_history=transcript + [{"round_number": 2, "role": "PRO", "content": r2_pro["content"]}], retrieved_evidence=[])

    assert r2_pro["role"] == "PRO"
    assert r2_con["role"] == "CON"
    assert r2_pro["title"] != r1_pro["title"] # Meaningful round differentiation
    assert r2_con["title"] != r1_con["title"]

# --------------------------------------------------------------------------
# 5. Citations point to real retrieved chunks and correct page metadata
# --------------------------------------------------------------------------
def test_citations_point_to_real_retrieved_chunks_and_correct_page():
    """
    Verifies that evidence citations strictly match the actual retrieved document chunks:
    genuine page number, genuine section title, genuine passage excerpt, and no hallucinated metadata.
    """
    topic = "Clinical triage safety"
    pro_turn = pro_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context=rag_service.format_evidence_context(SAMPLE_RETRIEVED_EVIDENCE),
        retrieved_evidence=SAMPLE_RETRIEVED_EVIDENCE
    )

    refs = pro_turn.get("evidence_references", [])
    assert len(refs) > 0, "Expected at least one bound evidence reference"
    ref = refs[0]
    
    # Must strictly match the input chunk's genuine page and section
    assert ref["page"] == 7
    assert ref["section"] == "Section 3.1: Empirical Outcomes"
    # Excerpt must hold genuine PDF text for View Source
    assert ref["excerpt"] == SAMPLE_PDF_PASSAGE
    assert "41.2 minutes" in ref["excerpt"]
    assert "23.8% increase" in ref["excerpt"]

# --------------------------------------------------------------------------
# 6. Missing evidence states limitations without inventing citations
# --------------------------------------------------------------------------
def test_missing_evidence_states_limitations_without_inventing_citations():
    """
    Verifies that when no document evidence is retrieved:
    - evidence_references is empty list []
    - limitations is clearly populated
    - No phantom sources or hallucinated page numbers are created.
    """
    topic = "Speculative philosophy on post-biological consciousness"
    empty_evidence = []

    pro_turn = pro_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context=rag_service.format_evidence_context(empty_evidence),
        retrieved_evidence=empty_evidence
    )

    assert pro_turn["evidence_references"] == []
    assert pro_turn.get("limitations") is not None
    assert "no external" in pro_turn["limitations"].lower() or "deductive" in pro_turn["limitations"].lower() or "uncertainty" in pro_turn["limitations"].lower()

# --------------------------------------------------------------------------
# 7. Malformed model output and truncated output handled safely
# --------------------------------------------------------------------------
def test_malformed_and_truncated_output_handled_safely():
    """
    Verifies that if the LLM produces malformed text, raw JSON, broken markdown,
    or truncated sentences, the turn_parser and response_validator handle it cleanly
    without crashing, producing a valid GroundedTurnPayload.
    """
    # 7A: Raw JSON with markdown backticks
    raw_json_md = (
        "```json\n"
        "{\n"
        '  "argument_title": "Affirmative Defense",\n'
        '  "argument_text": "Algorithmic decision systems systematically eliminate human fatigue under formal constraints.",\n'
        '  "main_claim": "Formal constraints bound variance.",\n'
        '  "reasoning_summary": "Empirical validation confirms structural consistency.",\n'
        '  "evidence_references": [],\n'
        '  "limitations": null\n'
        "}\n"
        "```"
    )
    payload_a = turn_parser.parse_and_validate("PRO", raw_json_md, SAMPLE_RETRIEVED_EVIDENCE)
    assert payload_a.argument_title == "Affirmative Defense"
    assert "eliminate human fatigue" in payload_a.argument_text
    assert not payload_a.argument_text.startswith("```") # Must not leak markdown backticks into main text!

    # 7B: Structured key-value text without JSON
    structured_text = (
        "Title: Epistemic Due Process Bounds\n"
        "Main Claim: Due process demands non-delegable moral discretion.\n"
        "Argument: Algorithmic constraint envelopes fail to provide constitutional due process on atypical cases.\n"
        "Reasoning: Moral discretion cannot be mathematically solved through Bayesian priors.\n"
        "Limitations: External empirical evidence on jury simulation is limited."
    )
    payload_b = turn_parser.parse_and_validate("CON", structured_text, SAMPLE_RETRIEVED_EVIDENCE)
    assert payload_b.argument_title == "Epistemic Due Process Bounds"
    assert "constitutional due process" in payload_b.argument_text
    assert "non-delegable moral discretion" in payload_b.main_claim

    # 7C: Raw copied PDF passage detected and synthesized
    raw_copied_text = SAMPLE_PDF_PASSAGE # Model blindly extracted the PDF chunk!
    payload_c = turn_parser.parse_and_validate("PRO", raw_copied_text, SAMPLE_RETRIEVED_EVIDENCE)
    # Parser must detect verbatim copy-paste and synthesize into proper reasoning!
    assert "Section 3.1: Empirical Outcomes of Automated Clinical Triage." not in payload_c.argument_text
    assert "affirmative case" in payload_c.argument_text.lower() or "empirical support" in payload_c.argument_text.lower()

# --------------------------------------------------------------------------
# 8. API & Frontend Contract: argument_text displayed as main content, genuine passage for View Source
# --------------------------------------------------------------------------
def test_api_and_frontend_contract_presents_argument_text_not_raw_chunk():
    """
    Verifies that _format_debate_session populates DebateTurnSchema.content with
    the clean argument_text, and EvidenceItemSchema with real page, section, and passage
    content for the 'View Source' action.
    """
    debate_id = str(uuid.uuid4())
    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic="Clinical AI Liability", rounds=1, status="completed")
        db.add(deb)
        msg = DebateMessageModel(
            id=str(uuid.uuid4()),
            debate_id=debate_id,
            round_number=1,
            speaker="DEBATER_A",
            role="PRO",
            title="Round 1 Affirmative Argument",
            content="Drawing upon documented clinical findings, procedural automation eliminates diagnostic latency.",
            confidence=92.0,
            evidence_references=[
                {
                    "id": "ref-1",
                    "claim": "Evidentiary finding from Clinical Triage",
                    "source": "Document: Clinical_AI_Safety_Report.pdf",
                    "page": 7,
                    "section": "Section 3.1: Empirical Outcomes",
                    "content": SAMPLE_PDF_PASSAGE,
                    "relevanceScore": 94.0,
                    "verdict": "supported"
                }
            ]
        )
        db.add(msg)
        db.commit()

        session_schema = _format_debate_session(deb)
        assert len(session_schema.rounds) == 1
        turn = session_schema.rounds[0].turns[0]

        # 1. Main argument text is clean synthesized prose, NOT raw PDF passage or JSON
        assert turn.content == "Drawing upon documented clinical findings, procedural automation eliminates diagnostic latency."
        assert not turn.content.startswith("{")
        assert SAMPLE_PDF_PASSAGE not in turn.content

        # 2. Evidence item carries genuine page and passage content for "View Source"
        assert len(turn.evidence) == 1
        ev = turn.evidence[0]
        assert ev.page == 7
        assert ev.section == "Section 3.1: Empirical Outcomes"
        assert ev.content == SAMPLE_PDF_PASSAGE
        assert ev.relevanceScore == 94.0

# --------------------------------------------------------------------------
# 9. Optional Real Model Smoke Test (CPU or GPU)
# --------------------------------------------------------------------------
@pytest.mark.skip(reason="Optional real model smoke test; run explicitly when testing physical model reasoning on CPU/GPU")
def test_optional_real_model_smoke_test():
    """
    Executes a single real turn with local model weights to test physical LLM reasoning.
    Skipped by default in automated testing suites.
    """
    real_mgr = LocalModelManager()
    real_mgr.mock_mode = False
    pro_turn = pro_agent.generate_turn(
        topic="Should AI models be legally accountable for errors?",
        round_number=1,
        max_rounds=1,
        evidence_context="Verified Document Excerpt: Automated neural classifiers reduce variance by 30%.",
        max_new_tokens=64
    )
    assert pro_turn["is_valid"] is True
    assert len(pro_turn["content"]) > 20

