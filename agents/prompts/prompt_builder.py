"""
Prompt Builder
===============
Assembles prompts with dynamic context injection.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List

from rules.dictionaries.country_groups import COUNTRY_GROUPS

logger = logging.getLogger(__name__)

# ── Cached graph entities context ────────────────────────────────────────────
_graph_entities_cache: Optional[str] = None
_graph_entities_cache_time: float = 0.0
_GRAPH_ENTITIES_TTL = 300  # 5 minutes


def build_graph_entities_context() -> str:
    """Query the RulesGraph for all entity names across 11 types.

    Returns formatted text listing actual graph values for injection into
    agent prompts. Cached for 5 minutes to avoid repeated queries.
    Falls back to empty string if graph is unavailable.
    """
    global _graph_entities_cache, _graph_entities_cache_time

    now = time.time()
    if _graph_entities_cache is not None and (now - _graph_entities_cache_time) < _GRAPH_ENTITIES_TTL:
        return _graph_entities_cache

    try:
        from services.database import get_db_service
        db = get_db_service()
        graph = db.get_rules_graph()

        # Core entity queries
        entity_queries = {
            "Countries": "MATCH (n:Country) RETURN n.name AS name ORDER BY name",
            "Regulators": "MATCH (n:Regulator) RETURN n.name AS name ORDER BY name",
            "Authorities": "MATCH (n:Authority) RETURN n.name AS name ORDER BY name",
            "PurposeOfProcessing": "MATCH (n:PurposeOfProcessing) RETURN n.name AS name ORDER BY name",
            "DataCategory": "MATCH (n:DataCategory) RETURN n.name AS name ORDER BY name",
            "SensitiveDataCategory": "MATCH (n:SensitiveDataCategory) RETURN n.name AS name ORDER BY name",
            "Process": "MATCH (n:Process) RETURN n.name AS name ORDER BY name",
            "GDC": "MATCH (n:GDC) RETURN n.name AS name ORDER BY name",
            "DataSubject": "MATCH (n:DataSubject) RETURN n.name AS name ORDER BY name",
            "LegalEntity": "MATCH (n:LegalEntity) RETURN n.name AS name ORDER BY name",
            "GlobalBusinessFunction": "MATCH (n:GlobalBusinessFunction) RETURN n.name AS name ORDER BY name",
        }

        # Include dynamic node types from schema metadata
        try:
            import os
            schema_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "schema_metadata.json"))
            with open(schema_path, "r") as f:
                schema = json.load(f)
            covered = set(entity_queries.keys()) | {"Rule", "CountryGroup", "Duty", "Action", "Permission", "Prohibition", "Attribute"}
            for nt in schema.get("nodeTypes", []):
                label = nt["label"]
                if label not in covered:
                    entity_queries[label] = f"MATCH (n:{label}) RETURN n.name AS name ORDER BY name"
        except Exception as e:
            logger.debug(f"Could not load dynamic schema for prompt builder: {e}")

        sections = []
        for label, query in entity_queries.items():
            try:
                result = graph.query(query)
                names = [row[0] for row in result.result_set if row[0]]
                if names:
                    # Truncate to 50 items to keep prompt size manageable
                    display = names[:50]
                    suffix = f" ... and {len(names) - 50} more" if len(names) > 50 else ""
                    sections.append(f"**{label}** ({len(names)} total): {', '.join(display)}{suffix}")
            except Exception as e:
                logger.debug(f"Failed to query {label}: {e}")

        _graph_entities_cache = "\n".join(sections) if sections else "(Graph not yet built — no entities available)"
        _graph_entities_cache_time = now
        logger.info(f"Built graph entities context: {len(sections)} entity types")
        return _graph_entities_cache

    except Exception as e:
        logger.warning(f"Could not build graph entities context: {e}")
        _graph_entities_cache = "(Graph not available — entities could not be loaded)"
        _graph_entities_cache_time = now
        return _graph_entities_cache


def build_country_groups_context() -> str:
    """Build a prompt section listing available country groups."""
    lines = []
    for name, countries in COUNTRY_GROUPS.items():
        sample = list(countries)[:5]
        lines.append(f"- {name}: {', '.join(sample)}{'...' if len(countries) > 5 else ''}")
    return "\n".join(lines)


def compress_prompt_for_retry(prompt: str, max_length: int = 4000) -> str:
    """Optionally reduce prompt size for retry iterations.

    Truncates agent output JSON blocks and long sections while preserving
    the structure and key fields needed for decision-making.
    """
    if len(prompt) <= max_length:
        return prompt

    # Find and truncate large JSON blocks (agent_outputs section)
    import re
    json_blocks = list(re.finditer(r'\{[^{}]{500,}\}', prompt, re.DOTALL))
    if json_blocks:
        for match in reversed(json_blocks):
            block = match.group()
            if len(block) > 500:
                # Truncate inner content, keep first/last 200 chars
                truncated = block[:200] + "\n... [truncated for retry] ...\n" + block[-200:]
                prompt = prompt[:match.start()] + truncated + prompt[match.end():]

    # Final truncation if still too long
    if len(prompt) > max_length:
        prompt = prompt[:max_length] + "\n\n[... prompt truncated for retry iteration ...]"

    return prompt


def build_supervisor_prompt(
    template: str,
    rule_text: str,
    origin_country: str,
    scenario_type: str,
    receiving_countries: List[str],
    data_categories: List[str],
    current_phase: str,
    iteration: int,
    max_iterations: int,
    agent_outputs: Dict[str, Any],
    validation_status: str,
    feedback: str,
    graph_step: int = 0,
    agent_retry_counts: Optional[Dict[str, int]] = None,
) -> str:
    """Build a fully-assembled supervisor user prompt."""
    return template.format(
        rule_text=rule_text,
        origin_country=origin_country,
        scenario_type=scenario_type,
        receiving_countries=", ".join(receiving_countries),
        data_categories=", ".join(data_categories) if data_categories else "None",
        current_phase=current_phase,
        iteration=iteration,
        max_iterations=max_iterations,
        graph_step=graph_step,
        agent_retry_counts=json.dumps(agent_retry_counts or {}, default=str),
        agent_outputs=json.dumps(agent_outputs, indent=2, default=str),
        validation_status=validation_status,
        feedback=feedback or "None",
    )


def build_analyzer_prompt(
    template: str,
    rule_text: str,
    origin_country: str,
    receiving_countries: List[str],
    scenario_type: str,
    data_categories: List[str],
    feedback: str,
    is_pii_related: bool = False,
) -> str:
    """Build a fully-assembled analyzer user prompt."""
    return template.format(
        rule_text=rule_text,
        origin_country=origin_country,
        receiving_countries=", ".join(receiving_countries),
        scenario_type=scenario_type,
        data_categories=", ".join(data_categories) if data_categories else "None",
        is_pii_related=str(is_pii_related),
        feedback=feedback or "None",
    )


def build_cypher_prompt(
    template: str,
    rule_definition: Dict[str, Any],
    feedback: str,
    dictionary_result: Optional[Dict[str, Any]] = None,
    origin_country: str = "",
    receiving_countries: Optional[List[str]] = None,
    data_categories: Optional[List[str]] = None,
) -> str:
    """Build a fully-assembled Cypher generator user prompt."""
    return template.format(
        rule_definition=json.dumps(rule_definition, indent=2),
        feedback=feedback or "None",
        dictionary_result=json.dumps(dictionary_result, indent=2) if dictionary_result else "None",
        origin_country=origin_country,
        receiving_countries=", ".join(receiving_countries) if receiving_countries else "None",
        data_categories=", ".join(data_categories) if data_categories else "None",
    )


def build_validator_prompt(
    template: str,
    rule_text: str,
    rule_definition: Dict[str, Any],
    cypher_queries: Dict[str, Any],
    dictionary: Optional[Dict[str, Any]],
    iteration: int,
    max_iterations: int,
    previous_errors: List[str],
) -> str:
    """Build a fully-assembled validator user prompt."""
    previous_errors_str = "\n".join(previous_errors) if previous_errors else "None"
    return template.format(
        rule_text=rule_text,
        rule_definition=json.dumps(rule_definition, indent=2),
        cypher_queries=json.dumps(cypher_queries, indent=2),
        dictionary=json.dumps(dictionary, indent=2) if dictionary else "None",
        iteration=iteration,
        max_iterations=max_iterations,
        previous_errors=f"Previous errors:\n{previous_errors_str}",
    )


def build_dictionary_prompt(
    template: str,
    data_categories: List[str],
    rule_text: str,
    origin_country: str,
    scenario_type: str,
    feedback: str,
    is_pii_related: bool = False,
) -> str:
    """Build a fully-assembled dictionary user prompt."""
    return template.format(
        data_categories=", ".join(data_categories),
        rule_text=rule_text,
        origin_country=origin_country,
        scenario_type=scenario_type,
        is_pii_related=str(is_pii_related),
        feedback=feedback or "None",
    )


def build_tester_prompt(
    template: str,
    rule_definition: Dict[str, Any],
    rule_text: str,
    dictionary_result: Optional[Dict[str, Any]],
    origin_country: str,
    receiving_countries: List[str],
    data_categories: List[str],
) -> str:
    """Build a fully-assembled tester user prompt."""
    return template.format(
        rule_definition=json.dumps(rule_definition, indent=2),
        rule_text=rule_text,
        dictionary_result=json.dumps(dictionary_result, indent=2) if dictionary_result else "None",
        origin_country=origin_country,
        receiving_countries=", ".join(receiving_countries),
        data_categories=", ".join(data_categories) if data_categories else "None",
    )


def build_reference_prompt(
    template: str,
    rule_definition: Dict[str, Any],
    rule_text: str,
    feedback: str,
) -> str:
    """Build a fully-assembled reference data user prompt."""
    existing_groups = list(COUNTRY_GROUPS.keys())
    return template.format(
        rule_definition=json.dumps(rule_definition, indent=2),
        rule_text=rule_text,
        existing_groups=", ".join(existing_groups),
        feedback=feedback or "None",
    )
