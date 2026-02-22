"""
A2A Agent Registry & Inter-Agent Contracts
============================================
Agent registry using Google A2A SDK AgentCard / AgentSkill types,
plus inter-agent contract definitions that enforce data shape between agents.
"""

import logging
from typing import Dict, List, Optional

from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Protocol version for internal A2A cards
_PROTOCOL_VERSION = "0.4.0"


# ═══════════════════════════════════════════════════════════════════════════════
# Inter-Agent Contracts
# ═══════════════════════════════════════════════════════════════════════════════

class AgentContract(BaseModel):
    """Defines the input/output contract for an agent.

    Used by the supervisor and executors to validate that required
    data is available before invoking an agent.
    """
    agent_name: str
    required_inputs: List[str] = Field(
        default_factory=list,
        description="State keys that MUST be present before this agent runs",
    )
    optional_inputs: List[str] = Field(
        default_factory=list,
        description="State keys that enhance output but are not required",
    )
    produced_outputs: List[str] = Field(
        default_factory=list,
        description="State keys that this agent populates on success",
    )
    preconditions: List[str] = Field(
        default_factory=list,
        description="Human-readable preconditions for this agent",
    )
    postconditions: List[str] = Field(
        default_factory=list,
        description="Human-readable postconditions (what should be true after success)",
    )


# Agent contracts define what each agent needs and produces
AGENT_CONTRACTS: Dict[str, AgentContract] = {
    "rule_analyzer": AgentContract(
        agent_name="rule_analyzer",
        required_inputs=["rule_text", "origin_country"],
        optional_inputs=["receiving_countries", "scenario_type", "data_categories", "is_pii_related"],
        produced_outputs=["rule_definition", "analysis_result"],
        preconditions=["Rule text must be a non-empty compliance rule description"],
        postconditions=[
            "rule_definition contains rule_id, name, outcome, rule_type",
            "analysis_result contains chain_of_thought reasoning",
        ],
    ),
    "data_dictionary": AgentContract(
        agent_name="data_dictionary",
        required_inputs=["rule_text"],
        optional_inputs=["data_categories", "analysis_result", "is_pii_related"],
        produced_outputs=["dictionary_result"],
        preconditions=["Rule text or data categories must be available for term extraction"],
        postconditions=["dictionary_result contains at least one category with keywords"],
    ),
    "cypher_generator": AgentContract(
        agent_name="cypher_generator",
        required_inputs=["rule_definition"],
        optional_inputs=["dictionary_result", "origin_country", "receiving_countries", "data_categories"],
        produced_outputs=["cypher_queries"],
        preconditions=["rule_definition must contain rule_id, name, outcome, rule_type"],
        postconditions=[
            "cypher_queries contains rule_check, rule_insert, validation queries",
            "All queries are FalkorDB-compatible OpenCypher",
        ],
    ),
    "validator": AgentContract(
        agent_name="validator",
        required_inputs=["rule_text", "rule_definition", "cypher_queries"],
        optional_inputs=["dictionary_result"],
        produced_outputs=["validation_result"],
        preconditions=["All upstream outputs must be present for cross-validation"],
        postconditions=[
            "validation_result contains overall_valid boolean",
            "If overall_valid is false, suggested_fixes must be non-empty",
        ],
    ),
    "rule_tester": AgentContract(
        agent_name="rule_tester",
        required_inputs=["rule_definition"],
        optional_inputs=["rule_text", "dictionary_result", "origin_country", "receiving_countries"],
        produced_outputs=["test_results"],
        preconditions=["rule_definition must be validated before testing"],
        postconditions=["test_results contains pass/fail for each scenario"],
    ),
    "reference_data": AgentContract(
        agent_name="reference_data",
        required_inputs=["rule_definition"],
        optional_inputs=["rule_text"],
        produced_outputs=[],
        preconditions=["rule_definition must reference country groups or attributes"],
        postconditions=["Missing reference data is flagged or created"],
    ),
}


def get_agent_contract(agent_name: str) -> Optional[AgentContract]:
    """Get the contract for an agent."""
    return AGENT_CONTRACTS.get(agent_name)


def check_agent_preconditions(agent_name: str, state: dict) -> tuple[bool, list[str]]:
    """Check if an agent's required inputs are present in state.

    Returns:
        (can_proceed, missing_inputs) tuple
    """
    contract = AGENT_CONTRACTS.get(agent_name)
    if not contract:
        return True, []

    missing = []
    for key in contract.required_inputs:
        val = state.get(key)
        if val is None or val == "" or val == [] or val == {}:
            missing.append(key)

    return len(missing) == 0, missing


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Card Registry
# ═══════════════════════════════════════════════════════════════════════════════

def _build_default_cards() -> Dict[str, AgentCard]:
    """Build AgentCards for the compliance agents."""
    cards: Dict[str, AgentCard] = {}

    definitions = [
        {
            "name": "supervisor",
            "description": (
                "Workflow orchestrator using Mandatory Logical Sequence framework. "
                "Assesses state, determines next agent, constructs targeted feedback, "
                "and enforces convergence rules to prevent infinite loops."
            ),
            "skills": [
                AgentSkill(
                    id="orchestrate",
                    name="Orchestrate Workflow",
                    description=(
                        "Route tasks to appropriate agents based on state assessment. "
                        "Enforces hard-stop at iteration limit and agent retry caps."
                    ),
                    tags=["orchestration", "routing", "convergence"],
                ),
                AgentSkill(
                    id="route",
                    name="Route Decision",
                    description="Select next agent with specific feedback from validator errors",
                    tags=["orchestration", "routing"],
                ),
            ],
        },
        {
            "name": "rule_analyzer",
            "description": (
                "Senior compliance rule analyst using CoT + ToT + MoE reasoning. "
                "Performs requirement check before analysis. Identifies domain, "
                "ontologies, entity links. Outputs validated RuleDefinitionModel."
            ),
            "skills": [
                AgentSkill(
                    id="analyze_rule",
                    name="Analyze Rule",
                    description=(
                        "Parse natural language rule into structured rule_definition. "
                        "Hard-stops if rule_text or origin_country is missing."
                    ),
                    tags=["analysis", "rule", "hard-stop"],
                ),
            ],
        },
        {
            "name": "cypher_generator",
            "description": (
                "Senior graph database engineer generating FalkorDB OpenCypher queries. "
                "Requirement-checks rule_definition before generating. "
                "Produces rule_check, rule_insert, rule_links, validation queries."
            ),
            "skills": [
                AgentSkill(
                    id="generate_cypher",
                    name="Generate Cypher",
                    description=(
                        "Generate 4 Cypher queries (check, insert, links, validation). "
                        "Hard-stops if rule_definition is missing."
                    ),
                    tags=["cypher", "generation", "falkordb", "hard-stop"],
                ),
            ],
        },
        {
            "name": "validator",
            "description": (
                "Senior QA engineer validating rule definitions, Cypher queries, "
                "and dictionaries. Quality gate — nothing passes without explicit approval. "
                "Returns overall_valid with errors/warnings/suggested_fixes."
            ),
            "skills": [
                AgentSkill(
                    id="validate_rule",
                    name="Validate Rule",
                    description=(
                        "Comprehensive validation of rule, cypher, dictionary, and logic. "
                        "Hard-stops if rule_definition or cypher_queries missing."
                    ),
                    tags=["validation", "rule", "quality-gate", "hard-stop"],
                ),
            ],
        },
        {
            "name": "data_dictionary",
            "description": (
                "Senior data classification specialist generating keyword dictionaries. "
                "Builds upon analyzer's CoT output. Supports Tier 2 fuzzy matching."
            ),
            "skills": [
                AgentSkill(
                    id="generate_dictionary",
                    name="Generate Dictionary",
                    description=(
                        "Create keyword dictionaries for data categories using four perspectives. "
                        "Includes PII sub-dictionary if applicable."
                    ),
                    tags=["dictionary", "generation", "classification"],
                ),
            ],
        },
        {
            "name": "reference_data",
            "description": (
                "Senior data architect maintaining reference data integrity. "
                "Creates missing country groups and attribute configs."
            ),
            "skills": [
                AgentSkill(
                    id="create_reference",
                    name="Create Reference Data",
                    description="Identify and create missing country groups and attribute configs",
                    tags=["reference", "data", "gap-analysis"],
                ),
            ],
        },
        {
            "name": "rule_tester",
            "description": (
                "Senior QA test engineer generating comprehensive test scenarios. "
                "Covers country matching, PII gate, Tier 1 exact, Tier 2 fuzzy, "
                "and outcome verification dimensions."
            ),
            "skills": [
                AgentSkill(
                    id="test_rule",
                    name="Test Rule",
                    description=(
                        "Generate and execute 8-12 test scenarios covering all matching dimensions. "
                        "Requires both positive and negative test cases."
                    ),
                    tags=["testing", "rule", "scenarios"],
                ),
            ],
        },
    ]

    for defn in definitions:
        card = AgentCard(
            name=defn["name"],
            description=defn["description"],
            url=f"internal://{defn['name']}",
            version=_PROTOCOL_VERSION,
            skills=defn["skills"],
            capabilities=AgentCapabilities(streaming=False, push_notifications=False),
            default_input_modes=["application/json"],
            default_output_modes=["application/json"],
        )
        cards[defn["name"]] = card

    return cards


class A2AAgentRegistry:
    """Registry of agent cards using Google A2A SDK types.

    Singleton that holds AgentCard instances for all compliance agents.
    """

    _instance: Optional["A2AAgentRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._cards: Dict[str, AgentCard] = _build_default_cards()
        self._contracts: Dict[str, AgentContract] = AGENT_CONTRACTS
        self._initialized = True
        logger.info(f"A2A Agent Registry initialized with {len(self._cards)} agents")

    def get_card(self, agent_name: str) -> Optional[AgentCard]:
        """Get an agent's card by name."""
        return self._cards.get(agent_name)

    def get_contract(self, agent_name: str) -> Optional[AgentContract]:
        """Get an agent's contract by name."""
        return self._contracts.get(agent_name)

    def list_cards(self) -> List[AgentCard]:
        """List all registered agent cards."""
        return list(self._cards.values())

    def find_agent_for_skill(self, skill_id: str) -> Optional[str]:
        """Find an agent that has a given skill."""
        for name, card in self._cards.items():
            if card.skills:
                for skill in card.skills:
                    if skill.id == skill_id:
                        return name
        return None

    def register_card(self, card: AgentCard):
        """Register or update an agent card."""
        self._cards[card.name] = card
        logger.info(f"Registered agent card: {card.name}")


_registry: Optional[A2AAgentRegistry] = None


def get_agent_registry() -> A2AAgentRegistry:
    """Get the agent registry singleton."""
    global _registry
    if _registry is None:
        _registry = A2AAgentRegistry()
    return _registry
