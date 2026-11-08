import sys
import os

# Ensure backend/.venv site-packages is in sys.path even when spawned by multiprocessing reloader
venv_site = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "Lib", "site-packages"))
if os.path.exists(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .database.session import engine, Base
from .routes.documents import router as documents_router
from .routes.debates import router as debates_router
from .routes.research import router as research_router
from .routes.history import router as history_router
from .services.qdrant_service import qdrant_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_debate_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure SQL tables exist
    logger.info("Initializing relational schema in configured database...")
    Base.metadata.create_all(bind=engine)
    # Ensure Qdrant collection exists
    logger.info("Ensuring Qdrant vector database collection...")
    try:
        qdrant_service._ensure_collection()
    except Exception as e:
        logger.warning(f"Qdrant collection verification warning: {e}")
    
    # Startup inference device reporting
    from .llm.model_manager import local_model_manager
    logger.info(
        f"Inference device initialized: configured='{settings.INFERENCE_DEVICE}', "
        f"effective='{local_model_manager.device}', cuda_available={local_model_manager._has_cuda()}"
    )

    # Pre-warm embedding service in background thread to eliminate first-request latency
    import threading
    from .services.embedding_service import embedding_service
    def _warmup_embeddings():
        try:
            logger.info("Pre-warming SentenceTransformer embedding model in background...")
            embedding_service._ensure_model()
            logger.info("SentenceTransformer embedding model pre-warmed successfully.")
        except Exception as ex:
            logger.warning(f"Embedding model pre-warming warning: {ex}")
    threading.Thread(target=_warmup_embeddings, daemon=True, name="embedding-warmer").start()

    # Ensure performance_metrics column exists on debates table
    from sqlalchemy import inspect, text
    try:
        with engine.connect() as conn:
            insp = inspect(engine)
            cols = [c["name"] for c in insp.get_columns("debates")]
            if "performance_metrics" not in cols:
                conn.execute(text("ALTER TABLE debates ADD COLUMN performance_metrics JSON"))
                conn.commit()
                logger.info("Migrated debates table: added performance_metrics column.")
    except Exception as e:
        logger.warning(f"Schema reconciliation check for performance_metrics: {e}")

    # Startup reconciliation: reconcile any stale debates interrupted by past server shutdowns
    from .database.session import SessionLocal
    from .models.debate import DebateModel
    from datetime import datetime, timedelta
    try:
        with SessionLocal() as db_init:
            stale_cutoff = datetime.utcnow() - timedelta(hours=2)
            reconciled = db_init.query(DebateModel).filter(
                DebateModel.status.in_(["debating", "running", "evaluating", "queued"]),
                DebateModel.created_at < stale_cutoff
            ).update({"status": "failed", "error_message": "Execution interrupted by server restart"}, synchronize_session=False)
            db_init.commit()
            if reconciled > 0:
                logger.info(f"Reconciled {reconciled} stale active debates on server startup.")
    except Exception as e:
        logger.warning(f"Startup reconciliation warning: {e}")

    yield
    # Shutdown
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Multi-agent dialectical debate simulator backend orchestrated via LangGraph StateGraph, Qdrant RAG, and PostgreSQL/SQLAlchemy persistence.",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers under /api
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(debates_router, prefix=settings.API_V1_STR)
app.include_router(research_router, prefix=settings.API_V1_STR)
app.include_router(history_router, prefix=settings.API_V1_STR)

# Direct root aliases for client flexibility
app.include_router(documents_router)
app.include_router(debates_router)
app.include_router(research_router)
app.include_router(history_router)

@app.get("/health", tags=["system"])
@app.get(f"{settings.API_V1_STR}/health", tags=["system"])
def health_check():
    from .llm.model_manager import local_model_manager
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "database": "connected",
        "qdrant": "available" if qdrant_service.client is not None else "degraded",
        "device": local_model_manager.device
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
