"""
Wizard Agent State
==================
LangGraph TypedDict state for the wizard workflow.
"""

from typing import Dict, List, Optional, Any, TypedDict, Annotated
from langgraph.graph.message import add_messages


class WizardAgentState(TypedDict):
    """State maintained throughout the wizard agent workflow."""

    # Input from wizard steps 1-3
    origin_country: str
    scenario_type: str
    receiving_countries: List[str]
    rule_text: str
    data_categories: List[str]
    is_pii_related: bool

    # A2A message log
    messages: Annotated[list, add_messages]

    # Agent outputs
    analysis_result: Optional[Dict[str, Any]]
    dictionary_result: Optional[Dict[str, Any]]
    rule_definition: Optional[Dict[str, Any]]
    cypher_queries: Optional[Dict[str, Any]]
    validation_result: Optional[Dict[str, Any]]
    test_results: Optional[Dict[str, Any]]
    
    # Final synthesized proposal for human review
    proposal: Optional[Dict[str, Any]]

    # Workflow control
    current_phase: str
    iteration: int
    max_iterations: int
    requires_human_input: bool
    agentic_mode: bool  # True = autonomous execution, False = step-by-step wizard

    # Validation tracking
    validation_errors: List[str]  # errors from previous iterations for context
    validation_retry_count: int   # consecutive validation failures (for skip fallback)

    # Circuit breaker: tracks total graph node transitions and per-agent invocations
    graph_step: int                          # incremented on every supervisor call
    agent_retry_counts: Dict[str, int]       # per-agent invocation counts
    test_retry_count: int                    # consecutive rule_tester failures

    # Shared reasoning context between agents
    shared_reasoning: List[Dict[str, Any]]

    # Memory checkpoints for intermediate results preservation
    memory_checkpoints: Dict[str, Any]

    # Events for SSE streaming
    events: List[Dict[str, Any]]

    # Final status
    success: bool
    error_message: Optional[str]


def create_initial_state(
    origin_country: str,
    scenario_type: str,
    receiving_countries: List[str],
    rule_text: str,
    data_categories: Optional[List[str]] = None,
    is_pii_related: bool = False,
    max_iterations: int = 10,
    agentic_mode: bool = False,
) -> WizardAgentState:
    """Create the initial state for a wizard workflow run."""
    return WizardAgentState(
        origin_country=origin_country,
        scenario_type=scenario_type,
        receiving_countries=receiving_countries,
        rule_text=rule_text,
        data_categories=data_categories or [],
        is_pii_related=is_pii_related,
        messages=[],
        analysis_result=None,
        dictionary_result=None,
        rule_definition=None,
        cypher_queries=None,
        validation_result=None,
        test_results=None,
        proposal=None,
        current_phase="supervisor",
        iteration=0,
        max_iterations=max_iterations,
        requires_human_input=False,
        agentic_mode=agentic_mode,
        validation_errors=[],
        validation_retry_count=0,
        graph_step=0,
        agent_retry_counts={},
        test_retry_count=0,
        shared_reasoning=[],
        memory_checkpoints={},
        events=[],
        success=False,
        error_message=None,
    )
