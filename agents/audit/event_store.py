"""
Event Store
============
Event-sourced append-only audit trail for compliance-grade traceability.
"""

import uuid
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from threading import Lock

from agents.audit.event_types import AuditEvent, AuditEventType

logger = logging.getLogger(__name__)


class EventStore:
    """Append-only event store for agent audit trail."""

    _instance: Optional['EventStore'] = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._events: Dict[str, List[AuditEvent]] = {}  # session_id -> events
        self._initialized = True
        logger.info("Event Store initialized")

    def append(
        self,
        session_id: str,
        event_type: AuditEventType,
        agent_name: str = "",
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditEvent:
        """Append an event to the store."""
        event = AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            session_id=session_id,
            agent_name=agent_name,
            data=data or {},
            duration_ms=duration_ms,
            error=error,
            correlation_id=correlation_id,
        )

        with self._lock:
            if session_id not in self._events:
                self._events[session_id] = []
            self._events[session_id].append(event)

        logger.debug(f"Event appended: {event_type.value} for session {session_id}")
        return event

    def get_events(self, session_id: str) -> List[AuditEvent]:
        """Get all events for a session."""
        return self._events.get(session_id, [])

    def get_events_by_type(
        self, session_id: str, event_type: AuditEventType
    ) -> List[AuditEvent]:
        """Get events of a specific type for a session."""
        return [
            e for e in self._events.get(session_id, [])
            if e.event_type == event_type
        ]

    def get_latest_event(self, session_id: str) -> Optional[AuditEvent]:
        """Get the most recent event for a session."""
        events = self._events.get(session_id, [])
        return events[-1] if events else None

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of events for a session."""
        events = self._events.get(session_id, [])
        if not events:
            return {"session_id": session_id, "total_events": 0}

        event_counts = {}
        for e in events:
            event_counts[e.event_type.value] = event_counts.get(e.event_type.value, 0) + 1

        return {
            "session_id": session_id,
            "total_events": len(events),
            "event_counts": event_counts,
            "first_event": events[0].timestamp,
            "last_event": events[-1].timestamp,
            "has_errors": any(e.error for e in events),
        }

    def export_session(self, session_id: str) -> str:
        """Export all events for a session as JSON."""
        events = self._events.get(session_id, [])
        return json.dumps(
            [e.model_dump() for e in events],
            indent=2,
            default=str,
        )

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions with summaries."""
        sessions = []
        for session_id in list(self._events.keys())[-limit:]:
            sessions.append(self.get_session_summary(session_id))
        return sessions

    def clear_session(self, session_id: str):
        """Remove all events for a session."""
        self._events.pop(session_id, None)

    def reset(self):
        """Clear all events (for testing)."""
        with self._lock:
            self._events.clear()


_event_store: Optional[EventStore] = None


def get_event_store() -> EventStore:
    """Get the event store instance."""
    global _event_store
    if _event_store is None:
        _event_store = EventStore()
    return _event_store
