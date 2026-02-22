"""
A2A Agent Registry
===================
Agent registry using Google A2A SDK AgentCard / AgentSkill types.
Replaces the custom AgentRegistry and AgentCapability models.
"""

import logging
from typing import Dict, List, Optional

from a2a.types import AgentCard, AgentSkill, AgentCapabilities

logger = logging.getLogger(__name__)

# Protocol version for internal A2A cards
_PROTOCOL_VERSION = "0.3.22"


def _build_default_cards() -> Dict[str, AgentCard]:
    """Build AgentCards for the six compliance agents."""
    cards: Dict[str, AgentCard] = {}

    definitions = [
        {
            "name": "supervisor",
            "description": "Orchestrates the wizard workflow, manages TODO list, routes tasks",
            "skills": [
                AgentSkill(
                    id="orchestrate",
                    name="Orchestrate Workflow",
                    description="Route tasks to appropriate agents and manage iteration flow",
                    tags=["orchestration", "routing"],
                ),
                AgentSkill(
                    id="route",
                    name="Route Decision",
                    description="Decide which agent should execute next",
                    tags=["orchestration", "routing"],
                ),
            ],
        },
        {
            "name": "rule_analyzer",
            "description": "Chain of Thought reasoning to extract rule structure from text",
            "skills": [
                AgentSkill(
                    id="analyze_rule",
                    name="Analyze Rule",
                    description="Extract structured rule definition from natural language",
                    tags=["analysis", "rule"],
                ),
            ],
        },
        {
            "name": "cypher_generator",
            "description": "Mixture of Experts Cypher query generation for FalkorDB",
            "skills": [
                AgentSkill(
                    id="generate_cypher",
                    name="Generate Cypher",
                    description="Generate rule_check, rule_insert, and validation Cypher queries",
                    tags=["cypher", "generation"],
                ),
            ],
        },
        {
            "name": "validator",
            "description": "Validates rules, Cypher queries, and logical consistency",
            "skills": [
                AgentSkill(
                    id="validate_rule",
                    name="Validate Rule",
                    description="Comprehensive validation of rule definition and Cypher queries",
                    tags=["validation", "rule"],
                ),
            ],
        },
        {
            "name": "data_dictionary",
            "description": "Generates keyword dictionaries per data category",
            "skills": [
                AgentSkill(
                    id="generate_dictionary",
                    name="Generate Dictionary",
                    description="Create keyword dictionaries for data categories",
                    tags=["dictionary", "generation"],
                ),
            ],
        },
        {
            "name": "reference_data",
            "description": "Creates country groups and attribute configurations in FalkorDB",
            "skills": [
                AgentSkill(
                    id="create_reference",
                    name="Create Reference Data",
                    description="Identify and create missing country groups and attribute configs",
                    tags=["reference", "data"],
                ),
            ],
        },
    ]

    for defn in definitions:
        card = AgentCard(
            name=defn["name"],
            description=defn["description"],
            url=f"internal://{defn['name']}",
            version="1.0.0",
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
        self._initialized = True
        logger.info(f"A2A Agent Registry initialized with {len(self._cards)} agents")

    def get_card(self, agent_name: str) -> Optional[AgentCard]:
        """Get an agent's card by name."""
        return self._cards.get(agent_name)

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
