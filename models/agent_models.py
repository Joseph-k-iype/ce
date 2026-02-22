"""
Agent Models
============
Pydantic models for agent events used by SSE streaming.

Custom A2A types (A2AMessageType, TaskStatus, A2AMessage, TaskRequest,
TaskResult, AgentCapability) have been replaced by Google A2A SDK types.
"""

from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class AgentEventType(str, Enum):
    """Types of agent events for SSE streaming"""
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    PHASE_CHANGED = "phase_changed"
    ANALYSIS_PROGRESS = "analysis_progress"
    DICTIONARY_PROGRESS = "dictionary_progress"
    VALIDATION_PROGRESS = "validation_progress"
    CYPHER_PROGRESS = "cypher_progress"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    ITERATION_STARTED = "iteration_started"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_FAILED = "workflow_failed"
    HEARTBEAT = "heartbeat"


class AgentEvent(BaseModel):
    """Event emitted by agents for SSE streaming"""
    event_type: AgentEventType
    session_id: str
    agent_name: str = ""
    phase: str = ""
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    progress_pct: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
