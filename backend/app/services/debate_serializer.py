import uuid
from typing import List, Dict, Any, Optional
from ..models.debate import DebateModel, DebateRoundModel, DebateMessageModel, JudgeEvaluationModel
from ..schemas.debate import (
    DebateSessionSchema,
    DebateConfigSchema,
    DebateRoundSchema,
    DebateTurnSchema,
    DebateSynthesisSchema,
    EvidenceItemSchema,
)

def _ensure_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return []


def _ensure_dict(val):
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            while isinstance(parsed, str):
                parsed = json.loads(parsed)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def format_debate_session(debate: DebateModel) -> DebateSessionSchema:
    """
    Pure data formatting function that maps SQLAlchemy DebateModel to DebateSessionSchema.
    Does NOT invoke any LLM, LangGraph, or vector database.
    """
    doc_name = debate.document.name if debate.document else None
    doc_type = debate.document.file_type if debate.document else None

    provider_used = getattr(debate, "judge_provider", "nvidia") or "nvidia"
    default_judge = "nvidia/nemotron-3.5-super-vl-120b-a12b" if provider_used == "nvidia" else "gemini-3.5-flash"

    config = DebateConfigSchema(
        topic=debate.topic,
        debaterAModel=debate.debater_a_model or "gemma-4-E4B-Q4_0",
        debaterBModel=debate.debater_b_model or "Qwen2.5-VL-7B-Instruct",
        judgeModel=debate.judge_model or default_judge,
        judgeProvider=provider_used,
        rounds=debate.rounds or 3,
        evidenceMode=debate.evidence_mode if debate.evidence_mode is not None else True,
        strictFactChecking=debate.strict_fact_checking if debate.strict_fact_checking is not None else True,
        documentId=debate.document_id,
        documentName=doc_name,
        documentType=doc_type,
        sourceScope=debate.source_scope or "document"
    )

    # Deterministically order messages: round_number ascending, PRO before CON
    sorted_messages = sorted(
        debate.messages or [],
        key=lambda m: (m.round_number, 0 if m.role == "PRO" else 1)
    )

    # Group messages into rounds
    rounds_map: Dict[int, List[DebateTurnSchema]] = {}
    for msg in sorted_messages:
        r_num = msg.round_number
        if r_num not in rounds_map:
            rounds_map[r_num] = []

        evidence_items = []
        exec_status = "SIMULATED"
        ev_refs = _ensure_list(msg.evidence_references)
        for ev in ev_refs:
            if isinstance(ev, dict):
                if ev.get("__meta__") and ev.get("execution_status"):
                    exec_status = ev.get("execution_status")
                    continue
                evidence_items.append(EvidenceItemSchema(
                    id=str(ev.get("id") or ev.get("chunk_id") or uuid.uuid4()),
                    claim=ev.get("claim") or ev.get("relevance_explanation") or "",
                    source=ev.get("source", "Document"),
                    url=ev.get("url"),
                    verdict=ev.get("verdict", "supported"),
                    confidenceScore=float(ev.get("confidenceScore") or ev.get("relevance_score") or 90.0),
                    page=ev.get("page") or ev.get("page_number"),
                    section=ev.get("section") or ev.get("section_title"),
                    content=ev.get("content") or ev.get("excerpt"),
                    relevanceScore=float(ev.get("relevanceScore") or ev.get("relevance_score") or ev.get("confidenceScore") or 90.0),
                    relevanceExplanation=ev.get("relevance_explanation") or ev.get("claim")
                ))

        if exec_status not in ("REAL_LOCAL_MODEL", "REAL_REMOTE_API", "SIMULATED"):
            if "LOCAL" in str(exec_status).upper():
                exec_status = "REAL_LOCAL_MODEL"
            elif "REMOTE" in str(exec_status).upper() or "API" in str(exec_status).upper():
                exec_status = "REAL_REMOTE_API"
            else:
                exec_status = "SIMULATED"

        rounds_map[r_num].append(DebateTurnSchema(
            speaker="DEBATER_A" if msg.role == "PRO" else "DEBATER_B",
            role=msg.role if msg.role in ["PRO", "CON"] else "PRO",
            content=msg.content,
            timestamp=msg.created_at.strftime("%I:%M:%S %p") if msg.created_at else "Now",
            title=msg.title,
            confidence=msg.confidence,
            evidence=evidence_items,
            executionStatus=exec_status
        ))

    round_schemas = [
        DebateRoundSchema(
            roundNumber=r,
            turns=sorted(rounds_map[r], key=lambda t: 0 if t.role == "PRO" else 1)
        )
        for r in sorted(rounds_map.keys())
    ]

    synthesis = None
    if debate.evaluation:
        ev = debate.evaluation
        raw = _ensure_dict(ev.raw_payload)
        is_fallback = raw.get("is_fallback", False) or ev.status == "failed"
        raw_exec = raw.get("execution_status")
        if is_fallback:
            exec_status = "SIMULATED"
        elif raw_exec in ("REAL_LOCAL_MODEL", "REAL_REMOTE_API", "SIMULATED"):
            exec_status = raw_exec
        elif raw_exec and "LOCAL" in str(raw_exec).upper():
            exec_status = "REAL_LOCAL_MODEL"
        elif raw_exec and ("REMOTE" in str(raw_exec).upper() or "API" in str(raw_exec).upper()):
            exec_status = "REAL_REMOTE_API"
        else:
            exec_status = "REAL_REMOTE_API"
        raw_judge_used = raw.get("judge_model_used")
        if is_fallback:
            judge_used = raw_judge_used if (raw_judge_used and "gemini" not in raw_judge_used.lower() and "nvidia" not in raw_judge_used.lower()) else "Uncertified / Fallback"
        else:
            judge_used = raw_judge_used or debate.judge_model or default_judge

        synthesis = DebateSynthesisSchema(
            summary=ev.judge_reasoning or "",
            keyConsensus=_ensure_list(ev.pro_strengths),
            keyContentions=_ensure_list(ev.con_strengths),
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
            decisiveArguments=_ensure_list(raw.get("decisive_arguments")),
            unsupportedClaims=_ensure_list(raw.get("unsupported_claims")),
            citationAssessments=_ensure_list(raw.get("citation_assessments")),
            confidence=raw.get("confidence", 85.0)
        )

    completed_at = None
    completed_at_epoch_ms = None
    completed_at_iso = None
    if debate.status in ("completed", "failed", "evaluation_failed", "cancelled") and debate.updated_at:
        completed_at = debate.updated_at.strftime("%b %d, %Y %I:%M %p")
        from datetime import timezone
        dt_comp_utc = debate.updated_at.replace(tzinfo=timezone.utc) if debate.updated_at.tzinfo is None else debate.updated_at
        completed_at_epoch_ms = int(dt_comp_utc.timestamp() * 1000)
        completed_at_iso = dt_comp_utc.isoformat()

    started_at_epoch_ms = None
    started_at_iso = None
    if debate.created_at:
        from datetime import timezone
        dt_utc = debate.created_at.replace(tzinfo=timezone.utc) if debate.created_at.tzinfo is None else debate.created_at
        started_at_epoch_ms = int(dt_utc.timestamp() * 1000)
        started_at_iso = dt_utc.isoformat()

    elapsed_seconds = 0
    if started_at_epoch_ms is not None:
        if completed_at_epoch_ms is not None:
            elapsed_seconds = max(0, int((completed_at_epoch_ms - started_at_epoch_ms) / 1000))
        else:
            import datetime
            from datetime import timezone
            now_ms = int(datetime.datetime.now(timezone.utc).timestamp() * 1000)
            elapsed_seconds = max(0, int((now_ms - started_at_epoch_ms) / 1000))

    res_sources = []
    if hasattr(debate, "research_sources") and debate.research_sources:
        for s in debate.research_sources:
            res_sources.append({
                "id": s.id,
                "title": s.title,
                "url": s.url,
                "snippet": s.content[:240] + "..." if len(s.content) > 240 else s.content,
                "publishedDate": s.published_date,
                "retrievalTimestamp": s.retrieval_timestamp.isoformat() if s.retrieval_timestamp else ""
            })

    return DebateSessionSchema(
        id=debate.id,
        topic=debate.topic,
        createdAt=debate.created_at.strftime("%b %d, %Y %I:%M %p") if debate.created_at else "Today",
        startedAtEpochMs=started_at_epoch_ms,
        completedAtEpochMs=completed_at_epoch_ms,
        startedAtIso=started_at_iso,
        elapsedSeconds=elapsed_seconds,
        completedAt=completed_at,
        status=debate.status or "idle",
        config=config,
        rounds=round_schemas,
        synthesis=synthesis,
        errorMessage=debate.error_message,
        documentName=doc_name,
        documentType=doc_type,
        researchSources=res_sources if res_sources else None
    )

