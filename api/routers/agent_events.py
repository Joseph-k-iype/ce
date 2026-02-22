"""
Agent Events Router
====================
SSE streaming endpoint for agent progress.
"""

import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.sse_manager import get_sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-events", tags=["agent-events"])


@router.get("/stream/{session_id}")
async def stream_agent_events(session_id: str):
    """SSE stream for agent progress events."""
    sse = get_sse_manager()

    return StreamingResponse(
        sse.event_stream(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
