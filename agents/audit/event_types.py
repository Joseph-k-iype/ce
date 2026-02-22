"""
Event Types
============
Typed events for all agent actions in the event-sourced audit trail.
"""

import uuid
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class AuditEventType(str, Enum):
    """Types of audit events."""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    AGENT_INVOKED = "agent_invoked"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    RULE_ANALYZED = "rule_analyzed"
    DICTIONARY_GENERATED = "dictionary_generated"
    CYPHER_GENERATED = "cypher_generated"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    REFERENCE_DATA_CREATED = "reference_data_created"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    HUMAN_REVIEW_COMPLETED = "human_review_completed"
    SANDBOX_CREATED = "sandbox_created"
    SANDBOX_EVALUATED = "sandbox_evaluated"
    RULE_PROMOTED = "rule_promoted"
    ITERATION_STARTED = "iteration_started"


class AuditEvent(BaseModel):
    """Single audit event in the event store."""
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: AuditEventType
    session_id: str
    agent_name: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None
