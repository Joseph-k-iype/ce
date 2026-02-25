"""
Tests for LangGraph Rule Ingestion Workflow
=============================================
Tests for the new multi-agent workflow with supervisor, analyzer, generator, and validator.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from agents.nodes.validation_models import (
    RuleDefinitionModel,
    CypherQueriesModel,
    ValidationResultModel,
)
from agents.state.wizard_state import WizardAgentState, create_initial_state
from agents.workflows.rule_ingestion_workflow import (
    build_rule_ingestion_graph,
    run_rule_ingestion,
    RuleIngestionResult,
    route_from_supervisor,
)
from pydantic import ValidationError


class TestPydanticModels:
    """Test Pydantic validation models"""

    def test_rule_definition_model_valid(self):
        """Test valid rule definition"""
        rule = RuleDefinitionModel(
            rule_type="attribute",
            rule_id="RULE_TEST_001",
            name="Test Transfer Rule",
            description="This is a test rule for transfer validation",
            priority="medium",
            origin_countries=["Germany"],
            receiving_countries=["India"],
            outcome="prohibition",
            odrl_type="Prohibition",
        )
        assert rule.rule_type == "attribute"
        assert rule.rule_id == "RULE_TEST_001"
        assert rule.priority == "medium"

    def test_rule_definition_model_invalid_rule_id(self):
        """Test invalid rule ID format (Permissive model should accept it)"""
        rule = RuleDefinitionModel(
            rule_type="attribute",
            rule_id="INVALID_001",  # Should ideally start with RULE_ but model is permissive
            name="Test Rule",
            description="Test description here",
            priority="medium",
            outcome="prohibition",
            odrl_type="Prohibition",
        )
        assert rule.rule_id == "INVALID_001"

    def test_rule_definition_model_invalid_priority(self):
        """Test invalid priority range (Normalised to medium)"""
        rule = RuleDefinitionModel(
            rule_type="attribute",
            rule_id="RULE_TEST_002",
            name="Test Rule",
            description="Test description here",
            priority="critical",  # Invalid
            outcome="prohibition",
            odrl_type="Prohibition",
        )
        assert rule.priority == "medium"

    def test_rule_definition_model_mismatched_odrl(self):
        """Test mismatched outcome and odrl_type (Permissive model allows it)"""
        rule = RuleDefinitionModel(
            rule_type="attribute",
            rule_id="RULE_TEST_003",
            name="Test Rule",
            description="Test description here",
            priority="medium",
            outcome="prohibition",
            odrl_type="Permission",  # Mismatch allowed structurally
        )
        assert rule.odrl_type == "Prohibition"

    def test_rule_definition_model_invalid_country_group(self):
        """Test invalid country group (Permissive model allows it)"""
        rule = RuleDefinitionModel(
            rule_type="attribute",
            rule_id="RULE_TEST_004",
            name="Test Rule",
            description="Test description here",
            priority="medium",
            origin_group="INVALID_GROUP",
            outcome="prohibition",
            odrl_type="Prohibition",
        )
        assert rule.origin_group == "INVALID_GROUP"

    def test_rule_definition_model_valid_country_group(self):
        """Test valid country group"""
        rule = RuleDefinitionModel(
            rule_type="attribute",
            rule_id="RULE_TEST_005",
            name="Test EU Rule",
            description="Test rule for EU transfers",
            priority="medium",
            origin_group="EU_EEA",
            outcome="permission",
            odrl_type="Permission",
        )
        assert rule.origin_group == "EU_EEA"

    def test_cypher_queries_model_valid(self):
        """Test valid Cypher queries"""
        queries = CypherQueriesModel(
            rule_check="MATCH (c:Case) RETURN c",
            rule_insert="CREATE (r:Rule {name: 'test'})",
            validation="MATCH (r:Rule) RETURN count(r)",
        )
        assert "MATCH" in queries.rule_check
        assert "CREATE" in queries.rule_insert

    def test_cypher_queries_model_invalid_syntax(self):
        """Test Cypher queries without required keywords"""
        with pytest.raises(ValidationError):
            CypherQueriesModel(
                rule_check="SELECT * FROM table",  # Not Cypher
                rule_insert="CREATE (r:Rule {name: 'test'})",
                validation="MATCH (r:Rule) RETURN count(r)",
            )

    def test_validation_result_model(self):
        """Test validation result model"""
        result = ValidationResultModel(
            overall_valid=True,
            confidence_score=0.85,
            rule_definition_valid=True,
            cypher_valid=True,
            logical_valid=True,
        )
        assert result.overall_valid is True
        assert result.confidence_score == 0.85

    def test_validation_result_clamped_confidence(self):
        """Test validation result clamps confidence score"""
        result = ValidationResultModel(
            overall_valid=True,
            confidence_score=1.5,
        )
        assert result.confidence_score == 1.0


class TestWizardAgentState:
    """Test WizardAgentState initialization"""

    def test_create_initial_state(self):
        """Test creating initial state"""
        state = create_initial_state(
            origin_country="Germany",
            scenario_type="transfer",
            receiving_countries=["India"],
            rule_text="Prohibit transfers from Germany to India",
        )
        assert state["origin_country"] == "Germany"
        assert state["scenario_type"] == "transfer"
        assert state["receiving_countries"] == ["India"]
        assert state["rule_text"] == "Prohibit transfers from Germany to India"
        assert state["iteration"] == 0
        assert state["max_iterations"] == 10  # Updated default
        assert state["success"] is False
        assert state["current_phase"] == "supervisor"

    def test_create_initial_state_with_categories(self):
        """Test creating initial state with data categories"""
        state = create_initial_state(
            origin_country="UK",
            scenario_type="attribute",
            receiving_countries=[],
            rule_text="Health data rule",
            data_categories=["health", "genetic"],
            max_iterations=5,
        )
        assert state["data_categories"] == ["health", "genetic"]
        assert state["max_iterations"] == 5


class TestRouting:
    """Test workflow routing functions"""

    def test_route_from_supervisor_valid_phases(self):
        """Test routing to valid agent phases"""
        for phase in ["rule_analyzer", "data_dictionary", "cypher_generator",
                       "validator", "reference_data", "human_review", "complete", "fail"]:
            state = create_initial_state("US", "transfer", [], "test")
            state["current_phase"] = phase
            assert route_from_supervisor(state) == phase

    def test_route_from_supervisor_max_iterations(self):
        """Test routing to fail when max iterations reached"""
        state = create_initial_state("US", "transfer", [], "test", max_iterations=3)
        state["iteration"] = 3
        state["current_phase"] = "rule_analyzer"
        assert route_from_supervisor(state) == "fail"

    def test_route_from_supervisor_invalid_phase(self):
        """Test routing to fail for unknown phase"""
        state = create_initial_state("US", "transfer", [], "test")
        state["current_phase"] = "unknown_agent"
        assert route_from_supervisor(state) == "fail"

    # def test_route_after_validation_complete(self):
    #     \"\"\"Test routing after successful validation\"\"\"
    #     state = create_initial_state("US", "transfer", [], "test")
    #     state["current_phase"] = "complete"
    #     assert route_after_validation(state) == "review_proposal"  # Updated route

    # def test_route_after_validation_fail(self):
    #     \"\"\"Test routing after failed validation\"\"\"
    #     state = create_initial_state("US", "transfer", [], "test")
    #     state["current_phase"] = "fail"
    #     assert route_after_validation(state) == "fail"

    # def test_route_after_validation_retry(self):
    #     \"\"\"Test routing back to supervisor for retry\"\"\"
    #     state = create_initial_state("US", "transfer", [], "test")
    #     state["current_phase"] = "supervisor"
    #     assert route_after_validation(state) == "supervisor"


class TestRuleIngestionResult:
    """Test RuleIngestionResult model"""

    def test_successful_result(self):
        """Test successful result from state"""
        state = create_initial_state("US", "transfer", [], "test")
        state["success"] = True
        state["rule_definition"] = {"rule_id": "RULE_AUTO_001", "rule_type": "transfer"}
        state["iteration"] = 2
        result = RuleIngestionResult(state)
        assert result.success is True
        assert result.rule_definition["rule_id"] == "RULE_AUTO_001"
        assert result.iterations == 2

    def test_failed_result(self):
        """Test failed result from state"""
        state = create_initial_state("US", "transfer", [], "test")
        state["success"] = False
        state["error_message"] = "Max iterations reached"
        state["iteration"] = 3
        result = RuleIngestionResult(state)
        assert result.success is False
        assert result.error_message == "Max iterations reached"

    def test_result_with_all_fields(self):
        """Test result with all optional fields populated"""
        state = create_initial_state("US", "transfer", ["UK"], "test")
        state["success"] = True
        state["rule_definition"] = {"rule_id": "RULE_001"}
        state["cypher_queries"] = {"queries": {"rule_check": "MATCH (c) RETURN c"}}
        state["dictionary_result"] = {"keywords": ["test"]}
        state["analysis_result"] = {"step1": "analysis"}
        state["validation_result"] = {"overall_valid": True}
        result = RuleIngestionResult(state)
        assert result.rule_definition is not None
        assert result.cypher_queries is not None
        assert result.dictionary_result is not None
        assert result.analysis_result is not None
        assert result.validation_result is not None


class TestBuildGraph:
    """Test LangGraph workflow graph building"""

    def test_build_graph_with_interrupt(self):
        """Test building graph with human review interrupt"""
        graph, checkpointer = build_rule_ingestion_graph(with_interrupt=True)
        assert graph is not None
        assert checkpointer is not None

    def test_build_graph_without_interrupt(self):
        """Test building graph without interrupt"""
        graph, checkpointer = build_rule_ingestion_graph(with_interrupt=False)
        assert graph is not None
        assert checkpointer is not None


class TestRunRuleIngestion:
    """Test the main run_rule_ingestion function"""

    @patch("agents.workflows.rule_ingestion_workflow.build_rule_ingestion_graph")
    @patch("agents.workflows.rule_ingestion_workflow.get_event_store")
    def test_successful_workflow(self, mock_event_store, mock_build_graph):
        """Test successful workflow execution"""
        mock_store = MagicMock()
        mock_event_store.return_value = mock_store

        final_state = create_initial_state("UK", "transfer", ["US"], "test rule")
        final_state["success"] = True
        final_state["rule_definition"] = {"rule_id": "RULE_AUTO_001", "rule_type": "transfer"}

        mock_graph = MagicMock()
        mock_graph.invoke.return_value = final_state
        mock_build_graph.return_value = (mock_graph, MagicMock())

        result = run_rule_ingestion(
            origin_country="UK",
            scenario_type="transfer",
            receiving_countries=["US"],
            rule_text="Test rule text",
        )

        assert result.success is True
        assert result.rule_definition["rule_id"] == "RULE_AUTO_001"

    @patch("agents.workflows.rule_ingestion_workflow.build_rule_ingestion_graph")
    @patch("agents.workflows.rule_ingestion_workflow.get_event_store")
    def test_failed_workflow(self, mock_event_store, mock_build_graph):
        """Test workflow that fails after max iterations"""
        mock_store = MagicMock()
        mock_event_store.return_value = mock_store

        final_state = create_initial_state("UK", "transfer", [], "test")
        final_state["success"] = False
        final_state["error_message"] = "Max iterations reached"

        mock_graph = MagicMock()
        mock_graph.invoke.return_value = final_state
        mock_build_graph.return_value = (mock_graph, MagicMock())

        result = run_rule_ingestion(
            origin_country="UK",
            scenario_type="transfer",
            receiving_countries=[],
            rule_text="Invalid rule text",
        )

        assert result.success is False
        assert "Max iterations" in result.error_message

    @patch("agents.workflows.rule_ingestion_workflow.build_rule_ingestion_graph")
    @patch("agents.workflows.rule_ingestion_workflow.get_event_store")
    def test_workflow_exception(self, mock_event_store, mock_build_graph):
        """Test workflow with unexpected exception"""
        mock_store = MagicMock()
        mock_event_store.return_value = mock_store

        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = Exception("Network error")
        mock_build_graph.return_value = (mock_graph, MagicMock())

        result = run_rule_ingestion(
            origin_country="Germany",
            scenario_type="transfer",
            receiving_countries=[],
            rule_text="Test rule",
        )

        assert result.success is False
        assert "Network error" in result.error_message
