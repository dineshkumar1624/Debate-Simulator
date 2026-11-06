"""
Optimization B Benchmark & Validation Suite.

Validates:
1. Baseline (128 tokens) vs 64-token generation ceiling behavior.
2. Token truncation detection, finish_reason classification, and completion validation.
3. Bounded recovery behavior (recovery continuation vs failed recovery honesty).
4. Persistence idempotency during turn updates.
5. Sentence-boundary stopping hazards (demonstrates premature termination on abbreviations, decimals, numbers).
6. Clear separation between normal EOS termination, sentence-boundary stopping, and max-token termination.
"""

import uuid
import pytest
import torch
from unittest.mock import MagicMock
from transformers import StoppingCriteria, StoppingCriteriaList

from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateMessageModel
from app.agents.con_agent import con_agent
from app.services.response_validator import response_validator, ResponseValidator
from app.graph.nodes import save_con_message, check_adjudication_routing
from app.llm.model_manager import local_model_manager

@pytest.fixture(autouse=True)
def setup_db():
    local_model_manager.mock_mode = True
    Base.metadata.create_all(bind=engine)
    yield


# ==============================================================================
# 1. Baseline (128 Tokens) vs 64-Token Ceiling Comparison
# ==============================================================================

def test_baseline_128_tokens_produces_complete_counterargument():
    topic = "Should universities allow students to use generative AI for academic assignments?"
    pro_arg = (
        "The affirmative asserts that generative AI provides essential cognitive scaffolding, "
        "accelerates creative iteration, and builds 21st-century workforce readiness."
    )
    turn_128 = con_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context="",
        latest_pro_argument=pro_arg,
        max_new_tokens=128
    )

    assert turn_128["is_valid"] is True
    assert turn_128["finish_reason"] == "stop"
    assert turn_128["is_truncated"] is False
    assert len(turn_128["validation_errors"]) == 0
    assert len(turn_128["content"]) > 100


def test_64_token_ceiling_truncation_detection():
    # Realistic 64-token cutoff from benchmark
    raw_64_output = (
        "**Target:** The affirmative claims that AI provides essential cognitive scaffolding, "
        "accelerates creative iteration, and builds essential 21st-century workforce readiness.\n\n"
        "**Counterarguments:**\n\n"
        "1. **Impact on Cognitive Development:** While AI can provide scaffolding, it may not necessarily "
        "enhance deep cognitive processes. A study published in *"
    )
    val = response_validator.validate(
        text=raw_64_output,
        role="CON",
        max_tokens_configured=64,
        actual_tokens_generated=64
    )

    assert val.is_valid is False
    assert val.is_truncated is True
    assert val.finish_reason == "length"
    assert any("terminal punctuation" in e or "dangling" in e for e in val.errors)


# ==============================================================================
# 2. Bounded Recovery Behavior
# ==============================================================================

def test_64_token_bounded_recovery_completion():
    raw_64_output = (
        "**Target:** The affirmative claims that AI provides essential cognitive scaffolding, "
        "accelerates creative iteration, and builds essential 21st-century workforce readiness.\n\n"
        "**Counterarguments:**\n\n"
        "1. **Impact on Cognitive Development:** While AI can provide scaffolding, it may not necessarily "
        "enhance deep cognitive processes. A study published in *"
    )
    val = response_validator.validate(
        text=raw_64_output,
        role="CON",
        max_tokens_configured=64,
        actual_tokens_generated=64
    )

    mock_mgr = MagicMock()
    mock_mgr.generate.return_value = "Nature shows passive tool use impairs memory consolidation."

    recovered_text, rec_val = response_validator.attempt_recovery(
        role="CON",
        text=raw_64_output,
        system_prompt="sys",
        user_prompt="usr",
        validation=val,
        model_manager=mock_mgr
    )

    assert rec_val.recovery_attempted is True
    assert rec_val.recovery_successful is True
    assert rec_val.is_valid is True
    assert "Nature shows passive tool use impairs memory consolidation." in recovered_text


def test_64_token_failed_recovery_marks_turn_honestly():
    raw_64_output = "The affirmative position overlooks that automated tool reliance weakens"
    val = response_validator.validate(
        text=raw_64_output,
        role="CON",
        max_tokens_configured=64,
        actual_tokens_generated=64
    )

    mock_mgr = MagicMock()
    # Continuation also fails / produces truncated text
    mock_mgr.generate.return_value = " and fails to"

    _, rec_val = response_validator.attempt_recovery(
        role="CON",
        text=raw_64_output,
        system_prompt="sys",
        user_prompt="usr",
        validation=val,
        model_manager=mock_mgr
    )

    assert rec_val.recovery_attempted is True
    assert rec_val.recovery_successful is False
    assert rec_val.is_valid is False


# ==============================================================================
# 3. Persistence Idempotency and Workflow Safety
# ==============================================================================

def test_recovery_persistence_idempotency_prevents_duplicate_messages():
    debate_id = str(uuid.uuid4())
    with SessionLocal() as db:
        db.add(DebateModel(id=debate_id, topic="AI in Higher Ed", rounds=1, status="debating"))
        db.commit()

    turn = {
        "speaker": "DEBATER_B",
        "role": "CON",
        "round_number": 1,
        "title": "Initial Opposition Argument",
        "content": "Initial unrecovered opposition argument.",
        "confidence": 91.0,
        "is_valid": True,
        "is_truncated": False,
        "finish_reason": "stop",
        "validation_errors": []
    }

    state = {
        "debate_id": debate_id,
        "topic": "AI in Higher Ed",
        "current_round": 1,
        "max_rounds": 1,
        "current_con_turn": turn,
        "current_con_evidence": [],
        "transcript": [],
        "status": "debating"
    }

    # Save initial turn
    res1 = save_con_message(state)
    assert len(res1["transcript"]) == 1

    # Simulate recovery update to same turn
    state["transcript"] = res1["transcript"]
    state["current_con_turn"]["content"] = "Recovered complete substantive counterargument."
    res2 = save_con_message(state)

    # Transcript and DB must remain exactly 1 record
    assert len(res2["transcript"]) == 1
    assert "Recovered complete" in res2["transcript"][0]["content"]

    with SessionLocal() as db:
        records = db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == debate_id).all()
        assert len(records) == 1
        assert "Recovered complete" in records[0].content


def test_failed_turn_diverts_workflow_and_bypasses_judge():
    failed_state = {
        "debate_id": str(uuid.uuid4()),
        "topic": "AI in Higher Ed",
        "current_round": 1,
        "max_rounds": 1,
        "transcript": [
            {"speaker": "DEBATER_A", "role": "PRO", "round_number": 1, "content": "Valid PRO", "is_valid": True},
            {"speaker": "DEBATER_B", "role": "CON", "round_number": 1, "content": "Truncated CON", "is_valid": False, "validation_errors": ["Truncated"]}
        ],
        "status": "failed",
        "error": "CON failed completion validation"
    }

    # Adjudication routing must strictly bypass judge and go directly to save_result
    target = check_adjudication_routing(failed_state)
    assert target == "save_result"


# ==============================================================================
# 4. Sentence-Boundary Stopping Hazards Demonstration
# ==============================================================================

class NaivePunctuationStoppingCriteria(StoppingCriteria):
    def __init__(self, punct_token_ids):
        self.punct_token_ids = set(punct_token_ids)

    def __call__(self, input_ids: torch.LongTensor, scores: tuple[torch.FloatTensor] | None, **kwargs) -> bool:
        last_token = input_ids[0, -1].item()
        return last_token in self.punct_token_ids


def test_naive_punctuation_stopping_causes_premature_termination():
    """
    Demonstrates empirically why naive sentence-boundary stopping on punctuation
    prematurely truncates valid arguments at abbreviations, decimal numbers, and list points.
    """
    qwen_tok = local_model_manager.load_tokenizer("CON")
    period_id = qwen_tok.encode(".", add_special_tokens=False)[0]
    stop_criteria = NaivePunctuationStoppingCriteria([period_id])

    test_samples = [
        # Abbreviation: Dr. Smith
        "Dr. Smith demonstrated that AI scaffolding reduces cognitive retention.",
        # Decimal number: 3.5%
        "A 3.5% decline in retention benchmarks was documented in randomized trials.",
        # Numbered list: Point 1.
        "Point 1. First, passive reliance disrupts foundational neural pathways."
    ]

    for sample in test_samples:
        tokens = qwen_tok.encode(sample, add_special_tokens=False)
        premature_trigger_idx = None
        for idx, tid in enumerate(tokens):
            tensor_in = torch.tensor([[tid]])
            if stop_criteria(tensor_in, None):
                premature_trigger_idx = idx + 1
                break

        # A naive stopping criteria triggers at the FIRST period (e.g. after 'Dr' or '3' or '1')
        assert premature_trigger_idx is not None
        assert premature_trigger_idx < len(tokens), (
            f"Expected premature stop before full sentence length {len(tokens)}, "
            f"but triggered at {premature_trigger_idx}"
        )
        truncated_text = qwen_tok.decode(tokens[:premature_trigger_idx])
        assert not truncated_text.endswith("retention.") and not truncated_text.endswith("pathways.")

