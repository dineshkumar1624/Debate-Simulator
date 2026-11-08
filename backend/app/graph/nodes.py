import logging
import uuid
import time
from typing import Dict, Any, List
from datetime import datetime, timezone
from ..database.session import SessionLocal
from ..models.debate import DebateModel, DebateRoundModel, DebateMessageModel, JudgeEvaluationModel
from ..models.document import DocumentModel
from ..services.rag_service import rag_service
from ..services.context_manager import context_manager
from ..agents.pro_agent import pro_agent
from ..agents.con_agent import con_agent
from ..agents.judge_agent import judge_agent
from ..schemas.judge import JudgeReportSchema
from ..core.config import settings
from ..services.debate_stream_service import debate_stream_service
from ..llm.model_manager import local_model_manager, DebateCancelledException
from ..services.cancellation_service import is_debate_cancelled
from .state import DebateGraphState

logger = logging.getLogger(__name__)

# Node 1: initialize_debate
def initialize_debate(state: DebateGraphState) -> Dict[str, Any]:
    logger.info(f"[Graph] initialize_debate for debate_id={state.get('debate_id')}")
    debate_id = state.get("debate_id")
    topic = state.get("topic", "")
    scope = state.get("source_scope", "document")
    doc_ids = state.get("document_ids") or []
    doc_id = doc_ids[0] if doc_ids else None

    doc_name = None
    page_count = None
    core_evidence = []

    with SessionLocal() as db:
        debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        if debate:
            debate.status = "debating"
            debate.error_message = None
            db.commit()

        if doc_id:
            doc_rec = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
            if doc_rec:
                doc_name = doc_rec.name
                page_count = doc_rec.page_count

        perm_context = context_manager.build_permanent_context(
            topic=topic,
            source_scope=scope,
            document_id=doc_id,
            document_name=doc_name,
            page_count=page_count,
            core_evidence=None
        )

        # Check existing messages in DB for restart / resume
        existing_msgs = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id
        ).order_by(DebateMessageModel.round_number, DebateMessageModel.created_at).all()

        if existing_msgs:
            logger.info(f"[Graph] Resuming debate {debate_id} with {len(existing_msgs)} existing messages from database.")
            resumed_transcript = []
            rounds_map: Dict[int, Dict[str, Any]] = {}

            for msg in existing_msgs:
                r = msg.round_number
                if r not in rounds_map:
                    rounds_map[r] = {}
                rounds_map[r][msg.role] = msg

                resumed_transcript.append({
                    "speaker": msg.speaker,
                    "role": msg.role,
                    "round_number": msg.round_number,
                    "title": msg.title,
                    "content": msg.content,
                    "evidence": msg.evidence_references or [],
                    "timestamp": msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat()
                })

            max_r = max(rounds_map.keys())
            has_pro = "PRO" in rounds_map[max_r]
            has_con = "CON" in rounds_map[max_r]
            max_rounds = state.get("max_rounds") or (debate.rounds if (debate and debate.rounds) else 3)

            if has_pro and not has_con:
                # PRO was committed, but CON was interrupted!
                resume_round = max_r
                resume_target = "retrieve_con_evidence"
                latest_pro = rounds_map[max_r]["PRO"].content
                latest_con = rounds_map[max_r - 1]["CON"].content if (max_r > 1 and "CON" in rounds_map[max_r - 1]) else None
                logger.info(f"[Graph Resume] Round {max_r} PRO is committed; resuming directly to CON rebuttal.")
            elif has_pro and has_con:
                latest_con = rounds_map[max_r]["CON"].content
                latest_pro = rounds_map[max_r]["PRO"].content
                if max_r < max_rounds:
                    resume_round = max_r + 1
                    resume_target = "retrieve_pro_evidence"
                    logger.info(f"[Graph Resume] Round {max_r} fully completed; resuming to Round {resume_round} PRO.")
                else:
                    resume_round = max_rounds
                    resume_target = "compile_complete_transcript"
                    logger.info(f"[Graph Resume] All {max_rounds} speech rounds committed; resuming directly to Adjudication.")
            else:
                resume_round = 1
                resume_target = "retrieve_pro_evidence"
                latest_pro = None
                latest_con = None

            return {
                "status": "debating",
                "current_round": resume_round,
                "max_rounds": max_rounds,
                "resume_target": resume_target,
                "transcript": resumed_transcript,
                "latest_pro_argument": latest_pro,
                "latest_con_argument": latest_con,
                "permanent_context": perm_context,
                "rolling_summary": None,
                "telemetry": [],
                "error": None
            }

    import time
    from datetime import timezone
    metrics = dict(state.get("metrics") or {})
    if "started_at_perf" not in metrics:
        metrics["started_at_perf"] = time.perf_counter()
    if "created_at_utc" not in metrics:
        metrics["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    if "queue_wait_sec" not in metrics:
        metrics["queue_wait_sec"] = 0.0
    if "db_persistence_sec" not in metrics:
        metrics["db_persistence_sec"] = 0.0
    if "rounds" not in metrics:
        metrics["rounds"] = {}
    if not metrics.get("research"):
        res_timings = state.get("research_timings")
        if not res_timings and scope in ("web", "web_research"):
            from ..services.research_service import research_cache
            cached_res = research_cache.get_topic(topic)
            if cached_res and cached_res.get("timings"):
                res_timings = cached_res["timings"]
        metrics["research"] = res_timings

    initial_max_rounds = state.get("max_rounds") or (debate.rounds if (debate and debate.rounds) else 3)
    return {
        "status": "debating",
        "current_round": 1,
        "max_rounds": initial_max_rounds,
        "resume_target": "retrieve_pro_evidence",
        "transcript": state.get("transcript", []) or [],
        "latest_pro_argument": None,
        "latest_con_argument": None,
        "permanent_context": perm_context,
        "rolling_summary": None,
        "telemetry": [],
        "metrics": metrics,
        "error": None
    }

# Node 2: retrieve_pro_evidence
def retrieve_pro_evidence(state: DebateGraphState) -> Dict[str, Any]:
    round_num = state.get("current_round", 1)
    debate_id = state.get("debate_id", "")
    if is_debate_cancelled(debate_id) or state.get("status") == "cancelled":
        logger.info(f"[Graph] Debate {debate_id} cancelled before PRO evidence retrieval.")
        return {"status": "cancelled"}

    logger.info(f"[Graph] retrieve_pro_evidence for Round {round_num}")
    topic = state.get("topic", "")
    scope = state.get("source_scope", "document")
    doc_id = state.get("document_ids", [None])[0] if state.get("document_ids") else None
    latest_con = state.get("latest_con_argument")

    import time
    from datetime import timezone
    metrics = dict(state.get("metrics") or {})
    rounds_meta = metrics.setdefault("rounds", {})
    if round_num not in rounds_meta:
        rounds_meta[round_num] = {
            "round_number": round_num,
            "started_at_perf": time.perf_counter(),
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "pro": {},
            "con": {}
        }

    debate_stream_service.publish(debate_id, "phase", {
        "phase": "retrieval",
        "speaker": "PRO",
        "round": round_num,
        "message": f"Round {round_num}: Retrieving verified document evidence for Gemma (PRO)..."
    })

    evidence = rag_service.retrieve_evidence_for_turn(
        topic=topic,
        opponent_argument=latest_con,
        speaker="PRO",
        document_id=doc_id,
        source_scope=scope
    )
    context_str = rag_service.format_evidence_context(evidence)

    return {
        "current_speaker": "PRO",
        "current_pro_evidence": evidence,
        "pro_evidence_context": context_str,
        "metrics": metrics
    }

# Node 3: pro_agent
def pro_agent_node(state: DebateGraphState) -> Dict[str, Any]:
    round_num = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 3)
    debate_id = state.get("debate_id", "")
    if is_debate_cancelled(debate_id) or state.get("status") == "cancelled":
        logger.info(f"[Graph] Debate {debate_id} cancelled prior to PRO turn execution.")
        return {
            "current_pro_turn": None,
            "status": "cancelled",
            "error": "Debate was cancelled by user."
        }

    logger.info(f"[Graph] pro_agent executing turn for Round {round_num}")
    
    debate_stream_service.publish(debate_id, "phase", {
        "phase": "generation",
        "speaker": "PRO",
        "round": round_num,
        "message": f"Round {round_num}: Gemma (PRO) synthesizing affirmative case..."
    })

    debate_stream_service.publish(debate_id, "speaker_start", {
        "speaker": "PRO",
        "round": round_num,
        "model": "gemma-4-E4B-Q4_0",
        "message": f"Round {round_num}: Gemma (PRO) synthesizing affirmative case..."
    })

    def on_token_callback(delta: str):
        if is_debate_cancelled(debate_id):
            logger.info(f"[Graph] Debate {debate_id} cancelled during PRO generation.")
            raise DebateCancelledException("Debate was cancelled by user.")
        debate_stream_service.publish(debate_id, "token", {
            "speaker": "PRO",
            "round": round_num,
            "delta": delta
        })

    try:
        turn = pro_agent.generate_turn(
            topic=state.get("topic", ""),
            round_number=round_num,
            max_rounds=max_rounds,
            evidence_context=state.get("pro_evidence_context", ""),
            latest_con_argument=state.get("latest_con_argument"),
            debate_history=state.get("transcript", []),
            max_new_tokens=settings.PRO_MAX_NEW_TOKENS,
            retrieved_evidence=state.get("current_pro_evidence", []),
            on_token=on_token_callback,
            permanent_context=state.get("permanent_context"),
            rolling_summary=state.get("rolling_summary")
        )
    except DebateCancelledException:
        logger.info(f"[Graph] PRO generation safely halted due to cancellation for debate {debate_id}")
        return {
            "current_pro_turn": None,
            "status": "cancelled",
            "error": "Debate was cancelled by user."
        }
    except Exception as e:
        err_msg = f"Round {round_num} PRO generation failed: {e}"
        logger.error(f"[Graph] {err_msg}", exc_info=True)
        debate_stream_service.publish(debate_id, "error", {
            "speaker": "PRO",
            "round": round_num,
            "message": err_msg
        })
        debate_stream_service.publish(debate_id, "failed", {
            "status": "failed",
            "error": err_msg,
            "message": err_msg
        })
        with SessionLocal() as db:
            debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
            if debate:
                debate.status = "failed"
                debate.error_message = err_msg
                db.commit()
        return {
            "current_pro_turn": None,
            "status": "failed",
            "error": err_msg
        }

    dur_sec = turn.get("duration_seconds") or 0.0
    ttft_val = turn.get("ttft_seconds")
    tok_speed = turn.get("tokens_per_second")
    gen_tokens = turn.get("completion_tokens") or turn.get("generated_tokens") or len((turn.get("content") or "").split())
    if not tok_speed and dur_sec > 0:
        tok_speed = round(gen_tokens / dur_sec, 2)

    import time
    from datetime import timezone
    metrics = dict(state.get("metrics") or {})
    rounds_meta = metrics.setdefault("rounds", {})
    r_meta = rounds_meta.setdefault(round_num, {
        "round_number": round_num,
        "started_at_perf": time.perf_counter(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "pro": {},
        "con": {}
    })
    r_meta["pro"] = {
        "speaker": "PRO",
        "model": "gemma-4-E4B-Q4_0",
        "queue_wait_sec": metrics.get("queue_wait_sec", 0.0) if round_num == 1 else 0.0,
        "model_load_sec": turn.get("model_load_seconds", 0.0),
        "prompt_prep_sec": turn.get("prompt_prep_seconds", 0.01),
        "ttft_sec": ttft_val,
        "generation_duration_sec": dur_sec,
        "generated_tokens": gen_tokens,
        "tokens_per_second": tok_speed,
        "input_tokens": turn.get("prompt_tokens", 0)
    }

    debate_stream_service.publish(debate_id, "performance_update", {
        "speaker": "PRO",
        "round": round_num,
        "stage": "pro",
        "duration_sec": dur_sec,
        "tokens": gen_tokens,
        "tokens_per_second": tok_speed,
        "ttft_sec": ttft_val
    })

    telem_record = {
        "speaker": "PRO",
        "model": "gemma-4-E4B-Q4_0",
        "round": round_num,
        "ttft_seconds": turn.get("ttft_seconds"),
        "prompt_tokens": turn.get("prompt_tokens"),
        "cache_tokens": turn.get("cache_tokens"),
        "tokens_per_second": tok_speed,
        "duration_seconds": dur_sec,
        "generated_tokens": gen_tokens
    }
    debate_stream_service.publish(debate_id, "telemetry", telem_record)

    telemetry_list = list(state.get("telemetry") or [])
    telemetry_list.append(telem_record)

    debate_stream_service.publish(debate_id, "speaker_done", {
        "speaker": "PRO",
        "round": round_num,
        "title": turn.get("title", f"Round {round_num}: Affirmative Thesis"),
        "text": turn.get("content", ""),
        "telemetry": telem_record
    })

    return {
        "current_pro_turn": turn,
        "telemetry": telemetry_list,
        "metrics": metrics
    }

# Node 4: save_pro_message
def save_pro_message(state: DebateGraphState) -> Dict[str, Any]:
    turn = state.get("current_pro_turn")
    debate_id = state.get("debate_id")
    round_num = state.get("current_round", 1)

    if state.get("status") == "cancelled" or is_debate_cancelled(debate_id):
        logger.info(f"[Graph] save_pro_message skipping persist due to debate cancellation (Round {round_num})")
        return {"status": "cancelled"}

    if state.get("status") == "failed" or not turn:
        logger.warning(f"[Graph] save_pro_message skipping persist due to failed turn state (Round {round_num})")
        return {
            "status": "failed",
            "error": state.get("error") or "Missing PRO turn content to persist"
        }

    evidence = turn.get("evidence_references") or state.get("current_pro_evidence", [])
    logger.info(f"[Graph] save_pro_message for Round {round_num}")

    is_valid = turn.get("is_valid", True)
    is_truncated = turn.get("is_truncated", False)
    validation_errors = turn.get("validation_errors", [])
    error_text = "; ".join(validation_errors) if validation_errors else None

    exec_status = turn.get("execution_status", "SIMULATED")
    clean_ev = [e for e in (evidence or []) if not (isinstance(e, dict) and e.get("__meta__"))]
    clean_ev.append({"__meta__": True, "execution_status": exec_status})

    import time
    t_save_start = time.perf_counter()
    with SessionLocal() as db:
        existing_msg = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id,
            DebateMessageModel.round_number == round_num,
            DebateMessageModel.role == "PRO"
        ).first()
        if existing_msg:
            existing_msg.title = turn.get("title", existing_msg.title)
            existing_msg.content = turn.get("content", existing_msg.content)
            existing_msg.confidence = turn.get("confidence", existing_msg.confidence)
            existing_msg.evidence_references = clean_ev
        else:
            msg = DebateMessageModel(
                id=str(uuid.uuid4()),
                debate_id=debate_id,
                round_number=round_num,
                speaker="DEBATER_A",
                role="PRO",
                title=turn.get("title", f"Round {round_num} Affirmative Argument"),
                content=turn.get("content", ""),
                confidence=turn.get("confidence", 92.0),
                evidence_references=clean_ev
            )
            db.add(msg)

        if not is_valid and not turn.get("content"):
            existing_round = db.query(DebateRoundModel).filter(
                DebateRoundModel.debate_id == debate_id,
                DebateRoundModel.round_number == round_num
            ).first()
            if existing_round:
                existing_round.status = "failed"
            else:
                round_rec = DebateRoundModel(
                    id=str(uuid.uuid4()),
                    debate_id=debate_id,
                    round_number=round_num,
                    status="failed"
                )
                db.add(round_rec)
            debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
            if debate:
                debate.status = "failed"
                debate.error_message = f"Round {round_num} PRO failed completion validation: {error_text}"
        db.commit()

    t_save_dur = time.perf_counter() - t_save_start
    metrics = dict(state.get("metrics") or {})
    metrics["db_persistence_sec"] = round(metrics.get("db_persistence_sec", 0.0) + t_save_dur, 4)

    transcript_item = {
        "speaker": "DEBATER_A",
        "role": "PRO",
        "round_number": round_num,
        "title": turn.get("title", ""),
        "content": turn.get("content", ""),
        "main_claim": turn.get("main_claim", ""),
        "reasoning_summary": turn.get("reasoning_summary", ""),
        "limitations": turn.get("limitations"),
        "evidence": evidence,
        "is_valid": is_valid,
        "is_truncated": is_truncated,
        "validation_errors": validation_errors,
        "finish_reason": turn.get("finish_reason", "stop"),
        "timestamp": datetime.utcnow().isoformat()
    }
    # Filter out existing round/role entry to guarantee idempotence in transcript
    existing_transcripts = [
        t for t in state.get("transcript", [])
        if not (t.get("round_number") == round_num and t.get("role") == "PRO")
    ]
    new_transcript = existing_transcripts + [transcript_item]

    res = {
        "transcript": new_transcript,
        "latest_pro_argument": turn.get("content", ""),
        "metrics": metrics
    }
    if not is_valid and not turn.get("content"):
        res["status"] = "failed"
        res["error"] = f"Round {round_num} PRO failed completion validation: {error_text}"
    return res

# Node 5: retrieve_con_evidence
def retrieve_con_evidence(state: DebateGraphState) -> Dict[str, Any]:
    round_num = state.get("current_round", 1)
    debate_id = state.get("debate_id", "")
    if is_debate_cancelled(debate_id) or state.get("status") == "cancelled":
        logger.info(f"[Graph] Debate {debate_id} cancelled before CON evidence retrieval.")
        return {"status": "cancelled"}

    logger.info(f"[Graph] retrieve_con_evidence for Round {round_num}")
    topic = state.get("topic", "")
    scope = state.get("source_scope", "document")
    doc_id = state.get("document_ids", [None])[0] if state.get("document_ids") else None
    latest_pro = state.get("latest_pro_argument")

    debate_stream_service.publish(debate_id, "phase", {
        "phase": "retrieval",
        "speaker": "CON",
        "round": round_num,
        "message": f"Round {round_num}: Retrieving counter-evidence from document for Qwen (CON)..."
    })

    evidence = rag_service.retrieve_evidence_for_turn(
        topic=topic,
        opponent_argument=latest_pro,
        speaker="CON",
        document_id=doc_id,
        source_scope=scope
    )
    context_str = rag_service.format_evidence_context(evidence)

    return {
        "current_speaker": "CON",
        "current_con_evidence": evidence,
        "con_evidence_context": context_str
    }

# Node 6: con_agent
def con_agent_node(state: DebateGraphState) -> Dict[str, Any]:
    round_num = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 3)
    debate_id = state.get("debate_id", "")
    if is_debate_cancelled(debate_id) or state.get("status") == "cancelled":
        logger.info(f"[Graph] Debate {debate_id} cancelled prior to CON turn execution.")
        return {
            "current_con_turn": None,
            "status": "cancelled",
            "error": "Debate was cancelled by user."
        }

    logger.info(f"[Graph] con_agent executing turn for Round {round_num}")
    
    con_max_tokens = state.get("con_max_tokens") or settings.CON_MAX_NEW_TOKENS
    debate_stream_service.publish(debate_id, "phase", {
        "phase": "generation",
        "speaker": "CON",
        "round": round_num,
        "message": f"Round {round_num}: Qwen (CON) synthesizing direct rebuttal..."
    })

    debate_stream_service.publish(debate_id, "speaker_start", {
        "speaker": "CON",
        "round": round_num,
        "model": "Qwen2.5-VL-7B-Instruct",
        "message": f"Round {round_num}: Qwen (CON) synthesizing direct rebuttal..."
    })

    def on_token_callback(delta: str):
        if is_debate_cancelled(debate_id):
            logger.info(f"[Graph] Debate {debate_id} cancelled during CON generation.")
            raise DebateCancelledException("Debate was cancelled by user.")
        debate_stream_service.publish(debate_id, "token", {
            "speaker": "CON",
            "round": round_num,
            "delta": delta
        })

    try:
        turn = con_agent.generate_turn(
            topic=state.get("topic", ""),
            round_number=round_num,
            max_rounds=max_rounds,
            evidence_context=state.get("con_evidence_context", ""),
            latest_pro_argument=state.get("latest_pro_argument"),
            debate_history=state.get("transcript", []),
            max_new_tokens=con_max_tokens,
            retrieved_evidence=state.get("current_con_evidence", []),
            on_token=on_token_callback,
            permanent_context=state.get("permanent_context"),
            rolling_summary=state.get("rolling_summary"),
            debate_id=debate_id
        )
    except DebateCancelledException:
        logger.info(f"[Graph] CON generation safely halted due to cancellation for debate {debate_id}")
        return {
            "current_con_turn": None,
            "status": "cancelled",
            "error": "Debate was cancelled by user."
        }
    except Exception as e:
        err_msg = f"Round {round_num} CON generation failed: {e}"
        logger.error(f"[Graph] {err_msg}", exc_info=True)
        debate_stream_service.publish(debate_id, "error", {
            "speaker": "CON",
            "round": round_num,
            "message": err_msg
        })
        debate_stream_service.publish(debate_id, "failed", {
            "status": "failed",
            "error": err_msg,
            "message": err_msg
        })
        with SessionLocal() as db:
            debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
            if debate:
                debate.status = "failed"
                debate.error_message = err_msg
                db.commit()
        return {
            "current_con_turn": None,
            "status": "failed",
            "error": err_msg
        }

    dur_sec = turn.get("duration_seconds") or 0.0
    ttft_val = turn.get("ttft_seconds")
    tok_speed = turn.get("tokens_per_second")
    gen_tokens = turn.get("completion_tokens") or turn.get("generated_tokens") or len((turn.get("content") or "").split())
    if not tok_speed and dur_sec > 0:
        tok_speed = round(gen_tokens / dur_sec, 2)

    import time
    from datetime import timezone
    metrics = dict(state.get("metrics") or {})
    rounds_meta = metrics.setdefault("rounds", {})
    r_meta = rounds_meta.setdefault(round_num, {
        "round_number": round_num,
        "started_at_perf": time.perf_counter(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "pro": {},
        "con": {}
    })
    r_meta["con"] = {
        "speaker": "CON",
        "model": "Qwen2.5-VL-7B-Instruct",
        "queue_wait_sec": 0.0,
        "model_load_sec": turn.get("model_load_seconds", 0.0),
        "prompt_prep_sec": turn.get("prompt_prep_seconds", 0.01),
        "ttft_sec": ttft_val,
        "generation_duration_sec": dur_sec,
        "generated_tokens": gen_tokens,
        "tokens_per_second": tok_speed,
        "input_tokens": turn.get("prompt_tokens", 0)
    }

    debate_stream_service.publish(debate_id, "performance_update", {
        "speaker": "CON",
        "round": round_num,
        "stage": "con",
        "duration_sec": dur_sec,
        "tokens": gen_tokens,
        "tokens_per_second": tok_speed,
        "ttft_sec": ttft_val
    })

    telem_record = {
        "speaker": "CON",
        "model": "Qwen2.5-VL-7B-Instruct",
        "round": round_num,
        "ttft_seconds": turn.get("ttft_seconds"),
        "prompt_tokens": turn.get("prompt_tokens"),
        "cache_tokens": turn.get("cache_tokens"),
        "tokens_per_second": tok_speed,
        "duration_seconds": dur_sec,
        "generated_tokens": gen_tokens
    }
    debate_stream_service.publish(debate_id, "telemetry", telem_record)

    telemetry_list = list(state.get("telemetry") or [])
    telemetry_list.append(telem_record)

    debate_stream_service.publish(debate_id, "speaker_done", {
        "speaker": "CON",
        "round": round_num,
        "title": turn.get("title", f"Round {round_num}: Negative Rebuttal"),
        "text": turn.get("content", ""),
        "telemetry": telem_record
    })

    return {
        "current_con_turn": turn,
        "telemetry": telemetry_list,
        "metrics": metrics
    }

# Node 7: save_con_message
def save_con_message(state: DebateGraphState) -> Dict[str, Any]:
    turn = state.get("current_con_turn")
    debate_id = state.get("debate_id")
    round_num = state.get("current_round", 1)

    if state.get("status") == "cancelled" or is_debate_cancelled(debate_id):
        logger.info(f"[Graph] save_con_message skipping persist due to debate cancellation (Round {round_num})")
        return {"status": "cancelled"}

    if state.get("status") == "failed" or not turn:
        logger.warning(f"[Graph] save_con_message skipping persist due to failed turn state (Round {round_num})")
        return {
            "status": "failed",
            "error": state.get("error") or "Missing CON turn content to persist"
        }

    evidence = turn.get("evidence_references") or state.get("current_con_evidence", [])
    logger.info(f"[Graph] save_con_message for Round {round_num}")

    is_valid = turn.get("is_valid", True)
    is_truncated = turn.get("is_truncated", False)
    validation_errors = turn.get("validation_errors", [])
    error_text = "; ".join(validation_errors) if validation_errors else None

    exec_status = turn.get("execution_status", "SIMULATED")
    clean_ev = [e for e in (evidence or []) if not (isinstance(e, dict) and e.get("__meta__"))]
    clean_ev.append({"__meta__": True, "execution_status": exec_status})

    import time
    t_save_start = time.perf_counter()
    with SessionLocal() as db:
        existing_msg = db.query(DebateMessageModel).filter(
            DebateMessageModel.debate_id == debate_id,
            DebateMessageModel.round_number == round_num,
            DebateMessageModel.role == "CON"
        ).first()
        if existing_msg:
            existing_msg.title = turn.get("title", existing_msg.title)
            existing_msg.content = turn.get("content", existing_msg.content)
            existing_msg.confidence = turn.get("confidence", existing_msg.confidence)
            existing_msg.evidence_references = clean_ev
        else:
            msg = DebateMessageModel(
                id=str(uuid.uuid4()),
                debate_id=debate_id,
                round_number=round_num,
                speaker="DEBATER_B",
                role="CON",
                title=turn.get("title", f"Round {round_num} Opposition Argument"),
                content=turn.get("content", ""),
                confidence=turn.get("confidence", 91.0),
                evidence_references=clean_ev
            )
            db.add(msg)

        round_status = "completed" if is_valid else "failed"
        existing_round = db.query(DebateRoundModel).filter(
            DebateRoundModel.debate_id == debate_id,
            DebateRoundModel.round_number == round_num
        ).first()
        if existing_round:
            existing_round.status = round_status
        else:
            round_rec = DebateRoundModel(
                id=str(uuid.uuid4()),
                debate_id=debate_id,
                round_number=round_num,
                status=round_status
            )
            db.add(round_rec)

        if not is_valid and not turn.get("content"):
            debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
            if debate:
                debate.status = "failed"
                debate.error_message = f"Round {round_num} CON failed completion validation: {error_text}"
        db.commit()

    t_save_dur = time.perf_counter() - t_save_start
    metrics = dict(state.get("metrics") or {})
    metrics["db_persistence_sec"] = round(metrics.get("db_persistence_sec", 0.0) + t_save_dur, 4)

    rounds_meta = metrics.setdefault("rounds", {})
    if round_num in rounds_meta:
        r_start = rounds_meta[round_num].get("started_at_perf", time.perf_counter())
        r_dur = round(time.perf_counter() - r_start, 3)
        rounds_meta[round_num]["duration_sec"] = r_dur
        from datetime import timezone
        rounds_meta[round_num]["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        debate_stream_service.publish(debate_id, "performance_update", {
            "round": round_num,
            "stage": "round",
            "duration_sec": r_dur
        })

    transcript_item = {
        "speaker": "DEBATER_B",
        "role": "CON",
        "round_number": round_num,
        "title": turn.get("title", ""),
        "content": turn.get("content", ""),
        "main_claim": turn.get("main_claim", ""),
        "reasoning_summary": turn.get("reasoning_summary", ""),
        "limitations": turn.get("limitations"),
        "evidence": evidence,
        "is_valid": is_valid,
        "is_truncated": is_truncated,
        "validation_errors": validation_errors,
        "finish_reason": turn.get("finish_reason", "stop"),
        "timestamp": datetime.utcnow().isoformat()
    }
    # Filter out existing round/role entry to guarantee idempotence in transcript
    existing_transcripts = [
        t for t in state.get("transcript", [])
        if not (t.get("round_number") == round_num and t.get("role") == "CON")
    ]
    new_transcript = existing_transcripts + [transcript_item]

    res = {
        "transcript": new_transcript,
        "latest_con_argument": turn.get("content", ""),
        "metrics": metrics
    }
    if not is_valid and not turn.get("content"):
        res["status"] = "failed"
        res["error"] = f"Round {round_num} CON failed completion validation: {error_text}"
    return res

# Node 7b: update_rolling_summary
def update_rolling_summary(state: DebateGraphState) -> Dict[str, Any]:
    round_num = state.get("current_round", 1)
    pro_turn = state.get("current_pro_turn") or {}
    con_turn = state.get("current_con_turn") or {}
    prev_summary = state.get("rolling_summary")

    if state.get("status") == "failed":
        return {}

    logger.info(f"[Graph] update_rolling_summary: synthesizing Round {round_num} into Layer B rolling summary")
    try:
        new_summary = context_manager.generate_rolling_summary(
            round_number=round_num,
            pro_turn=pro_turn,
            con_turn=con_turn,
            previous_summary=prev_summary
        )
        is_valid, errors = context_manager.validate_summary(new_summary, prev_summary)
        if not is_valid:
            logger.warning(f"[Graph] Rolling summary validation warnings for Round {round_num}: {errors}")
        else:
            logger.info(f"[Graph] Rolling summary for Round {round_num} successfully validated (thesis chars: PRO={len(new_summary.pro_core_thesis)}, CON={len(new_summary.con_core_thesis)})")

        return {"rolling_summary": new_summary}
    except Exception as e:
        logger.error(f"[Graph] Error generating rolling summary for Round {round_num}: {e}")
        return {}

# Node 8: increment_round
def increment_round(state: DebateGraphState) -> Dict[str, Any]:
    debate_id = state.get("debate_id", "")
    if state.get("status") == "cancelled" or is_debate_cancelled(debate_id):
        logger.info(f"[Graph] increment_round: debate {debate_id} cancelled, stopping.")
        return {"status": "cancelled"}
    new_round = state.get("current_round", 1) + 1
    max_rounds = state.get("max_rounds", 3)
    logger.info(f"[Graph] increment_round: advancing to Round {new_round} of {max_rounds}")
    return {
        "current_round": new_round,
        "max_rounds": max_rounds,
        "current_pro_turn": None,
        "current_con_turn": None
    }

# Node 9: compile_complete_transcript
def compile_complete_transcript(state: DebateGraphState) -> Dict[str, Any]:
    debate_id = state.get("debate_id", "")
    if state.get("status") == "cancelled" or is_debate_cancelled(debate_id):
        logger.info(f"[Graph] compile_complete_transcript: debate {debate_id} cancelled, stopping.")
        return {"status": "cancelled"}
    transcript = state.get("transcript", [])
    max_rounds = state.get("max_rounds", 3)
    expected_turns = max_rounds * 2
    logger.info(f"[Graph] compile_complete_transcript assembled {len(transcript)} / {expected_turns} expected turns")

    if len(transcript) < expected_turns:
        err = f"Incomplete debate: expected {expected_turns} turns ({max_rounds} rounds), but only {len(transcript)} turns exist. Refusing to adjudicate incomplete debate."
        logger.error(f"[Graph] {err}")
        return {
            "status": "failed",
            "error": err
        }

    # Strict audit: verify no unresolved invalid or incomplete turn exists
    for t in transcript:
        if t.get("is_valid") is False:
            err = f"Unresolved incomplete/invalid turn in Round {t.get('round_number')} ({t.get('role')}): {', '.join(t.get('validation_errors', []))}"
            logger.error(f"[Graph] {err}. Refusing to adjudicate incomplete debate.")
            return {
                "status": "failed",
                "error": err
            }

    # Hardware guard: Stop all local debater models to release RAM (~5.5 GB) before external Judge API execution
    try:
        from ..llm.model_manager import local_model_manager
        logger.info(f"[Graph] Debater turns complete. Releasing local debater models from RAM before Judge adjudication (Available RAM: {local_model_manager.get_available_ram_gb():.2f} GiB)...")
        local_model_manager.stop_all_servers()
        logger.info(f"[Graph] Local debater models unloaded. Available RAM for Judge: {local_model_manager.get_available_ram_gb():.2f} GiB")
    except Exception as e:
        logger.warning(f"[Graph] Error during pre-judge model deallocation: {e}")

    return {
        "status": "evaluating"
    }

# Node 10: judge_agent
def judge_agent_node(state: DebateGraphState) -> Dict[str, Any]:
    debate_id = state.get("debate_id", "")
    logger.info(f"[Graph] judge_agent adjudicating debate")

    if state.get("status") == "failed":
        logger.warning("[Graph] judge_agent invoked on failed debate state; refusing to call external Judge API.")
        return {
            "judge_report": {
                "winner": "FAILED",
                "status": "failed",
                "error_message": state.get("error") or "Adjudication skipped due to incomplete turn",
                "pro_score": 0.0,
                "con_score": 0.0,
                "judge_reasoning": "Judge cannot evaluate an incomplete or failed debate transcript.",
                "balanced_verdict": "No verdict rendered due to incomplete dialectical transcript."
            }
        }

    topic = state.get("topic", "")
    transcript = state.get("transcript", [])
    judge_provider = (state.get("judge_provider") or getattr(settings, "JUDGE_PROVIDER", "nvidia")).strip().lower()
    judge_model = state.get("judge_model") or (
        getattr(settings, "NVIDIA_JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
        if judge_provider == "nvidia"
        else getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash")
    )
    provider_label = "NVIDIA NIM" if judge_provider == "nvidia" else "Google Gemini"
    
    debate_stream_service.publish(debate_id, "judge_start", {
        "provider": judge_provider,
        "model": judge_model,
        "message": f"Independent Judge ({provider_label} - {judge_model}) evaluating complete dialectical transcript..."
    })

    t_judge_start = time.perf_counter()
    from datetime import timezone
    judge_start_utc = datetime.now(timezone.utc).isoformat()

    # Collect all citations from transcript and turn contexts
    citations = []
    for t in transcript:
        for ev in t.get("evidence", []):
            citations.append(ev)
    for ev in state.get("current_pro_evidence", []):
        citations.append(ev)
    for ev in state.get("current_con_evidence", []):
        citations.append(ev)

    # For image-grounded debates, inject full visual evidence pool from document metadata
    doc_ids = state.get("document_ids") or []
    if doc_ids and doc_ids[0]:
        try:
            from ..models.document import DocumentModel
            with SessionLocal() as db:
                doc_rec = db.query(DocumentModel).filter(DocumentModel.id == doc_ids[0]).first()
                if doc_rec:
                    meta = doc_rec.metadata_json or {}
                    ft = (doc_rec.file_type or "").lower()
                    if meta.get("source_type") == "image" or ft in ("png", "jpg", "jpeg", "webp", "bmp"):
                        for ev_item in meta.get("visual_evidence", []):
                            citations.append({
                                "id": ev_item.get("id"),
                                "evidence_id": ev_item.get("id"),
                                "section": ev_item.get("location") or "Visual Analysis",
                                "source": f"Uploaded Image ({doc_rec.name})",
                                "content": f"{ev_item.get('label')}: {ev_item.get('content')}",
                                "is_image": True
                            })
        except Exception as e:
            logger.debug(f"[Graph] Image citations pool note: {e}")

    t_prep_dur = round(time.perf_counter() - t_judge_start, 3)

    report_schema = judge_agent.evaluate_debate(
        topic=topic,
        transcript=transcript,
        evidence_citations=citations,
        provider=judge_provider,
        judge_model=judge_model
    )
    judge_dur = round(time.perf_counter() - t_judge_start, 3)

    j_perf = getattr(report_schema, "performance_metrics", None) or {}
    gen_tokens = j_perf.get("generated_tokens") or (len((report_schema.judge_reasoning or "").split()) + 120)
    tok_speed = j_perf.get("tokens_per_second") or (round(gen_tokens / judge_dur, 2) if judge_dur > 0 else 0.0)

    metrics = dict(state.get("metrics") or {})
    metrics["judge"] = {
        "provider": judge_provider,
        "model": report_schema.judge_model_used or judge_model,
        "started_at_utc": judge_start_utc,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "prompt_prep_sec": t_prep_dur,
        "ttft_sec": j_perf.get("ttft_sec"),
        "evaluation_duration_sec": judge_dur,
        "generated_tokens": gen_tokens,
        "tokens_per_second": tok_speed,
        "input_tokens": j_perf.get("input_tokens", 0)
    }

    debate_stream_service.publish(debate_id, "performance_update", {
        "stage": "judge",
        "duration_sec": judge_dur,
        "tokens": gen_tokens,
        "tokens_per_second": tok_speed
    })

    debate_stream_service.publish(debate_id, "judge_done", {
        "provider": judge_provider,
        "model": report_schema.judge_model_used or judge_model,
        "winner": report_schema.winner,
        "pro_score": report_schema.pro_score,
        "con_score": report_schema.con_score,
        "balanced_verdict": report_schema.balanced_verdict
    })

    return {"judge_report": report_schema.model_dump(), "metrics": metrics}

# Node 11: validate_judge_output
def validate_judge_output(state: DebateGraphState) -> Dict[str, Any]:
    report_dict = state.get("judge_report")
    logger.info(f"[Graph] validate_judge_output: validating schema")
    if not report_dict:
        raise ValueError("Missing judge report payload")
    
    # Validate strictly with Pydantic
    validated = JudgeReportSchema.model_validate(report_dict)
    if validated.status == "failed" or validated.winner == "FAILED":
        logger.warning("[Graph] Judge evaluation marked as failed. Setting state status to evaluation_failed.")
        return {
            "judge_report": validated.model_dump(),
            "status": "evaluation_failed",
            "error": validated.error_message or "Judge evaluation failed"
        }
    return {
        "judge_report": validated.model_dump(),
        "status": "evaluating"
    }

# Node 12: save_result
def save_result(state: DebateGraphState) -> Dict[str, Any]:
    logger.info(f"[Graph] save_result: persisting final evaluation")
    debate_id = state.get("debate_id")
    state_status = state.get("status")

    # Safe cancellation handler: skip judge and clean up debate records
    if state_status == "cancelled" or is_debate_cancelled(debate_id):
        logger.info(f"[Graph] save_result: debate {debate_id} cancelled by user. Finalizing without adjudication.")
        with SessionLocal() as db:
            debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
            if debate:
                db.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id == debate_id).delete(synchronize_session=False)
                db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).delete(synchronize_session=False)
                db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == debate_id).delete(synchronize_session=False)
                db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == debate_id).delete(synchronize_session=False)
                db.delete(debate)
                db.commit()

        try:
            from ..llm.model_manager import local_model_manager
            local_model_manager.unload_all()
        except Exception as e:
            logger.warning(f"Failed to unload model memory after cancelled debate: {e}")

        debate_stream_service.publish(debate_id, "cancelled", {
            "status": "cancelled",
            "winner": "CANCELLED",
            "message": "Debate execution cancelled by user."
        })
        return {
            "status": "cancelled",
            "error": "Debate execution cancelled by user.",
            "winner": "CANCELLED"
        }

    report = state.get("judge_report") or {}

    eval_status = report.get("status", "completed")
    winner = report.get("winner", "INCONCLUSIVE")
    state_status = state.get("status")

    is_failed = (
        state_status == "failed"
        or state_status == "evaluation_failed"
        or eval_status == "failed"
        or winner == "FAILED"
    )
    final_debate_status = "failed" if state_status == "failed" else ("evaluation_failed" if is_failed else "completed")
    error_msg = state.get("error") or report.get("error_message") if is_failed else None

    if is_failed:
        final_eval_winner = report.get("winner") if (report.get("winner") == "FAILED") else "FAILED"
        final_eval_status = "failed"
        final_pro_score = 0.0
        final_con_score = 0.0
        final_rel_score = 0.0
        final_reasoning = report.get("judge_reasoning") or (
            f"Adjudication aborted: debate terminated early due to {error_msg or 'turn validation failure'}."
            if state_status == "failed"
            else "Judge evaluation failed."
        )
        final_verdict = report.get("balanced_verdict") or "No verdict rendered: debate did not complete all required turns."
        final_raw_payload = report if report else {"status": "failed", "winner": "FAILED", "error_message": error_msg}
    else:
        final_eval_winner = report.get("winner", "INCONCLUSIVE")
        final_eval_status = "completed"
        final_pro_score = report.get("pro_score", 85.0)
        final_con_score = report.get("con_score", 84.0)
        final_rel_score = report.get("evidence_reliability_score", 88.0)
        final_reasoning = report.get("judge_reasoning", "")
        final_verdict = report.get("balanced_verdict", "")
        final_raw_payload = report

    import time
    t_save_start = time.perf_counter()
    with SessionLocal() as db:
        existing_eval = db.query(JudgeEvaluationModel).filter(
            JudgeEvaluationModel.debate_id == debate_id
        ).first()
        if existing_eval:
            existing_eval.pro_score = final_pro_score
            existing_eval.con_score = final_con_score
            existing_eval.winner = final_eval_winner
            existing_eval.status = final_eval_status
            existing_eval.pro_strengths = report.get("pro_strengths", [])
            existing_eval.pro_weaknesses = report.get("pro_weaknesses", [])
            existing_eval.con_strengths = report.get("con_strengths", [])
            existing_eval.con_weaknesses = report.get("con_weaknesses", [])
            existing_eval.key_points = [p if isinstance(p, dict) else p.model_dump() for p in report.get("round_points", [])]
            existing_eval.judge_reasoning = final_reasoning
            existing_eval.balanced_verdict = final_verdict
            existing_eval.evidence_reliability_score = final_rel_score
            existing_eval.raw_payload = final_raw_payload
        else:
            eval_record = JudgeEvaluationModel(
                id=str(uuid.uuid4()),
                debate_id=debate_id,
                pro_score=final_pro_score,
                con_score=final_con_score,
                winner=final_eval_winner,
                status=final_eval_status,
                pro_strengths=report.get("pro_strengths", []),
                pro_weaknesses=report.get("pro_weaknesses", []),
                con_strengths=report.get("con_strengths", []),
                con_weaknesses=report.get("con_weaknesses", []),
                key_points=[p if isinstance(p, dict) else p.model_dump() for p in report.get("round_points", [])],
                judge_reasoning=final_reasoning,
                balanced_verdict=final_verdict,
                evidence_reliability_score=final_rel_score,
                raw_payload=final_raw_payload
            )
            db.add(eval_record)

        debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        if debate:
            debate.status = final_debate_status
            if is_failed:
                debate.error_message = error_msg or "Debate stopped due to failed turn or evaluation"
        db.commit()

    t_save_dur = time.perf_counter() - t_save_start
    metrics = dict(state.get("metrics") or {})
    metrics["db_persistence_sec"] = round(metrics.get("db_persistence_sec", 0.0) + t_save_dur, 4)

    from datetime import timezone
    total_wall_clock_sec = round(time.perf_counter() - metrics.get("started_at_perf", time.perf_counter()), 3)
    completed_at_utc = datetime.now(timezone.utc).isoformat()

    rounds_list = []
    total_pro_sec = 0.0
    total_con_sec = 0.0
    total_pro_tokens = 0
    total_con_tokens = 0

    for r_num in sorted(metrics.get("rounds", {}).keys()):
        r_data = metrics["rounds"][r_num]
        p = r_data.get("pro", {})
        c = r_data.get("con", {})
        total_pro_sec += p.get("generation_duration_sec", 0.0)
        total_con_sec += c.get("generation_duration_sec", 0.0)
        total_pro_tokens += p.get("generated_tokens", 0)
        total_con_tokens += c.get("generated_tokens", 0)
        rounds_list.append({
            "round_number": r_num,
            "started_at_utc": r_data.get("started_at_utc"),
            "completed_at_utc": r_data.get("completed_at_utc"),
            "duration_sec": r_data.get("duration_sec", 0.0),
            "pro": p,
            "con": c
        })

    judge_data = metrics.get("judge") or {}
    judge_sec = judge_data.get("evaluation_duration_sec", 0.0)
    judge_tokens = judge_data.get("generated_tokens", 0)

    total_generation_sec = round(total_pro_sec + total_con_sec + judge_sec, 3)
    total_generated_tokens = total_pro_tokens + total_con_tokens + judge_tokens
    avg_speed = round(total_generated_tokens / total_generation_sec, 2) if total_generation_sec > 0 else 0.0

    # Collect source / PDF metrics
    source_count = 0
    pdfs_processed = 0
    pages_extracted = 0
    try:
        from ..models.research import ResearchSourceModel
        with SessionLocal() as db_src:
            sources = db_src.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id == debate_id).all()
            source_count = len(sources)
            for s in sources:
                meta = s.metadata_json or {}
                if meta.get("content_type") == "FULL_PDF_TEXT":
                    pdfs_processed += 1
                    pages_extracted += int(meta.get("pages_extracted") or meta.get("page_count") or 0)
    except Exception:
        pass

    final_performance_metrics = {
        "debate_id": debate_id,
        "topic": state.get("topic"),
        "evidence_mode": state.get("source_scope", "document"),
        "source_count": source_count,
        "pdfs_processed": pdfs_processed,
        "pages_extracted": pages_extracted,
        "completion_status": final_debate_status,
        "created_at_utc": metrics.get("created_at_utc"),
        "started_at_utc": metrics.get("created_at_utc"),
        "completed_at_utc": completed_at_utc,
        "total_elapsed_sec": total_wall_clock_sec,
        "total_generation_sec": total_generation_sec,
        "total_pro_sec": round(total_pro_sec, 3),
        "total_con_sec": round(total_con_sec, 3),
        "total_judge_sec": round(judge_sec, 3),
        "rounds_count": len(rounds_list),
        "total_generated_tokens": total_generated_tokens,
        "avg_tokens_per_second": avg_speed,
        "queue_wait_sec": metrics.get("queue_wait_sec", 0.0),
        "db_persistence_sec": round(metrics.get("db_persistence_sec", 0.0), 4),
        "research": metrics.get("research"),
        "pro_total": {
            "duration_sec": round(total_pro_sec, 3),
            "tokens": total_pro_tokens,
            "avg_tokens_per_second": round(total_pro_tokens / total_pro_sec, 2) if total_pro_sec > 0 else 0.0
        },
        "con_total": {
            "duration_sec": round(total_con_sec, 3),
            "tokens": total_con_tokens,
            "avg_tokens_per_second": round(total_con_tokens / total_con_sec, 2) if total_con_sec > 0 else 0.0
        },
        "judge": judge_data,
        "rounds": rounds_list
    }

    with SessionLocal() as db:
        deb = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
        if deb:
            deb.performance_metrics = final_performance_metrics
            db.commit()

    debate_stream_service.publish(debate_id, "performance_metrics", final_performance_metrics)

    # Free model memory after debate completes or fails to prevent lingering RAM usage
    try:
        from ..llm.model_manager import local_model_manager
        local_model_manager.unload_all()
    except Exception as e:
        logger.warning(f"Failed to unload model memory after debate run: {e}")

    if final_debate_status == "failed":
        debate_stream_service.publish(debate_id, "failed", {
            "status": "failed",
            "error": error_msg or "Debate ended with failure",
            "message": error_msg or "Debate ended with failure",
            "performance_metrics": final_performance_metrics
        })
    debate_stream_service.publish(debate_id, "completed", {
        "status": final_debate_status,
        "winner": final_eval_winner,
        "error": error_msg if final_debate_status == "failed" else None,
        "message": "Debate Adjudication Complete!" if final_debate_status == "completed" else (error_msg or "Debate ended with failure"),
        "performance_metrics": final_performance_metrics
    })

    return {
        "status": final_debate_status,
        "error": error_msg,
        "winner": final_eval_winner,
        "metrics": final_performance_metrics
    }

# Conditional routing edges
def check_initial_routing(state: DebateGraphState) -> str:
    resume_target = state.get("resume_target")
    if resume_target:
        logger.info(f"[Graph Routing] Resuming graph directly to target: '{resume_target}'")
        return resume_target

    transcript = state.get("transcript", [])
    max_rounds = state.get("max_rounds", 3)
    con_turns = [t for t in transcript if t.get("role") == "CON"]
    if len(con_turns) >= max_rounds:
        logger.info(f"[Graph Routing] All {max_rounds} rounds already completed ({len(con_turns)} CON turns). Routing directly to compile_complete_transcript.")
        return "compile_complete_transcript"
    return "retrieve_pro_evidence"

def check_pro_turn_routing(state: DebateGraphState) -> str:
    debate_id = state.get("debate_id", "")
    if state.get("status") in ("cancelled", "failed") or is_debate_cancelled(debate_id):
        logger.warning(f"[Graph Routing] PRO turn state is {state.get('status')}; routing directly to save_result.")
        return "save_result"
    if state.get("status") == "failed" and not state.get("latest_pro_argument"):
        logger.warning("[Graph Routing] PRO turn produced no argument; routing directly to save_result.")
        return "save_result"
    return "retrieve_con_evidence"

def should_continue_debate(state: DebateGraphState) -> str:
    debate_id = state.get("debate_id", "")
    if state.get("status") in ("cancelled", "failed") or is_debate_cancelled(debate_id):
        logger.warning(f"[Graph Condition] Debate status is {state.get('status')}; routing directly to save_result.")
        return "save_result"
    current = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 3)
    logger.info(f"[Graph Condition] check_rounds: current={current}, max={max_rounds}")
    if current < max_rounds:
        return "increment_round"
    return "compile_complete_transcript"

def check_adjudication_routing(state: DebateGraphState) -> str:
    debate_id = state.get("debate_id", "")
    if state.get("status") in ("cancelled", "failed") or is_debate_cancelled(debate_id):
        logger.warning(f"[Graph Routing] State is {state.get('status')}; bypassing judge_agent directly to save_result.")
        return "save_result"
    return "judge_agent"
