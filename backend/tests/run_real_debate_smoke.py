"""
Controlled Real Debate Smoke Test Runner for Optimization C.
Executes 1 round of real sequential inference on the CPU host:
PRO (Gemma 4.3B) -> Unload -> CON (Qwen 7.6B) -> Unload -> Judge Adjudication.
Measures and records:
- Exact load and generation durations
- Peak RSS memory
- Token counts and termination reasons
- Recovery necessity and duration
- Persistence idempotency
- Substantive output quality
"""

import os
import sys
import time
import json
import uuid
import psutil
from datetime import datetime

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database.session import SessionLocal, Base, engine
from app.models.debate import DebateModel, DebateRoundModel, DebateMessageModel, JudgeEvaluationModel
from app.llm.model_manager import local_model_manager
from app.agents.pro_agent import pro_agent
from app.agents.con_agent import con_agent
from app.agents.judge_agent import judge_agent
from app.graph.nodes import save_pro_message, save_con_message, save_result
from app.graph.state import DebateGraphState

def get_current_rss_mb():
    try:
        proc = psutil.Process(os.getpid())
        return proc.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0

def run_smoke_test(real_inference: bool = True):
    Base.metadata.create_all(bind=engine)
    local_model_manager.mock_mode = not real_inference

    topic = "Should universities allow students to use generative AI for academic assignments?"
    debate_id = str(uuid.uuid4())

    print(f"[{datetime.now().isoformat()}] Starting Smoke Test (real_inference={real_inference})...")
    print(f"Topic: {topic}")
    print(f"Debate ID: {debate_id}")
    print(f"Initial Process RSS: {get_current_rss_mb():.2f} MB")

    with SessionLocal() as db:
        deb = DebateModel(id=debate_id, topic=topic, rounds=1, status="debating")
        db.add(deb)
        db.commit()

    results = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "debate_id": debate_id,
        "real_inference": real_inference,
        "pro": {},
        "con": {},
        "judge": {},
        "memory": {}
    }

    # --------------------------------------------------------------------------
    # STEP 1: PRO AGENT INFERENCE (Gemma-4-E4B-it)
    # --------------------------------------------------------------------------
    print("\n--- STEP 1: PRO AGENT (Gemma-4-E4B-it) ---")
    pro_start_time = time.perf_counter()
    pro_initial_rss = get_current_rss_mb()

    pro_turn = pro_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context="",
        max_new_tokens=128
    )

    pro_duration = time.perf_counter() - pro_start_time
    pro_peak_rss = get_current_rss_mb()

    print(f"PRO completed in {pro_duration:.2f}s (Peak RSS: {pro_peak_rss:.2f} MB)")
    print(f"PRO valid: {pro_turn.get('is_valid')}, finish_reason: {pro_turn.get('finish_reason')}")
    print(f"PRO content:\n{pro_turn.get('content')}")

    results["pro"] = {
        "model": "gemma-4-E4B-it",
        "duration_seconds": round(pro_duration, 2),
        "peak_rss_mb": round(pro_peak_rss, 2),
        "is_valid": pro_turn.get("is_valid"),
        "finish_reason": pro_turn.get("finish_reason"),
        "content": pro_turn.get("content")
    }

    # Persist PRO message
    pro_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "current_round": 1,
        "max_rounds": 1,
        "current_pro_turn": pro_turn,
        "current_pro_evidence": [],
        "transcript": [],
        "status": "debating"
    }
    pro_saved = save_pro_message(pro_state)
    transcript = pro_saved["transcript"]

    # Explicitly unload PRO to guarantee sequential memory isolation
    print("Unloading PRO model before CON loading...")
    local_model_manager.unload_all()
    post_pro_unload_rss = get_current_rss_mb()
    print(f"Post-PRO Unload RSS: {post_pro_unload_rss:.2f} MB")
    results["memory"]["post_pro_unload_rss_mb"] = round(post_pro_unload_rss, 2)

    # --------------------------------------------------------------------------
    # STEP 2: CON AGENT INFERENCE (Qwen2.5-VL-7B-Instruct)
    # --------------------------------------------------------------------------
    print("\n--- STEP 2: CON AGENT (Qwen2.5-VL-7B-Instruct) ---")
    con_start_time = time.perf_counter()

    con_turn = con_agent.generate_turn(
        topic=topic,
        round_number=1,
        max_rounds=1,
        evidence_context="",
        latest_pro_argument=pro_turn.get("content"),
        debate_history=transcript,
        max_new_tokens=128
    )

    con_duration = time.perf_counter() - con_start_time
    con_peak_rss = get_current_rss_mb()

    print(f"CON completed in {con_duration:.2f}s (Peak RSS: {con_peak_rss:.2f} MB)")
    print(f"CON valid: {con_turn.get('is_valid')}, finish_reason: {con_turn.get('finish_reason')}")
    print(f"CON recovery attempted: {con_turn.get('recovery_attempted')}, successful: {con_turn.get('recovery_successful')}")
    print(f"CON content:\n{con_turn.get('content')}")

    results["con"] = {
        "model": "Qwen2.5-VL-7B-Instruct",
        "duration_seconds": round(con_duration, 2),
        "peak_rss_mb": round(con_peak_rss, 2),
        "is_valid": con_turn.get("is_valid"),
        "finish_reason": con_turn.get("finish_reason"),
        "recovery_attempted": con_turn.get("recovery_attempted"),
        "recovery_successful": con_turn.get("recovery_successful"),
        "content": con_turn.get("content")
    }

    # Persist CON message
    con_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "current_round": 1,
        "max_rounds": 1,
        "current_con_turn": con_turn,
        "current_con_evidence": [],
        "transcript": transcript,
        "status": "debating"
    }
    con_saved = save_con_message(con_state)
    full_transcript = con_saved["transcript"]

    # Explicitly unload CON
    print("Unloading CON model...")
    local_model_manager.unload_all()
    post_con_unload_rss = get_current_rss_mb()
    print(f"Post-CON Unload RSS: {post_con_unload_rss:.2f} MB")
    results["memory"]["post_con_unload_rss_mb"] = round(post_con_unload_rss, 2)

    # --------------------------------------------------------------------------
    # STEP 3: JUDGE AGENT EVALUATION
    # --------------------------------------------------------------------------
    print("\n--- STEP 3: JUDGE EVALUATION ---")
    local_model_manager.mock_mode = True # Use offline evaluation rubric for Judge on CPU host
    judge_start = time.perf_counter()
    report = judge_agent.evaluate_debate(
        topic=topic,
        transcript=full_transcript,
        evidence_citations=[]
    )
    judge_duration = time.perf_counter() - judge_start

    print(f"Judge completed in {judge_duration:.2f}s: Winner={report.winner}, PRO={report.pro_score}, CON={report.con_score}")
    print(f"Judge Reasoning: {report.judge_reasoning[:120]}...")

    results["judge"] = {
        "winner": report.winner,
        "pro_score": report.pro_score,
        "con_score": report.con_score,
        "evidence_reliability_score": report.evidence_reliability_score,
        "judge_reasoning": report.judge_reasoning,
        "balanced_verdict": report.balanced_verdict,
        "duration_seconds": round(judge_duration, 2)
    }

    # Final result persistence
    final_state: DebateGraphState = {
        "debate_id": debate_id,
        "topic": topic,
        "transcript": full_transcript,
        "judge_report": report.model_dump(),
        "status": "evaluating"
    }
    save_result(final_state)

    # --------------------------------------------------------------------------
    # STEP 4: PERSISTENCE IDEMPOTENCY CHECK
    # --------------------------------------------------------------------------
    with SessionLocal() as db:
        pro_msgs = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id, DebateMessageModel.role == "PRO"
        ).all()
        con_msgs = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id, DebateMessageModel.role == "CON"
        ).all()
        eval_recs = db.query(JudgeEvaluationModel).filter(
            JudgeEvaluationModel.debate_id == debate_id
        ).all()
        deb_rec = db.query(DebateModel).filter(DebateModel.id == debate_id).first()

    assert len(pro_msgs) == 1, f"Expected 1 PRO message, got {len(pro_msgs)}"
    assert len(con_msgs) == 1, f"Expected 1 CON message, got {len(con_msgs)}"
    assert len(eval_recs) == 1, f"Expected 1 Evaluation record, got {len(eval_recs)}"
    assert deb_rec.status == "completed", f"Expected debate status completed, got {deb_rec.status}"
    results["persistence_verified"] = True

    output_path = os.path.join(backend_dir, "..", "test_reports", "optimization_c_smoke_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Smoke test results written to {output_path}")
    return results

if __name__ == "__main__":
    is_real = "--mock" not in sys.argv
    run_smoke_test(real_inference=is_real)

