import threading
import logging
from ..database.session import SessionLocal
from ..models.debate import DebateModel

logger = logging.getLogger(__name__)

_cancelled_debates = set()
_cancellation_lock = threading.Lock()

def register_cancellation(debate_id: str):
    with _cancellation_lock:
        _cancelled_debates.add(debate_id)
    logger.info(f"[CancellationService] Registered cancellation for debate {debate_id}")

def is_debate_cancelled(debate_id: str) -> bool:
    if not debate_id:
        return False
    with _cancellation_lock:
        if debate_id in _cancelled_debates:
            return True
    try:
        with SessionLocal() as db:
            deb = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
            if deb and deb.status == "cancelled":
                with _cancellation_lock:
                    _cancelled_debates.add(debate_id)
                return True
    except Exception:
        pass
    return False

def clear_cancellation(debate_id: str):
    with _cancellation_lock:
        _cancelled_debates.discard(debate_id)

