"""
SSE Manager
============
Server-Sent Events connection manager using asyncio queues.
One queue per session for real-time agent progress streaming.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, AsyncGenerator

from config.settings import settings
from models.agent_models import AgentEvent, AgentEventType

logger = logging.getLogger(__name__)


class SSEManager:
    """Manages SSE connections and event distribution per session."""

    _instance: Optional['SSEManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._queues: Dict[str, list[asyncio.Queue]] = {}
        self._last_activity: Dict[str, float] = {}
        self._initialized = True
        logger.info("SSE Manager initialized")

    def subscribe(self, session_id: str) -> asyncio.Queue:
        """Create a new subscription queue for a session."""
        if session_id not in self._queues:
            self._queues[session_id] = []

        if len(self._queues[session_id]) >= settings.sse.max_connections_per_session:
            oldest = self._queues[session_id].pop(0)
            oldest.put_nowait(None)  # Signal disconnect

        queue: asyncio.Queue = asyncio.Queue(maxsize=settings.sse.event_queue_size)
        self._queues[session_id].append(queue)
        self._last_activity[session_id] = time.time()
        logger.info(f"SSE subscription created for session {session_id}")
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """Remove a subscription queue."""
        if session_id in self._queues:
            try:
                self._queues[session_id].remove(queue)
            except ValueError:
                pass
            if not self._queues[session_id]:
                del self._queues[session_id]
                self._last_activity.pop(session_id, None)
        logger.info(f"SSE subscription removed for session {session_id}")

    async def publish(self, session_id: str, event: AgentEvent):
        """Publish an event to all subscribers for a session."""
        if session_id not in self._queues:
            return

        self._last_activity[session_id] = time.time()
        dead_queues = []

        for queue in self._queues[session_id]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        for dq in dead_queues:
            try:
                self._queues[session_id].remove(dq)
            except ValueError:
                pass

    def publish_sync(self, session_id: str, event: AgentEvent):
        """Synchronous publish for use in non-async agent code.

        Uses direct put_nowait on queues (thread-safe) instead of
        going through the async publish method, which avoids event
        loop issues when called from worker threads.
        """
        if session_id not in self._queues:
            return

        self._last_activity[session_id] = time.time()
        for queue in list(self._queues.get(session_id, [])):
            try:
                queue.put_nowait(event)
            except (asyncio.QueueFull, Exception):
                pass

    async def event_stream(self, session_id: str) -> AsyncGenerator[str, None]:
        """Generate SSE event stream for a session."""
        queue = self.subscribe(session_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=settings.sse.heartbeat_interval_seconds
                    )
                    if event is None:
                        break
                    yield self._format_sse(event)
                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat = AgentEvent(
                        event_type=AgentEventType.HEARTBEAT,
                        session_id=session_id,
                        message="keepalive",
                    )
                    yield self._format_sse(heartbeat)
        finally:
            self.unsubscribe(session_id, queue)

    def _format_sse(self, event: AgentEvent) -> str:
        """Format an AgentEvent as an SSE message."""
        data = event.model_dump()
        return f"event: {event.event_type.value}\ndata: {json.dumps(data)}\n\n"

    def publish_error(self, session_id: str, agent_name: str, error_message: str):
        """Publish an error event when an agent fails."""
        error_event = AgentEvent(
            event_type=AgentEventType.AGENT_FAILED,
            session_id=session_id,
            agent_name=agent_name,
            message=f"Error in {agent_name}: {error_message}",
        )
        self.publish_sync(session_id, error_event)

    def has_subscribers(self, session_id: str) -> bool:
        """Check if a session has active subscribers."""
        return session_id in self._queues and len(self._queues[session_id]) > 0

    def cleanup_stale(self):
        """Remove stale sessions beyond timeout."""
        timeout = settings.sse.connection_timeout_seconds
        now = time.time()
        stale = [
            sid for sid, last in self._last_activity.items()
            if now - last > timeout
        ]
        for sid in stale:
            if sid in self._queues:
                for q in self._queues[sid]:
                    q.put_nowait(None)
                del self._queues[sid]
            self._last_activity.pop(sid, None)


_sse_manager: Optional[SSEManager] = None


def get_sse_manager() -> SSEManager:
    """Get the SSE manager instance."""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEManager()
    return _sse_manager
