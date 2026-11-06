import json
import logging
import queue
from typing import Dict, Set, Any

logger = logging.getLogger(__name__)

class DebateStreamService:
    """
    In-memory pub-sub streaming bus connecting background LangGraph debate execution
    to frontend Server-Sent Events (SSE) endpoints.
    Allows real-time streaming of generated tokens, phase updates, and active debater telemetry.
    """
    def __init__(self):
        self._listeners: Dict[str, Set[queue.Queue]] = {}
        self._event_history: Dict[str, List[Dict[str, Any]]] = {}

    def subscribe(self, debate_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=1000)
        if debate_id not in self._listeners:
            self._listeners[debate_id] = set()
        self._listeners[debate_id].add(q)

        # Replay milestone events to late-joining subscribers
        if debate_id in self._event_history:
            for past_event in self._event_history[debate_id]:
                try:
                    q.put_nowait(past_event)
                except queue.Full:
                    break

        logger.debug(f"[StreamService] Client subscribed to debate {debate_id}")
        return q

    def unsubscribe(self, debate_id: str, q: queue.Queue):
        if debate_id in self._listeners:
            self._listeners[debate_id].discard(q)
            if not self._listeners[debate_id]:
                del self._listeners[debate_id]
            logger.debug(f"[StreamService] Client unsubscribed from debate {debate_id}")

    def publish(self, debate_id: str, event_type: str, data: Dict[str, Any]):
        payload = {"type": event_type, **data}
        # Buffer non-token milestone events for subscriber replay
        if event_type != "token":
            if debate_id not in self._event_history:
                self._event_history[debate_id] = []
            self._event_history[debate_id].append(payload)
            if len(self._event_history[debate_id]) > 200:
                self._event_history[debate_id] = self._event_history[debate_id][-100:]

        if debate_id in self._listeners:
            dead = set()
            for q in list(self._listeners[debate_id]):
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.add(q)
            for q in dead:
                self._listeners[debate_id].discard(q)

    def format_sse(self, event_type: str, data: Dict[str, Any]) -> str:
        payload = {"type": event_type, **data}
        return f"data: {json.dumps(payload)}\n\n"

debate_stream_service = DebateStreamService()

