"""
Tests for Agent Audit Event Store
====================================
Tests for the event-sourced audit trail used by the agent workflow.
"""

import pytest
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.audit.event_store import EventStore, get_event_store
from agents.audit.event_types import AuditEventType, AuditEvent


class TestAuditEventType:
    """Tests for AuditEventType enum"""

    def test_event_types_exist(self):
        """Test that all expected event types exist"""
        assert AuditEventType.WORKFLOW_STARTED
        assert AuditEventType.WORKFLOW_COMPLETED
        assert AuditEventType.WORKFLOW_FAILED
        assert AuditEventType.AGENT_INVOKED
        assert AuditEventType.AGENT_FAILED
        assert AuditEventType.RULE_ANALYZED
        assert AuditEventType.CYPHER_GENERATED
        assert AuditEventType.VALIDATION_PASSED
        assert AuditEventType.VALIDATION_FAILED


class TestAuditEvent:
    """Tests for AuditEvent model"""

    def test_create_event(self):
        """Test creating an audit event"""
        event = AuditEvent(
            session_id="sess-001",
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name="rule_analyzer",
        )
        assert event.session_id == "sess-001"
        assert event.event_type == AuditEventType.AGENT_INVOKED
        assert event.agent_name == "rule_analyzer"
        assert event.timestamp is not None

    def test_event_with_data(self):
        """Test event with data payload"""
        event = AuditEvent(
            session_id="sess-001",
            event_type=AuditEventType.RULE_ANALYZED,
            agent_name="rule_analyzer",
            data={"rule_id": "RULE_TEST_001"},
            duration_ms=250.0,
        )
        assert event.data["rule_id"] == "RULE_TEST_001"
        assert event.duration_ms == 250.0

    def test_event_with_error(self):
        """Test event with error"""
        event = AuditEvent(
            session_id="sess-001",
            event_type=AuditEventType.AGENT_FAILED,
            agent_name="cypher_generator",
            error="Failed to parse LLM response",
        )
        assert event.error == "Failed to parse LLM response"

    def test_event_model_dump(self):
        """Test serializing event to dict"""
        event = AuditEvent(
            session_id="sess-001",
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name="validator",
        )
        dumped = event.model_dump()
        assert "session_id" in dumped
        assert "event_type" in dumped
        assert "timestamp" in dumped


class TestEventStore:
    """Tests for the EventStore service"""

    @pytest.fixture
    def store(self):
        """Create a fresh event store for each test"""
        store = EventStore()
        store.reset()
        return store

    def test_append_event(self, store):
        """Test appending a single event"""
        store.append(
            session_id="sess-001",
            event_type=AuditEventType.WORKFLOW_STARTED,
        )
        events = store.get_events("sess-001")
        assert len(events) == 1
        assert events[0].event_type == AuditEventType.WORKFLOW_STARTED

    def test_append_multiple_events(self, store):
        """Test appending multiple events to the same session"""
        store.append("sess-001", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-001", AuditEventType.AGENT_INVOKED, agent_name="analyzer")
        store.append("sess-001", AuditEventType.RULE_ANALYZED, agent_name="analyzer", duration_ms=500)
        store.append("sess-001", AuditEventType.AGENT_INVOKED, agent_name="cypher_gen")
        store.append("sess-001", AuditEventType.CYPHER_GENERATED, agent_name="cypher_gen")
        store.append("sess-001", AuditEventType.WORKFLOW_COMPLETED)

        events = store.get_events("sess-001")
        assert len(events) == 6

    def test_events_are_ordered(self, store):
        """Test that events maintain insertion order"""
        store.append("sess-001", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-001", AuditEventType.AGENT_INVOKED, agent_name="a")
        store.append("sess-001", AuditEventType.AGENT_INVOKED, agent_name="b")

        events = store.get_events("sess-001")
        assert events[0].event_type == AuditEventType.WORKFLOW_STARTED
        assert events[1].agent_name == "a"
        assert events[2].agent_name == "b"

    def test_get_events_empty_session(self, store):
        """Test retrieving events for a nonexistent session"""
        events = store.get_events("nonexistent")
        assert len(events) == 0

    def test_session_summary(self, store):
        """Test getting a session summary"""
        store.append("sess-001", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-001", AuditEventType.AGENT_INVOKED, agent_name="analyzer")
        store.append("sess-001", AuditEventType.RULE_ANALYZED, agent_name="analyzer")

        summary = store.get_session_summary("sess-001")
        assert summary["session_id"] == "sess-001"
        assert summary["total_events"] == 3

    def test_session_summary_empty(self, store):
        """Test summary for nonexistent session"""
        summary = store.get_session_summary("nonexistent")
        assert summary["total_events"] == 0

    def test_list_sessions(self, store):
        """Test listing all sessions"""
        store.append("sess-001", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-002", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-003", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-001", AuditEventType.WORKFLOW_COMPLETED)

        sessions = store.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_with_limit(self, store):
        """Test listing sessions with limit"""
        for i in range(10):
            store.append(f"sess-{i:03d}", AuditEventType.WORKFLOW_STARTED)

        sessions = store.list_sessions(limit=5)
        assert len(sessions) == 5

    def test_export_session(self, store):
        """Test exporting session as JSON string"""
        store.append("sess-001", AuditEventType.AGENT_INVOKED, agent_name="test")
        store.append("sess-001", AuditEventType.RULE_ANALYZED, agent_name="test")

        export = store.export_session("sess-001")
        parsed = json.loads(export)
        assert len(parsed) == 2

    def test_export_empty_session(self, store):
        """Test exporting nonexistent session returns empty array"""
        export = store.export_session("nonexistent")
        assert export == "[]"

    def test_event_data_preserved(self, store):
        """Test that event data payloads are preserved"""
        store.append(
            session_id="sess-001",
            event_type=AuditEventType.VALIDATION_PASSED,
            agent_name="validator",
            data={"confidence": 0.95, "rule_id": "RULE_TEST"},
            duration_ms=300.0,
        )

        events = store.get_events("sess-001")
        assert events[0].data["confidence"] == 0.95
        assert events[0].data["rule_id"] == "RULE_TEST"
        assert events[0].duration_ms == 300.0

    def test_event_error_preserved(self, store):
        """Test that error messages are preserved"""
        store.append(
            session_id="sess-001",
            event_type=AuditEventType.AGENT_FAILED,
            agent_name="cypher_gen",
            error="JSON parse error: unexpected token",
        )

        events = store.get_events("sess-001")
        assert "JSON parse error" in events[0].error

    def test_multiple_sessions_isolated(self, store):
        """Test that events from different sessions don't mix"""
        store.append("sess-001", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-002", AuditEventType.WORKFLOW_STARTED)
        store.append("sess-001", AuditEventType.AGENT_INVOKED, agent_name="a")
        store.append("sess-002", AuditEventType.AGENT_INVOKED, agent_name="b")

        events_1 = store.get_events("sess-001")
        events_2 = store.get_events("sess-002")

        assert len(events_1) == 2
        assert len(events_2) == 2
        assert events_1[1].agent_name == "a"
        assert events_2[1].agent_name == "b"

    def test_get_event_store_singleton(self):
        """Test that get_event_store returns the same instance"""
        store1 = get_event_store()
        store2 = get_event_store()
        assert store1 is store2

    def test_thread_safety(self, store):
        """Test that the event store is thread-safe"""
        import threading

        errors = []

        def append_event(i):
            try:
                store.append(
                    session_id="concurrent-test",
                    event_type=AuditEventType.AGENT_INVOKED,
                    agent_name=f"thread_{i}",
                )
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=append_event, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        events = store.get_events("concurrent-test")
        assert len(events) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
