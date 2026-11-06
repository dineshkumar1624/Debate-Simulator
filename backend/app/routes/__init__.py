from .documents import router as documents_router
from .debates import router as debates_router
from .research import router as research_router
from .history import router as history_router

__all__ = ["documents_router", "debates_router", "research_router", "history_router"]
