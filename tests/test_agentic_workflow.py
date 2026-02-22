"""
Tests for Agentic Workflow
===========================
Tests for the new multi-agent workflow nodes, state management, and API endpoints.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.state.wizard_state import WizardAgentState, create_initial_state
from agents.nodes.validation_models import RuleDefinitionModel, CypherQueriesModel, ValidationResultModel
from agents.audit.event_store import EventStore, get_event_store
from agents.audit.event_types import AuditEventType, AuditEvent


class TestAgentNodes:
    """Tests for individual agent nodes"""

    @patch("agents.executors.base_executor.ComplianceAgentExecutor.call_ai_with_retry")
    @patch("agents.audit.event_store.get_event_store")
    def test_rule_analyzer_success(self, mock_event_store, mock_call_ai):
        """Test rule analyzer node with successful parsing"""
        mock_store = MagicMock()
        mock_event_store.return_value = mock_store

        # Mock the AI response directly at the executor level
        mock_call_ai.return_value = '''```json
{
    "chain_of_thought": {"step1": "Analyzed rule text"},
    "rule_definition": {
        "rule_type": "attribute",
        "rule_id": "RULE_TEST_001",
        "name": "Test Transfer Rule",
        "description": "A test rule for transfer validation purposes",
        "priority": "medium",
        "origin_countries": ["Germany"],
        "receiving_countries": ["India"],
        "outcome": "prohibition",
        "odrl_type": "Prohibition"
    }
}
```'''

        from agents.nodes.rule_analyzer import rule_analyzer_node

        state = create_initial_state(
            origin_country="Germany",
            scenario_type="transfer",
            receiving_countries=["India"],
            rule_text="Prohibit transfers from Germany to India",
        )

        result = rule_analyzer_node(state)
        assert result.get("rule_definition") is not None
        assert result["rule_definition"]["rule_id"] == "RULE_TEST_001"

    @patch("agents.executors.base_executor.ComplianceAgentExecutor.call_ai_with_retry")
    @patch("agents.audit.event_store.get_event_store")
    def test_cypher_generator_success(self, mock_event_store, mock_call_ai):
        """Test cypher generator node with successful parsing"""
        mock_store = MagicMock()
        mock_event_store.return_value = mock_store

        mock_call_ai.return_value = '''```json
{
    "cypher_queries": {
        "rule_check": "MATCH (c:Case)-[:ORIGINATES_FROM]->(co:Country {name: 'Germany'}) RETURN c",
        "rule_insert": "CREATE (r:Rule {rule_id: 'RULE_TEST_001', name: 'Test'}) RETURN r",
        "validation": "MATCH (r:Rule {rule_id: 'RULE_TEST_001'}) RETURN count(r)"
    },
    "query_params": {},
    "optimization_notes": []
}
```'''

        from agents.nodes.cypher_generator import cypher_generator_node

        state = create_initial_state("Germany", "transfer", ["India"], "test")
        state["rule_definition"] = {"rule_id": "RULE_TEST_001"}

        result = cypher_generator_node(state)
        assert result.get("cypher_queries") is not None
        assert result["current_phase"] == "validator"

    @patch("agents.executors.base_executor.ComplianceAgentExecutor.call_ai_with_retry")
    @patch("agents.audit.event_store.get_event_store")
    def test_validator_pass(self, mock_event_store, mock_call_ai):
        """Test validator node with passing validation"""
        mock_store = MagicMock()
        mock_event_store.return_value = mock_store

        mock_call_ai.return_value = '''```json
{
    "overall_valid": true,
    "confidence_score": 0.9,
    "validation_results": {
        "rule_definition": {"valid": true, "errors": [], "warnings": []},
        "cypher_queries": {"valid": true, "errors": [], "warnings": []},
        "logical": {"valid": true, "errors": [], "warnings": []}
    },
    "suggested_fixes": []
}
```'''

        from agents.nodes.validator import validator_node

        state = create_initial_state("Germany", "transfer", ["India"], "test")
        state["rule_definition"] = {"rule_id": "RULE_TEST_001"}
        state["cypher_queries"] = {"queries": {"rule_check": "MATCH (c) RETURN c"}}

        result = validator_node(state)
        assert result["success"] is True
        assert result.get("success") is True

    @patch("agents.executors.base_executor.ComplianceAgentExecutor.call_ai_with_retry")
    @patch("agents.audit.event_store.get_event_store")
    def test_validator_fail_retries(self, mock_event_store, mock_call_ai):
        """Test validator node with failing validation triggers retry"""
        mock_store = MagicMock()
        mock_event_store.return_value = mock_store

        mock_call_ai.return_value = '''```json
{
    "overall_valid": false,
    "confidence_score": 0.3,
    "validation_results": {
        "rule_definition": {"valid": false, "errors": ["Missing origin"], "warnings": []},
        "cypher_queries": {"valid": true, "errors": [], "warnings": []},
        "logical": {"valid": true, "errors": [], "warnings": []}
    },
    "suggested_fixes": ["Add origin countries"]
}
```'''

        from agents.nodes.validator import validator_node

        state = create_initial_state("Germany", "transfer", ["India"], "test")
        state["rule_definition"] = {"rule_id": "RULE_TEST_001"}
        state["cypher_queries"] = {"queries": {"rule_check": "MATCH (c) RETURN c"}}

        result = validator_node(state)
        assert result["success"] is False
        assert result["current_phase"] == "supervisor"


class TestEventStore:
    """Tests for the event store"""

    def setup_method(self):
        """Reset the singleton store before each test"""
        EventStore().reset()

    def test_append_and_retrieve(self):
        """Test appending and retrieving events"""
        store = EventStore()
        store.append(
            session_id="test-session",
            event_type=AuditEventType.AGENT_INVOKED,
            agent_name="rule_analyzer",
        )

        events = store.get_events("test-session")
        assert len(events) == 1
        assert events[0].event_type == AuditEventType.AGENT_INVOKED
        assert events[0].agent_name == "rule_analyzer"

    def test_session_summary(self):
        """Test session summary"""
        store = EventStore()
        store.append("sess1", AuditEventType.WORKFLOW_STARTED)
        store.append("sess1", AuditEventType.AGENT_INVOKED, agent_name="analyzer")
        store.append("sess1", AuditEventType.RULE_ANALYZED, agent_name="analyzer")
        store.append("sess1", AuditEventType.WORKFLOW_COMPLETED)

        summary = store.get_session_summary("sess1")
        assert summary["total_events"] == 4
        assert summary["session_id"] == "sess1"

    def test_list_sessions(self):
        """Test listing sessions"""
        store = EventStore()
        store.append("sess1", AuditEventType.WORKFLOW_STARTED)
        store.append("sess2", AuditEventType.WORKFLOW_STARTED)
        store.append("sess1", AuditEventType.WORKFLOW_COMPLETED)

        sessions = store.list_sessions()
        assert len(sessions) == 2

    def test_export_session(self):
        """Test exporting session events"""
        store = EventStore()
        store.append("sess1", AuditEventType.AGENT_INVOKED, agent_name="test")

        export = store.export_session("sess1")
        assert export != "[]"
        import json
        parsed = json.loads(export)
        assert len(parsed) == 1

    def test_empty_session_export(self):
        """Test exporting nonexistent session"""
        store = EventStore()
        export = store.export_session("nonexistent")
        assert export == "[]"

    def test_event_with_data_and_duration(self):
        """Test event with data payload and duration"""
        store = EventStore()
        store.append(
            session_id="sess1",
            event_type=AuditEventType.CYPHER_GENERATED,
            agent_name="cypher_gen",
            data={"query_count": 3},
            duration_ms=150.5,
        )

        events = store.get_events("sess1")
        assert events[0].data == {"query_count": 3}
        assert events[0].duration_ms == 150.5

    def test_event_with_error(self):
        """Test event with error"""
        store = EventStore()
        store.append(
            session_id="sess1",
            event_type=AuditEventType.AGENT_FAILED,
            agent_name="validator",
            error="Parse error",
        )

        events = store.get_events("sess1")
        assert events[0].error == "Parse error"


class TestAPIEndpoints:
    """Tests for the API endpoints"""

    @pytest.fixture
    def client(self):
        """Get test client"""
        from api.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_agent_sessions_endpoint(self, client):
        """Test the agent sessions listing endpoint"""
        response = client.get("/api/agent/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_agent_stats_endpoint(self, client):
        """Test the agent stats endpoint"""
        response = client.get("/api/agent/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "total_events" in data

    def test_agent_session_not_found(self, client):
        """Test 404 for nonexistent session"""
        response = client.get("/api/agent/sessions/nonexistent-id")
        assert response.status_code == 404

    def test_cache_stats_endpoint(self, client):
        """Test cache stats endpoint"""
        response = client.get("/api/cache/stats")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
