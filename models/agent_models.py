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
    # Core lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    PHASE_CHANGED = "phase_changed"

    # Agent-specific progress
    ANALYSIS_PROGRESS = "analysis_progress"
    DICTIONARY_PROGRESS = "dictionary_progress"
    VALIDATION_PROGRESS = "validation_progress"
    CYPHER_PROGRESS = "cypher_progress"

    # AI call lifecycle
    AI_CALL_STARTED = "ai_call_started"
    AI_CALL_COMPLETED = "ai_call_completed"
    AI_CALL_RETRY = "ai_call_retry"

    # Execution details
    QUERY_EXECUTION = "query_execution"
    CIRCUIT_BREAKER_STATE = "circuit_breaker_state"
    VALIDATION_DETAIL = "validation_detail"
    AGENT_REASONING = "agent_reasoning"

    # Step progress
    STEP_PROGRESS = "step_progress"

    # Workflow lifecycle
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
    step_current: Optional[int] = None
    step_total: Optional[int] = None
    elapsed_ms: Optional[float] = None
    estimated_remaining_ms: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
