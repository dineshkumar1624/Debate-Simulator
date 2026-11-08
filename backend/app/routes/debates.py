import uuid
import threading
import json
import logging
import asyncio
import queue
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from ..database.session import get_db, SessionLocal
from ..services.debate_stream_service import debate_stream_service
from ..models.debate import DebateModel, DebateRoundModel, DebateMessageModel, JudgeEvaluationModel
from ..models.document import DocumentModel
from ..models.research import ResearchSourceModel
from ..schemas.debate import (
    StartDebateRequest,
    StartDebateResponse,
    DebateSessionSchema,
    DebateConfigSchema,
    DebateRoundSchema,
    DebateTurnSchema,
    DebateSynthesisSchema,
    DebateHistoryItemSchema,
    EvidenceItemSchema,
    DeleteResponse,
)
from ..schemas.judge import JudgeReportSchema
from ..graph.debate_graph import debate_graph
from ..graph.state import DebateGraphState

from ..services.debate_serializer import format_debate_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/debates", tags=["debates"])
_active_debate_lock = threading.Lock()
_running_threads: Dict[str, threading.Thread] = {}
_threads_lock = threading.Lock()
from ..services.cancellation_service import register_cancellation, is_debate_cancelled, clear_cancellation


_format_debate_session = format_debate_session

def start_debate_background_thread(
    debate_id: str,
    topic: str,
    rounds: int,
    document_id: Optional[str],
    source_scope: str,
    judge_provider: Optional[str] = "nvidia",
    judge_model: Optional[str] = None,
    research_timings: Optional[Dict[str, Any]] = None
) -> threading.Thread:
    """
    Spawns and tracks a persistent background thread for LangGraph debate execution.
    Completely decoupled from HTTP request lifetime and browser connection.
    Guarantees thread reference retention to prevent garbage collection.
    """
    with _threads_lock:
        existing = _running_threads.get(debate_id)
        if existing and existing.is_alive():
            logger.info(f"Background thread for debate {debate_id} is already running.")
            return existing

        def runner():
            try:
                _run_debate_in_background(
                    debate_id=debate_id,
                    topic=topic,
                    rounds=rounds,
                    document_id=document_id,
                    source_scope=source_scope,
                    judge_provider=judge_provider,
                    judge_model=judge_model,
                    research_timings=research_timings
                )
            except Exception as ex:
                logger.error(f"Unhandled exception in debate background thread for {debate_id}: {ex}", exc_info=True)
            finally:
                with _threads_lock:
                    _running_threads.pop(debate_id, None)

        thread = threading.Thread(
            target=runner,
            name=f"debate-runner-{debate_id[:8]}",
            daemon=True
        )
        _running_threads[debate_id] = thread
        thread.start()
        logger.info(f"Spawned dedicated background execution thread {thread.name} for debate {debate_id}.")
        return thread


def _run_debate_in_background(
    debate_id: str,
    topic: str,
    rounds: int,
    document_id: Optional[str],
    source_scope: str,
    judge_provider: Optional[str] = "nvidia",
    judge_model: Optional[str] = None,
    research_timings: Optional[Dict[str, Any]] = None
):
    """
    Executes LangGraph debate workflow in background thread/task.
    Enforces hardware exclusivity via _active_debate_lock to guarantee sequential execution.
    """
    import time
    from datetime import timezone
    logger.info(f"Queuing background LangGraph execution for debate {debate_id} (judge: {judge_provider}/{judge_model})")
    t_queue_wait_start = time.perf_counter()
    acquired = _active_debate_lock.acquire(timeout=600)
    queue_wait_duration = time.perf_counter() - t_queue_wait_start
    if not acquired:
        err = f"Debate {debate_id} timed out waiting for hardware execution lock."
        logger.error(err)
        debate_stream_service.publish(debate_id, "failed", {"status": "failed", "error": err, "message": err})
        with SessionLocal() as db:
            deb = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
            if deb:
                deb.status = "failed"
                deb.error_message = err
                db.commit()
        return

    try:
        logger.info(f"Hardware execution lock acquired for debate {debate_id}. Starting execution...")
        initial_state: DebateGraphState = {
            "debate_id": debate_id,
            "topic": topic,
            "document_ids": [document_id] if document_id else [],
            "source_scope": source_scope,
            "current_round": 1,
            "max_rounds": rounds,
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
            "permanent_context": None,
            "rolling_summary": None,
            "telemetry": [],
            "judge_provider": judge_provider,
            "judge_model": judge_model,
            "judge_report": None,
            "resume_target": None,
            "status": "debating",
            "error": None,
            "research_timings": research_timings,
            "metrics": {
                "debate_id": debate_id,
                "topic": topic,
                "source_scope": source_scope,
                "queue_wait_sec": round(queue_wait_duration, 4),
                "started_at_perf": time.perf_counter(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "db_persistence_sec": 0.0,
                "rounds": {},
                "research": research_timings
            }
        }

        try:
            final_state = debate_graph.invoke(initial_state)
            status_val = final_state.get("status")
            logger.info(f"LangGraph execution finished for {debate_id}: status={status_val}")
            if status_val == "failed" and not is_debate_cancelled(debate_id):
                err_msg = final_state.get("error") or "Debate workflow terminated with failed status"
                with SessionLocal() as db:
                    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
                    if debate:
                        debate.status = "failed"
                        debate.error_message = err_msg
                        db.commit()
                debate_stream_service.publish(debate_id, "error", {"error": err_msg, "message": err_msg})
                debate_stream_service.publish(debate_id, "failed", {"status": "failed", "error": err_msg, "message": err_msg})
        except Exception as e:
            if not is_debate_cancelled(debate_id):
                logger.error(f"LangGraph execution error for {debate_id}: {e}", exc_info=True)
                with SessionLocal() as db:
                    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
                    if debate:
                        debate.status = "failed"
                        debate.error_message = str(e)
                        db.commit()
                debate_stream_service.publish(debate_id, "error", {"error": str(e), "message": f"Debate execution error: {e}"})
                debate_stream_service.publish(debate_id, "failed", {"status": "failed", "error": str(e), "message": f"Debate execution error: {e}"})
    finally:
        clear_cancellation(debate_id)
        _active_debate_lock.release()
        logger.info(f"Hardware execution lock released for debate {debate_id}.")

_format_debate_session = format_debate_session

@router.post("", response_model=StartDebateResponse)
def create_or_start_debate(
    payload: StartDebateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if not payload.topic or not payload.topic.strip():
        raise HTTPException(
            status_code=400,
            detail="Debate topic cannot be empty or whitespace-only."
        )

    debate_id = str(uuid.uuid4())
    rounds_val = payload.rounds if payload.rounds is not None else 3
    if rounds_val not in (1, 3, 5):
        if rounds_val <= 1:
            rounds = 1
        elif rounds_val <= 3:
            rounds = 3
        else:
            rounds = 5
    else:
        rounds = rounds_val
    scope = payload.sourceScope or ("document" if payload.documentId else "general_topic")
    if payload.documentId:
        doc = db.query(DocumentModel).filter(DocumentModel.id == payload.documentId).first()
        if doc:
            meta = doc.metadata_json or {}
            ft = (doc.file_type or "").lower()
            if meta.get("source_type") == "image" or ft in ("png", "jpg", "jpeg", "webp", "bmp"):
                scope = "image"

    # Determine judge provider & model
    req_provider = (payload.judgeProvider or "").strip().lower()
    raw_judge = (payload.judgeModel or "").strip()

    if not req_provider:
        if any(term in raw_judge.lower() for term in ["nvidia", "nemotron"]):
            req_provider = "nvidia"
        elif "gemini" in raw_judge.lower():
            req_provider = "gemini"
        else:
            req_provider = getattr(settings, "JUDGE_PROVIDER", "nvidia").strip().lower()

    if req_provider not in ("gemini", "nvidia"):
        req_provider = "nvidia"

    if not raw_judge:
        judge = (
            getattr(settings, "NVIDIA_JUDGE_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b")
            if req_provider == "nvidia"
            else getattr(settings, "GEMINI_MODEL_ID", "gemini-3.5-flash")
        )
    else:
        judge = raw_judge

    # Allowed models check
    allowed_pro = (
        "gemma-4-E4B-Q4_0",
        "gemma-4-E4B-it",
        "D:/models/gemma-4-E4B-Q4/gemma-4-E4B_q4_0-it.gguf",
        "D:/models/gemma-4-E4B-it",
        "gemma"
    )
    allowed_con = (
        "Qwen2.5-VL-7B-Instruct",
        "D:/models_cpu_converted/Qwen2.5-VL-7B-Instruct",
        "D:/models/Qwen2.5-VL-7B-Instruct",
        "qwen"
    )
    allowed_gemini_judge = (
        "gemini-3.5-flash",
        "Gemini 3.5 Flash",
        "gemini-3.8-flash",
        "Gemini 3.8 Flash",
        "gemini"
    )
    allowed_nvidia_judge = (
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.3-70b-instruct",
        "meta/llama-3.1-70b-instruct",
        "mistralai/mixtral-8x22b-instruct-v0.1",
        "nvidia"
    )

    debater_a = payload.debaterAModel or getattr(settings, "GEMMA_MODEL_NAME", "gemma-4-E4B-Q4_0")
    debater_b = payload.debaterBModel or getattr(settings, "QWEN_MODEL_NAME", "Qwen2.5-VL-7B-Instruct")

    if debater_a not in allowed_pro:
        raise HTTPException(
            status_code=400,
            detail=f"Disallowed debater A (PRO) model: '{debater_a}'. Only Google Gemma ('gemma-4-E4B-Q4_0') is permitted."
        )
    if debater_b not in allowed_con:
        raise HTTPException(
            status_code=400,
            detail=f"Disallowed debater B (CON) model: '{debater_b}'. Only Alibaba Qwen ('Qwen2.5-VL-7B-Instruct') is permitted."
        )

    if req_provider == "nvidia":
        if judge not in allowed_nvidia_judge and not judge.startswith("nvidia/") and not judge.startswith("meta/"):
            raise HTTPException(
                status_code=400,
                detail=f"Disallowed NVIDIA NIM judge model: '{judge}'. Supported models include 'nvidia/nemotron-3.5-super-vl-120b-a12b'."
            )
    else:
        if judge not in allowed_gemini_judge:
            raise HTTPException(
                status_code=400,
                detail=f"Disallowed Google Gemini judge model: '{judge}'. Only Google Gemini ('gemini-3.5-flash') is permitted."
            )

    # Check if there is already an active debate currently running on this topic
    existing_active = db.query(DebateModel).filter(
        DebateModel.status.in_(["debating", "running", "queued", "evaluating"]),
        DebateModel.topic == payload.topic
    ).first()
    if existing_active:
        logger.info(f"Reconnecting to existing active debate {existing_active.id} for topic '{payload.topic}'")
        start_debate_background_thread(
            debate_id=existing_active.id,
            topic=existing_active.topic,
            rounds=existing_active.rounds,
            document_id=existing_active.document_id,
            source_scope=existing_active.source_scope,
            judge_provider=getattr(existing_active, "judge_provider", "gemini") or "gemini",
            judge_model=existing_active.judge_model
        )
        from datetime import timezone
        dt_active_utc = existing_active.created_at.replace(tzinfo=timezone.utc) if existing_active.created_at.tzinfo is None else existing_active.created_at
        return StartDebateResponse(
            debateId=existing_active.id,
            status=existing_active.status,
            message="Reconnected to existing active debate in progress",
            startedAtEpochMs=int(dt_active_utc.timestamp() * 1000),
            startedAtIso=dt_active_utc.isoformat()
        )

    debate = DebateModel(
        id=debate_id,
        topic=payload.topic,
        debater_a_model=debater_a,
        debater_b_model=debater_b,
        judge_model=judge,
        judge_provider=req_provider,
        rounds=rounds,
        evidence_mode=payload.evidenceMode if payload.evidenceMode is not None else True,
        strict_fact_checking=payload.strictFactChecking if payload.strictFactChecking is not None else True,
        source_scope=scope,
        document_id=payload.documentId,
        status="debating"
    )
    db.add(debate)
    if scope in ("web", "web_research"):
        db.query(ResearchSourceModel).filter(
            ResearchSourceModel.topic == payload.topic,
            ResearchSourceModel.debate_id.is_(None)
        ).update({"debate_id": debate_id}, synchronize_session=False)
    db.commit()

    # Retrieve research timings if applicable
    from ..services.research_service import research_cache
    cached_res = research_cache.get_topic(payload.topic)
    res_timings = payload.researchTimings or (cached_res.get("timings") if cached_res else None)

    start_debate_background_thread(
        debate_id=debate_id,
        topic=payload.topic,
        rounds=rounds,
        document_id=payload.documentId,
        source_scope=scope,
        judge_provider=req_provider,
        judge_model=judge,
        research_timings=res_timings
    )

    from datetime import timezone
    dt_new_utc = debate.created_at.replace(tzinfo=timezone.utc) if debate.created_at.tzinfo is None else debate.created_at
    return StartDebateResponse(
        debateId=debate_id,
        status="debating",
        message="Debate initialized and LangGraph state machine dispatched",
        startedAtEpochMs=int(dt_new_utc.timestamp() * 1000),
        startedAtIso=dt_new_utc.isoformat()
    )

@router.post("/{debate_id}/start", response_model=StartDebateResponse)
def start_existing_debate(
    debate_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    if debate.status == "debating":
        # Ensure thread is alive
        start_debate_background_thread(
            debate_id=debate.id,
            topic=debate.topic,
            rounds=debate.rounds,
            document_id=debate.document_id,
            source_scope=debate.source_scope,
            judge_provider=getattr(debate, "judge_provider", "gemini") or "gemini",
            judge_model=debate.judge_model
        )
        return StartDebateResponse(
            debateId=debate.id,
            status="debating",
            message="Debate execution is already in progress"
        )

    debate.status = "debating"
    db.commit()

    start_debate_background_thread(
        debate_id=debate.id,
        topic=debate.topic,
        rounds=debate.rounds,
        document_id=debate.document_id,
        source_scope=debate.source_scope,
        judge_provider=getattr(debate, "judge_provider", "gemini") or "gemini",
        judge_model=debate.judge_model
    )

    return StartDebateResponse(
        debateId=debate.id,
        status="debating",
        message="Debate restarted and LangGraph execution resumed"
    )

@router.get("", response_model=List[DebateHistoryItemSchema])
def list_debates(db: Session = Depends(get_db)):
    debates = (
        db.query(DebateModel)
        .options(
            joinedload(DebateModel.document),
            joinedload(DebateModel.evaluation),
            joinedload(DebateModel.round_records),
            joinedload(DebateModel.messages)
        )
        .order_by(DebateModel.created_at.desc())
        .all()
    )
    history = []
    for d in debates:
        doc_name = d.document.name if d.document else None
        ev = d.evaluation
        history.append(DebateHistoryItemSchema(
            id=d.id,
            topic=d.topic,
            createdAt=d.created_at.strftime("%b %d, %Y %I:%M %p") if d.created_at else "Today",
            completedAt=d.updated_at.strftime("%b %d, %Y %I:%M %p") if d.updated_at and d.status in ("completed", "failed", "evaluation_failed") else None,
            roundsCount=len(d.round_records) if d.round_records else (d.rounds or 3),
            status=d.status or "idle",
            documentName=doc_name,
            documentId=d.document_id,
            winner=ev.winner if ev else None,
            proScore=float(ev.pro_score) if (ev and ev.pro_score is not None) else None,
            conScore=float(ev.con_score) if (ev and ev.con_score is not None) else None,
            judgeModel=d.judge_model,
            judgeProvider=getattr(d, "judge_provider", "gemini"),
            messagesCount=len(d.messages) if d.messages else 0
        ))
    return history

@router.get("/active")
def get_active_debate(db: Session = Depends(get_db)):
    """
    Returns the currently active / running debate if one exists.
    Enables frontend clients to seamlessly reconnect across page navigation,
    browser refreshes, or new tabs without losing the active session.
    """
    active_debate = (
        db.query(DebateModel)
        .options(
            joinedload(DebateModel.document),
            joinedload(DebateModel.round_records),
            joinedload(DebateModel.messages),
            joinedload(DebateModel.research_sources)
        )
        .filter(DebateModel.status.in_(["debating", "running", "queued", "evaluating"]))
        .order_by(DebateModel.created_at.desc())
        .first()
    )
    if not active_debate:
        return {
            "hasActive": False,
            "debateId": None,
            "status": None,
            "topic": None,
            "rounds": None,
            "documentId": None,
            "sourceScope": None,
            "evidenceMode": None,
            "startedAtEpochMs": None,
            "elapsedSeconds": None,
            "debate": None
        }

    with _threads_lock:
        t = _running_threads.get(active_debate.id)
        is_thread_alive = t.is_alive() if t else False

    # Auto-resume thread if DB status is active but thread died (e.g. restart survival)
    if not is_thread_alive and active_debate.status in ("debating", "running", "queued"):
        logger.info(f"Resuming background thread for active debate {active_debate.id} from database checkpoint.")
        start_debate_background_thread(
            debate_id=active_debate.id,
            topic=active_debate.topic,
            rounds=active_debate.rounds,
            document_id=active_debate.document_id,
            source_scope=active_debate.source_scope,
            judge_provider=getattr(active_debate, "judge_provider", "gemini") or "gemini",
            judge_model=active_debate.judge_model
        )

    formatted_session = _format_debate_session(active_debate)
    effective_scope = active_debate.source_scope or ("web" if active_debate.document_id is None else "document")
    return {
        "hasActive": True,
        "debateId": active_debate.id,
        "status": active_debate.status,
        "topic": active_debate.topic,
        "rounds": active_debate.rounds,
        "documentId": active_debate.document_id,
        "sourceScope": effective_scope,
        "evidenceMode": bool(active_debate.evidence_mode) if active_debate.evidence_mode is not None else True,
        "startedAtEpochMs": formatted_session.startedAtEpochMs,
        "elapsedSeconds": formatted_session.elapsedSeconds,
        "debate": formatted_session
    }

@router.get("/{debate_id}", response_model=DebateSessionSchema)
def get_debate(debate_id: str, db: Session = Depends(get_db)):
    debate = (
        db.query(DebateModel)
        .options(
            joinedload(DebateModel.document),
            joinedload(DebateModel.round_records),
            joinedload(DebateModel.messages),
            joinedload(DebateModel.research_sources)
        )
        .filter(DebateModel.id == debate_id)
        .first()
    )
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    return _format_debate_session(debate)

@router.get("/{debate_id}/status")
def get_debate_status(debate_id: str, db: Session = Depends(get_db)):
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    completed_rounds = len(debate.round_records) if debate.round_records else 0
    return {
        "debateId": debate.id,
        "status": debate.status,
        "currentRound": min(completed_rounds + 1, debate.rounds),
        "totalRounds": debate.rounds,
        "errorMessage": debate.error_message
    }

@router.get("/{debate_id}/messages", response_model=List[DebateTurnSchema])
def get_debate_messages(debate_id: str, db: Session = Depends(get_db)):
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    session = _format_debate_session(debate)
    all_turns = []
    for r in session.rounds:
        all_turns.extend(r.turns)
    return all_turns

@router.get("/{debate_id}/result")
def get_debate_result(debate_id: str, db: Session = Depends(get_db)):
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    if not debate.evaluation:
        raise HTTPException(status_code=400, detail="Evaluation not yet ready for this debate")
    return debate.evaluation.raw_payload or {
        "pro_score": debate.evaluation.pro_score,
        "con_score": debate.evaluation.con_score,
        "winner": debate.evaluation.winner,
        "judge_reasoning": debate.evaluation.judge_reasoning,
        "balanced_verdict": debate.evaluation.balanced_verdict
    }

@router.get("/{debate_id}/synthesis", response_model=DebateSynthesisSchema)
def get_debate_synthesis(debate_id: str, db: Session = Depends(get_db)):
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")
    if not debate.evaluation:
        raise HTTPException(status_code=400, detail="Synthesis not yet ready")
    ev = debate.evaluation
    raw = ev.raw_payload or {}
    is_fallback = raw.get("is_fallback", False) or ev.status == "failed"
    exec_status = raw.get("execution_status") or ("SIMULATED" if is_fallback else "REAL_REMOTE_API")
    raw_judge_used = raw.get("judge_model_used")
    provider_used = getattr(debate, "judge_provider", "gemini") or "gemini"
    if is_fallback:
        judge_used = raw_judge_used if (raw_judge_used and "gemini" not in raw_judge_used.lower() and "nvidia" not in raw_judge_used.lower()) else "Uncertified / Fallback"
    else:
        judge_used = raw_judge_used or debate.judge_model or ("nvidia/nemotron-3.5-super-vl-120b-a12b" if provider_used == "nvidia" else "gemini-3.5-flash")

    return DebateSynthesisSchema(
        summary=ev.judge_reasoning or "",
        keyConsensus=ev.pro_strengths or [],
        keyContentions=ev.con_strengths or [],
        evidenceReliabilityScore=float(ev.evidence_reliability_score) if ev.evidence_reliability_score is not None else 0.0,
        balancedVerdict=ev.balanced_verdict or "",
        judgeModelUsed=judge_used,
        judgeProvider=provider_used,
        isFallback=is_fallback,
        executionStatus=exec_status,
        proScore=float(ev.pro_score) if ev.pro_score is not None else None,
        conScore=float(ev.con_score) if ev.con_score is not None else None,
        winner=ev.winner,
        verdictType=raw.get("verdict_type"),
        proCriteriaScores=raw.get("pro_criteria_scores"),
        conCriteriaScores=raw.get("con_criteria_scores"),
        decisiveArguments=raw.get("decisive_arguments") or [],
        unsupportedClaims=raw.get("unsupported_claims") or [],
        citationAssessments=raw.get("citation_assessments") or [],
        confidence=raw.get("confidence", 85.0)
    )

@router.get("/{debate_id}/stream")
async def stream_debate(debate_id: str, db: Session = Depends(get_db)):
    """
    Server-Sent Events (SSE) streaming endpoint for live debate progress,
    delivering real-time token streams, active agent status, and phase transitions.
    """
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail="Debate not found")

    q = debate_stream_service.subscribe(debate_id)

    async def event_generator():
        try:
            # Send initial confirmation event
            yield debate_stream_service.format_sse("connected", {
                "debateId": debate_id,
                "status": debate.status,
                "topic": debate.topic
            })

            # If debate is already completed or failed, emit terminal state and exit
            if debate.status in ("completed", "failed"):
                yield debate_stream_service.format_sse(
                    "completed" if debate.status == "completed" else "failed",
                    {"status": debate.status, "message": f"Debate already {debate.status}"}
                )
                return

            while True:
                try:
                    # Read from pub-sub queue in a thread pool without blocking event loop
                    event = await asyncio.to_thread(q.get, timeout=20.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("completed", "failed", "cancelled"):
                        break
                except queue.Empty:
                    # Database status watchdog fallback: check if debate finished, failed, or cancelled in DB
                    with SessionLocal() as db_watch:
                        deb_check = db_watch.query(DebateModel).filter(DebateModel.id == debate_id).first()
                        if deb_check and deb_check.status in ("completed", "failed", "cancelled"):
                            yield debate_stream_service.format_sse(
                                deb_check.status,
                                {
                                    "status": deb_check.status,
                                    "error": deb_check.error_message,
                                    "message": f"Debate {deb_check.status}: {deb_check.error_message or ''}"
                                }
                            )
                            break
                    # Heartbeat comment to keep connection alive through proxies
                    yield ": ping\n\n"
        finally:
            debate_stream_service.unsubscribe(debate_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/{debate_id}/cancel")
def cancel_debate_by_id(debate_id: str, db: Session = Depends(get_db)):
    """
    Safely cancels an in-progress or queued debate and removes it from history.
    - Signals background LangGraph execution to stop safely.
    - Skips Judge evaluation.
    - Releases execution locks and removes debate from active registry.
    - Deletes the cancelled debate session and all debate-specific records from database in an atomic transaction.
    - Ensures cancelled debates are excluded from history, replay, and active recovery.
    """
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate with id '{debate_id}' not found")

    if debate.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel an already completed debate")

    # 1. Register cancellation signal for active background worker
    register_cancellation(debate_id)

    # 2. Publish cancelled event to SSE stream
    debate_stream_service.publish(debate_id, "cancelled", {
        "status": "cancelled",
        "message": "Debate execution cancelled by user request."
    })

    # 3. Remove from active running threads registry
    with _threads_lock:
        _running_threads.pop(debate_id, None)

    # 4. Atomic database cleanup of debate-specific records
    try:
        # Delete research sources specifically owned by this debate
        db.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id == debate_id).delete(synchronize_session=False)

        # Delete judge evaluations for this debate (if any)
        db.query(JudgeEvaluationModel).filter(JudgeEvaluationModel.debate_id == debate_id).delete(synchronize_session=False)

        # Delete debate messages
        db.query(DebateMessageModel).filter(DebateMessageModel.debate_id == debate_id).delete(synchronize_session=False)

        # Delete debate rounds
        db.query(DebateRoundModel).filter(DebateRoundModel.debate_id == debate_id).delete(synchronize_session=False)

        # Delete the debate record itself
        db.delete(debate)

        db.commit()
        logger.info(f"Debate '{debate_id}' cancelled and completely removed from database.")
    except Exception as ex:
        db.rollback()
        logger.error(f"Failed to clean up cancelled debate '{debate_id}' records: {ex}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clean up cancelled debate: {str(ex)}")

    return {
        "status": "cancelled",
        "debateId": debate_id,
        "message": f"Debate '{debate_id}' was safely stopped and deleted from history."
    }


@router.delete("/{debate_id}", response_model=DeleteResponse)
def delete_debate_by_id(debate_id: str, db: Session = Depends(get_db)):
    """
    Deletes a single debate and all its child rounds, messages, and evaluations.
    """
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate with id '{debate_id}' not found")

    db.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id == debate_id).delete(synchronize_session=False)
    db.delete(debate)
    db.commit()

    logger.info(f"Deleted debate '{debate_id}'.")
    return DeleteResponse(
        status="success",
        deletedId=debate_id,
        deletedCount=1,
        message=f"Debate '{debate_id}' successfully deleted."
    )

