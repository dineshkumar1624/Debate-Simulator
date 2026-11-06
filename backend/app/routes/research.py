import logging
import json
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database.session import get_db, SessionLocal
from ..models.research import ResearchSourceModel
from ..services.research_service import research_service, research_cache
from ..schemas.research import (
    ResearchRequest,
    ResearchResponse,
    ResearchSourceSchema,
    ResearchEvidenceItem,
    ResearchStageSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["research"])

@router.post("", response_model=ResearchResponse)
def conduct_research(
    request: ResearchRequest,
    db: Session = Depends(get_db)
):
    if not request.topic or not request.topic.strip():
        raise HTTPException(
            status_code=400,
            detail="Research topic cannot be empty or whitespace-only."
        )
    try:
        result = research_service.conduct_research_and_index(
            db=db,
            topic=request.topic,
            max_sources=request.max_sources or 4,
            debate_id=request.debate_id
        )
        sources_schema = [
            ResearchSourceSchema(
                id=s["id"],
                title=s["title"],
                url=s["url"],
                snippet=s.get("content", "")[:240] + "..." if len(s.get("content", "")) > 240 else s.get("content", ""),
                publishedDate=s.get("published_date"),
                retrievalTimestamp=s.get("published_date") or ""
            )
            for s in result.get("sources", [])
        ]
        evidence_schema = [
            ResearchEvidenceItem(
                id=ev.get("id", ""),
                claim=ev.get("claim", ""),
                source=ev.get("source", ""),
                url=ev.get("url"),
                publishedDate=ev.get("publishedDate")
            )
            for ev in result.get("evidence_items", [])
        ]
        stages_schema = [
            ResearchStageSchema(
                id=st.get("id", ""),
                name=st.get("name", ""),
                status=st.get("status", "completed"),
                detail=st.get("detail")
            )
            for st in result.get("stages", [])
        ]
        default_message = (
            "Evidence collected, deduplicated, and indexed in Qdrant."
            if sources_schema
            else "Live research is unavailable or yielded no verified sources."
        )
        return ResearchResponse(
            topic=request.topic,
            query=result.get("queries", [""])[0] if result.get("queries") else "",
            sources=sources_schema,
            evidenceItems=evidence_schema,
            stages=stages_schema,
            indexedChunks=result.get("indexed_chunks", 0),
            status=result.get("status", "completed"),
            message=result.get("message", default_message)
        )
    except Exception as e:
        logger.error(f"Error during research execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def stream_research(
    topic: str = Query(..., description="Debate proposition to research"),
    max_sources: int = Query(4, description="Target number of verified sources"),
    debate_id: Optional[str] = Query(None, description="Optional debate ID association")
):
    """
    Real-time Server-Sent Events (SSE) streaming endpoint for web research pipeline.
    Delivers stage updates, progressive source discoveries, and final evidence payload.
    """
    clean_topic = topic.strip()
    if not clean_topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty or whitespace-only.")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_progress(event_type: str, status: str, detail: str, data: Optional[Dict[str, Any]] = None):
        payload = {
            "eventType": event_type,
            "status": status,
            "detail": detail,
            "data": data or {}
        }
        loop.call_soon_threadsafe(queue.put_nowait, (event_type, payload))

    def run_sync_research():
        with SessionLocal() as db_session:
            return research_service.conduct_research_and_index(
                db=db_session,
                topic=clean_topic,
                max_sources=max_sources,
                debate_id=debate_id,
                on_progress=on_progress
            )

    async def run_in_background():
        try:
            await asyncio.to_thread(run_sync_research)
        except Exception as e:
            logger.error(f"Streaming research worker error: {e}", exc_info=True)
            on_progress("error", "failed", str(e), {"error": str(e)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, ("_sentinel_done", {}))

    asyncio.create_task(run_in_background())

    async def event_generator():
        try:
            # Initial handshake
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'topic': clean_topic})}\n\n"
            while True:
                try:
                    event_type, payload = await asyncio.wait_for(queue.get(), timeout=25.0)
                    if event_type == "_sentinel_done":
                        break
                    yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
                    if event_type in ("complete", "error"):
                        break
                except asyncio.TimeoutError:
                    yield f": keep-alive\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/metrics")
def get_research_metrics():
    """
    Returns research caching efficiency and performance metrics.
    """
    return {
        "cacheHitRate": round(research_cache.hit_rate * 100, 2),
        "cachedTopicsCount": len(research_cache._topic_cache),
        "cachedArticlesCount": len(research_cache._article_cache),
        "totalHits": research_cache._hits,
        "totalMisses": research_cache._misses
    }


@router.get("/sources/{identifier}", response_model=List[ResearchSourceSchema])
def get_research_sources(
    identifier: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve saved research sources by debate_id or topic string.
    Read-only retrieval for history / replay / inspection.
    """
    sources = db.query(ResearchSourceModel).filter(
        (ResearchSourceModel.debate_id == identifier) | (ResearchSourceModel.topic == identifier)
    ).all()
    return [
        ResearchSourceSchema(
            id=s.id,
            title=s.title,
            url=s.url,
            snippet=s.content[:240] + "..." if len(s.content) > 240 else s.content,
            publishedDate=s.published_date,
            retrievalTimestamp=(s.retrieval_timestamp.isoformat() if getattr(s, "retrieval_timestamp", None) else "")
        )
        for s in sources
    ]
