import re
import logging
from collections import OrderedDict
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, and_

from ..database.session import get_db
from ..models.debate import DebateModel, DebateRoundModel, DebateMessageModel, JudgeEvaluationModel
from ..models.document import DocumentModel
from ..models.research import ResearchSourceModel
from ..schemas.debate import (
    DebateSessionSchema,
    DebateAttemptSchema,
    GroupedDebateHistoryItemSchema,
    DebateHistoryResponse,
    DeleteGroupRequest,
    DeleteResponse,
    ShowcaseArgumentSchema,
    ShowcaseDebateSchema,
    ShowcaseResponse,
)
from datetime import datetime
from ..services.debate_serializer import format_debate_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["history"])


def normalize_proposition(text: str) -> str:
    """
    Normalizes debate topic / proposition string for intelligent grouping:
    - Strips leading/trailing whitespace
    - Strips outer quotation marks (double, single, smart quotes, guillemets)
    - Collapses multiple whitespace characters into a single space
    - Converts to lowercase for key comparison
    """
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r'^[«»"\'“‘’”]+|[«»"\'“‘’”]+$', '', t).strip()
    t = re.sub(r'\s+', ' ', t).lower()
    return t


@router.get("", response_model=DebateHistoryResponse)
def get_debate_history(
    query: Optional[str] = Query(None, description="Search proposition or source document name"),
    status: Optional[str] = Query(None, description="Filter by status (strictly completed debates only)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(15, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Retrieves SMART GROUPED debate history for COMPLETED debates only.
    Strictly filters out all ongoing, debating, pending, and failed debates,
    as well as debates with missing, failed, or incomplete judge evaluations.
    
    Groups identical questions asked against the same document into a single card
    with expandable chronological attempts.
    
    Zero LLM calls, zero model loading, zero LangGraph operations.
    """
    # Strictly completed debates only:
    # Filter out all ongoing, debating, pending, failed, and cancelled debates.
    if status and status.strip().lower() not in ("completed", "all", ""):
        return DebateHistoryResponse(
            groups=[],
            items=[],
            totalGroups=0,
            totalCompletedDebates=0,
            total=0,
            page=page,
            pageSize=page_size,
            totalPages=1
        )

    base_query = (
        db.query(DebateModel)
        .outerjoin(JudgeEvaluationModel, DebateModel.id == JudgeEvaluationModel.debate_id)
        .outerjoin(DocumentModel, DebateModel.document_id == DocumentModel.id)
        .filter(
            DebateModel.status == "completed",
            JudgeEvaluationModel.status.in_(["completed", "success"]),
            JudgeEvaluationModel.winner != "FAILED"
        )
    )

    if query and query.strip():
        cleaned_term = query.strip()
        # Strip outer quotes and normalize whitespace so searches match regardless of formatting
        cleaned_term = re.sub(r'^[«»"\'“‘’”]+|[«»"\'“‘’”]+$', '', cleaned_term).strip()
        if cleaned_term:
            term = f"%{cleaned_term}%"
            base_query = base_query.filter(
                or_(
                    DebateModel.topic.ilike(term),
                    DocumentModel.name.ilike(term)
                )
            )

    # Fetch all completed records ordered by newest first
    debates = (
        base_query
        .options(
            joinedload(DebateModel.document),
            joinedload(DebateModel.evaluation),
            joinedload(DebateModel.round_records),
            joinedload(DebateModel.messages)
        )
        .order_by(desc(DebateModel.created_at))
        .all()
    )

    # Group completed debates by (normalized_proposition, document_id)
    groups_dict: OrderedDict[str, List[DebateModel]] = OrderedDict()
    for d in debates:
        norm_topic = normalize_proposition(d.topic)
        doc_id = str(d.document_id) if d.document_id else "general"
        group_key = f"{norm_topic}::{doc_id}"

        if group_key not in groups_dict:
            groups_dict[group_key] = []
        groups_dict[group_key].append(d)

    # Transform groups into GroupedDebateHistoryItemSchema
    grouped_items: List[GroupedDebateHistoryItemSchema] = []
    for group_key, records in groups_dict.items():
        latest = records[0]
        doc_name = latest.document.name if latest.document else None
        ev = latest.evaluation
        latest_winner = ev.winner if ev else None
        latest_pro_score = float(ev.pro_score) if (ev and ev.pro_score is not None) else None
        latest_con_score = float(ev.con_score) if (ev and ev.con_score is not None) else None

        latest_completed_at = None
        if latest.updated_at:
            latest_completed_at = latest.updated_at.strftime("%b %d, %Y %I:%M %p")
        elif latest.created_at:
            latest_completed_at = latest.created_at.strftime("%b %d, %Y %I:%M %p")

        # Build chronological attempts (Attempt #1 is earliest, Attempt #N is latest)
        attempts: List[DebateAttemptSchema] = []
        total_in_group = len(records)
        for idx, rec in enumerate(records):
            attempt_num = total_in_group - idx
            rec_ev = rec.evaluation
            att_completed_at = None
            if rec.updated_at:
                att_completed_at = rec.updated_at.strftime("%b %d, %Y %I:%M %p")
            elif rec.created_at:
                att_completed_at = rec.created_at.strftime("%b %d, %Y %I:%M %p")

            rec_status = rec.status or "completed"
            attempts.append(DebateAttemptSchema(
                attemptNumber=attempt_num,
                debateId=rec.id,
                status=rec_status,
                createdAt=rec.created_at.strftime("%b %d, %Y %I:%M %p") if rec.created_at else "Today",
                completedAt=att_completed_at,
                winner=rec_ev.winner if rec_ev else ("CANCELLED" if rec_status == "cancelled" else None),
                proScore=float(rec_ev.pro_score) if (rec_ev and rec_ev.pro_score is not None) else None,
                conScore=float(rec_ev.con_score) if (rec_ev and rec_ev.con_score is not None) else None,
                roundsCount=len(rec.round_records) if rec.round_records else (rec.rounds or 3),
                speechesCount=len(rec.messages) if rec.messages else 0,
                judgeModel=rec.judge_model,
                judgeProvider=getattr(rec, "judge_provider", "gemini"),
                sourceScope=rec.source_scope or ("document" if rec.document_id else "general_topic")
            ))

        latest_rounds = len(latest.round_records) if latest.round_records else (latest.rounds or 3)
        grouped_items.append(GroupedDebateHistoryItemSchema(
            groupKey=group_key,
            topic=latest.topic,
            id=latest.id,
            status=latest.status or "completed",
            createdAt=latest.created_at.strftime("%b %d, %Y %I:%M %p") if latest.created_at else "Today",
            documentId=latest.document_id,
            documentName=doc_name,
            sourceScope=latest.source_scope or ("document" if latest.document_id else "general_topic"),
            totalAttempts=total_in_group,
            latestCompletedAt=latest_completed_at,
            latestWinner=latest_winner,
            winner=latest_winner,
            latestProScore=latest_pro_score,
            latestConScore=latest_con_score,
            latestRoundsCount=latest_rounds,
            roundsCount=latest_rounds,
            latestSpeechesCount=len(latest.messages) if latest.messages else 0,
            attempts=attempts
        ))

    # Server-side pagination across grouped cards
    total_groups = len(grouped_items)
    total_completed_debates = len(debates)
    total_pages = max(1, (total_groups + page_size - 1) // page_size) if total_groups > 0 else 1
    offset = (page - 1) * page_size
    paged_groups = grouped_items[offset : offset + page_size]

    return DebateHistoryResponse(
        groups=paged_groups,
        items=paged_groups,
        totalGroups=total_groups,
        totalCompletedDebates=total_completed_debates,
        total=total_groups,
        page=page,
        pageSize=page_size,
        totalPages=total_pages
    )


@router.delete("/group", response_model=DeleteResponse)
@router.delete("/batch", response_model=DeleteResponse)
@router.post("/batch-delete", response_model=DeleteResponse)
def delete_debate_group(payload: DeleteGroupRequest, db: Session = Depends(get_db)):
    """
    Deletes an entire debate topic group or batch of debates (e.g. all on a page).
    Cascades and cleanly removes all debate rounds, messages, and judicial evaluations.
    """
    target_ids = list(payload.debateIds or [])

    if not target_ids and payload.topic:
        norm_target = normalize_proposition(payload.topic)
        all_debates = db.query(DebateModel).all()
        for d in all_debates:
            if normalize_proposition(d.topic) == norm_target:
                if payload.documentId is not None:
                    if str(d.document_id) == str(payload.documentId):
                        target_ids.append(d.id)
                else:
                    if d.document_id is None:
                        target_ids.append(d.id)

    if not target_ids:
        raise HTTPException(
            status_code=400,
            detail="No matching debates or debate IDs specified for topic group deletion."
        )

    debates_to_delete = db.query(DebateModel).filter(DebateModel.id.in_(target_ids)).all()
    count = len(debates_to_delete)
    db.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id.in_(target_ids)).delete(synchronize_session=False)
    for d in debates_to_delete:
        db.delete(d)
    db.commit()

    logger.info(f"Deleted {count} debates for topic group.")
    return DeleteResponse(
        status="success",
        deletedCount=count,
        message=f"Successfully deleted {count} debates for this topic."
    )


@router.delete("/{debate_id}", response_model=DeleteResponse)
def delete_debate_attempt(debate_id: str, db: Session = Depends(get_db)):
    """
    Deletes a single debate attempt by ID.
    Cascades and cleanly removes all debate rounds, messages, and judicial evaluations.
    """
    debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate with id '{debate_id}' not found")

    db.query(ResearchSourceModel).filter(ResearchSourceModel.debate_id == debate_id).delete(synchronize_session=False)
    db.delete(debate)
    db.commit()

    logger.info(f"Deleted debate attempt '{debate_id}'.")
    return DeleteResponse(
        status="success",
        deletedId=debate_id,
        deletedCount=1,
        message=f"Debate attempt '{debate_id}' successfully deleted."
    )


def _extract_evidence_citation(ev_list) -> tuple:
    """Helper to extract evidence text and page citation from evidence_references JSON."""
    if not ev_list or not isinstance(ev_list, list):
        return None, None
    for ev in ev_list:
        if not isinstance(ev, dict) or ev.get("__meta__"):
            continue
        page = ev.get("page") or ev.get("page_number")
        page_str = f"Page {page}" if page else None
        title = ev.get("source_title") or ev.get("document_name") or ev.get("chunk_id")
        text = ev.get("text") or ev.get("content") or ""
        evidence_str = title or (text[:90] + "..." if len(text) > 90 else text)
        if evidence_str or page_str:
            return evidence_str, page_str
    return None, None


@router.get("/showcase", response_model=ShowcaseResponse)
def get_showcase_debates(
    limit: int = Query(8, ge=1, le=20, description="Maximum showcase debates to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the latest genuine completed debates for the homepage showcase.
    Strictly read-only: zero LLM calls, zero model loading, zero LangGraph operations.
    Only includes debates with persisted PRO and CON speeches and a valid Judge evaluation.
    """
    candidates = (
        db.query(DebateModel)
        .join(JudgeEvaluationModel, DebateModel.id == JudgeEvaluationModel.debate_id)
        .outerjoin(DocumentModel, DebateModel.document_id == DocumentModel.id)
        .options(
            joinedload(DebateModel.document),
            joinedload(DebateModel.messages),
            joinedload(DebateModel.evaluation)
        )
        .filter(
            DebateModel.status == "completed",
            JudgeEvaluationModel.status.in_(["completed", "success"]),
            JudgeEvaluationModel.winner != "FAILED"
        )
        .order_by(desc(DebateModel.created_at))
        .all()
    )

    seen_topics = set()
    showcase_debates: List[ShowcaseDebateSchema] = []

    for deb in candidates:
        if not deb.messages or len(deb.messages) < 2:
            continue
        if not deb.evaluation:
            continue

        pro_msgs = [m for m in deb.messages if (m.role or "").upper() == "PRO" or (m.speaker or "").upper() in ("DEBATER_A", "PRO")]
        con_msgs = [m for m in deb.messages if (m.role or "").upper() == "CON" or (m.speaker or "").upper() in ("DEBATER_B", "CON")]

        if not pro_msgs or not con_msgs:
            continue

        norm_topic = normalize_proposition(deb.topic)
        doc_key = str(deb.document_id) if deb.document_id else "general"
        topic_doc_key = f"{norm_topic}::{doc_key}"

        # Prefer diverse topics for carousel rotation
        if topic_doc_key in seen_topics and len(showcase_debates) < limit:
            continue
        seen_topics.add(topic_doc_key)

        pro_args: List[ShowcaseArgumentSchema] = []
        for m in sorted(pro_msgs, key=lambda x: (x.round_number, x.created_at or datetime.min)):
            ev_str, page_str = _extract_evidence_citation(m.evidence_references)
            pro_args.append(ShowcaseArgumentSchema(
                speaker="PRO",
                roundNumber=m.round_number,
                roundLabel=f"ROUND {m.round_number:02d} • PRO (AFFIRMATIVE)",
                title=m.title or "Affirmative Argument",
                content=m.content,
                evidence=ev_str or (deb.document.name if deb.document else "Grounded Evidentiary Baseline"),
                pageCitation=page_str,
                confidence=m.confidence
            ))

        con_args: List[ShowcaseArgumentSchema] = []
        for m in sorted(con_msgs, key=lambda x: (x.round_number, x.created_at or datetime.min)):
            ev_str, page_str = _extract_evidence_citation(m.evidence_references)
            con_args.append(ShowcaseArgumentSchema(
                speaker="CON",
                roundNumber=m.round_number,
                roundLabel=f"ROUND {m.round_number:02d} • CON (CHALLENGING)",
                title=m.title or "Counter-Argument & Critique",
                content=m.content,
                evidence=ev_str or (deb.document.name if deb.document else "Dialectical Counter-Analysis"),
                pageCitation=page_str,
                confidence=m.confidence
            ))

        created_str = deb.created_at.strftime("%b %d, %Y") if deb.created_at else ""

        showcase_debates.append(ShowcaseDebateSchema(
            id=deb.id,
            topic=deb.topic,
            createdAt=created_str,
            documentName=deb.document.name if deb.document else None,
            documentId=deb.document_id,
            isReal=True,
            roundsCount=deb.rounds or 1,
            proArguments=pro_args,
            conArguments=con_args,
            judgeWinner=deb.evaluation.winner,
            judgeProScore=deb.evaluation.pro_score,
            judgeConScore=deb.evaluation.con_score,
            judgeReasoning=deb.evaluation.judge_reasoning,
            judgeVerdict=deb.evaluation.balanced_verdict,
            judgeModel=deb.judge_model,
            judgeProvider=getattr(deb, "judge_provider", None) or "gemini"
        ))

        if len(showcase_debates) >= limit:
            break

    # If we didn't fill limit with unique topics, allow repeated topics from newest candidates
    if len(showcase_debates) < limit:
        existing_ids = {d.id for d in showcase_debates}
        for deb in candidates:
            if deb.id in existing_ids:
                continue
            if not deb.messages or len(deb.messages) < 2 or not deb.evaluation:
                continue
            pro_msgs = [m for m in deb.messages if (m.role or "").upper() == "PRO" or (m.speaker or "").upper() in ("DEBATER_A", "PRO")]
            con_msgs = [m for m in deb.messages if (m.role or "").upper() == "CON" or (m.speaker or "").upper() in ("DEBATER_B", "CON")]
            if not pro_msgs or not con_msgs:
                continue

            pro_args = []
            for m in sorted(pro_msgs, key=lambda x: (x.round_number, x.created_at or datetime.min)):
                ev_str, page_str = _extract_evidence_citation(m.evidence_references)
                pro_args.append(ShowcaseArgumentSchema(
                    speaker="PRO",
                    roundNumber=m.round_number,
                    roundLabel=f"ROUND {m.round_number:02d} • PRO",
                    title=m.title or "Affirmative Argument",
                    content=m.content,
                    evidence=ev_str or (deb.document.name if deb.document else "Grounded Evidentiary Baseline"),
                    pageCitation=page_str,
                    confidence=m.confidence
                ))

            con_args = []
            for m in sorted(con_msgs, key=lambda x: (x.round_number, x.created_at or datetime.min)):
                ev_str, page_str = _extract_evidence_citation(m.evidence_references)
                con_args.append(ShowcaseArgumentSchema(
                    speaker="CON",
                    roundNumber=m.round_number,
                    roundLabel=f"ROUND {m.round_number:02d} • CON",
                    title=m.title or "Counter-Argument",
                    content=m.content,
                    evidence=ev_str or (deb.document.name if deb.document else "Dialectical Counter-Analysis"),
                    pageCitation=page_str,
                    confidence=m.confidence
                ))

            created_str = deb.created_at.strftime("%b %d, %Y") if deb.created_at else ""

            showcase_debates.append(ShowcaseDebateSchema(
                id=deb.id,
                topic=deb.topic,
                createdAt=created_str,
                documentName=deb.document.name if deb.document else None,
                documentId=deb.document_id,
                isReal=True,
                roundsCount=deb.rounds or 1,
                proArguments=pro_args,
                conArguments=con_args,
                judgeWinner=deb.evaluation.winner,
                judgeProScore=deb.evaluation.pro_score,
                judgeConScore=deb.evaluation.con_score,
                judgeReasoning=deb.evaluation.judge_reasoning,
                judgeVerdict=deb.evaluation.balanced_verdict,
                judgeModel=deb.judge_model,
                judgeProvider=getattr(deb, "judge_provider", None) or "gemini"
            ))

            if len(showcase_debates) >= limit:
                break

    return ShowcaseResponse(
        debates=showcase_debates,
        totalAvailable=len(candidates)
    )


@router.get("/{debate_id}", response_model=DebateSessionSchema)
def get_debate_by_id(debate_id: str, db: Session = Depends(get_db)):
    """
    Retrieves one exact historical debate with complete rounds, all speeches,
    grounded evidence references, citations, and judicial evaluation.
    Strictly read-only: returns 404 if debate does not exist, performs zero LLM calls.
    """
    debate = (
        db.query(DebateModel)
        .options(
            joinedload(DebateModel.document),
            joinedload(DebateModel.round_records),
            joinedload(DebateModel.messages),
            joinedload(DebateModel.evaluation)
        )
        .filter(DebateModel.id == debate_id)
        .first()
    )

    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate with id '{debate_id}' not found")

    return format_debate_session(debate)

