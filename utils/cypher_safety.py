"""
Cypher Query Safety Utilities

This module provides utilities for safely constructing Cypher queries
to prevent injection attacks.
"""

from typing import Set, Dict, Any, Tuple
import re


# Whitelist of allowed node labels
ALLOWED_LABELS: Set[str] = {
    "Rule",
    "DataCategory",
    "SensitiveDataCategory",
    "Purpose",
    "Process",
    "Regulator",
    "Authority",
    "DataSubject",
    "GDC",
    "Country",
    "CountryGroup",
    "LegalEntity",
    "Permission",
    "Prohibition",
}

# Whitelist of allowed relationship types
ALLOWED_RELATIONSHIPS: Set[str] = {
    "HAS_PERMISSION",
    "HAS_PROHIBITION",
    "BELONGS_TO",
    "HAS_LEGAL_ENTITY",
    "REQUIRES",
    "ALLOWS",
    "PROHIBITS",
    "LINKS_TO",
}


def validate_label(label: str) -> str:
    """
    Validate and sanitize a node label against whitelist.

    Args:
        label: The label to validate

    Returns:
        The validated label

    Raises:
        ValueError: If the label is not in the whitelist
    """
    if label not in ALLOWED_LABELS:
        raise ValueError(f"Invalid node label: {label}")
    return label


def validate_relationship(rel_type: str) -> str:
    """
    Validate and sanitize a relationship type against whitelist.

    Args:
        rel_type: The relationship type to validate

    Returns:
        The validated relationship type

    Raises:
        ValueError: If the relationship type is not in the whitelist
    """
    if rel_type not in ALLOWED_RELATIONSHIPS:
        raise ValueError(f"Invalid relationship type: {rel_type}")
    return rel_type


def validate_property_name(prop_name: str) -> str:
    """
    Validate a property name to ensure it only contains safe characters.

    Args:
        prop_name: The property name to validate

    Returns:
        The validated property name

    Raises:
        ValueError: If the property name contains invalid characters
    """
    # Only allow alphanumeric characters and underscores
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', prop_name):
        raise ValueError(f"Invalid property name: {prop_name}")

    # Prevent property names that are too long
    if len(prop_name) > 64:
        raise ValueError(f"Property name too long: {prop_name}")

    return prop_name


def build_node_match(label: str, properties: Dict[str, str]) -> Tuple[str, Dict[str, Any]]:
    """
    Build a safe MATCH clause for a node with properties.

    Args:
        label: The node label (will be validated)
        properties: Dictionary of property names to parameter names

    Returns:
        Tuple of (cypher_pattern, params_dict)

    Example:
        pattern, params = build_node_match("Rule", {"rule_id": "$rule_id"})
        # Returns: ("(n:Rule {rule_id: $rule_id})", {})
    """
    validated_label = validate_label(label)

    if not properties:
        return f"(n:{validated_label})", {}

    # Build property pattern
    prop_parts = []
    for prop_name, param_ref in properties.items():
        validated_prop = validate_property_name(prop_name)
        prop_parts.append(f"{validated_prop}: {param_ref}")

    pattern = f"(n:{validated_label} {{{', '.join(prop_parts)}}})"
    return pattern, {}


def build_merge_node(label: str, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Build a safe MERGE clause for creating/matching a node.

    Args:
        label: The node label (will be validated)
        params: Dictionary of property values to merge on

    Returns:
        Tuple of (cypher_query, params_dict)

    Example:
        query, params = build_merge_node("Rule", {"rule_id": "R123"})
        # Returns: ("MERGE (n:Rule {rule_id: $rule_id})", {"rule_id": "R123"})
    """
    validated_label = validate_label(label)

    if not params:
        raise ValueError("MERGE requires at least one property")

    # Build property pattern using parameters
    prop_parts = []
    param_dict = {}
    for prop_name, prop_value in params.items():
        validated_prop = validate_property_name(prop_name)
        param_name = f"{validated_prop}"
        prop_parts.append(f"{validated_prop}: ${param_name}")
        param_dict[param_name] = prop_value

    query = f"MERGE (n:{validated_label} {{{', '.join(prop_parts)}}})"
    return query, param_dict


def build_create_index(label: str, property_name: str) -> Tuple[str, Dict[str, Any]]:
    """
    Build a safe CREATE INDEX statement.

    Note: Cypher doesn't support parameterized index creation, so we validate
    the label and property name against whitelists.

    Args:
        label: The node label (will be validated)
        property_name: The property to index (will be validated)

    Returns:
        Tuple of (cypher_query, empty_params_dict)

    Example:
        query, params = build_create_index("Rule", "name")
        # Returns: ("CREATE INDEX FOR (n:Rule) ON (n.name)", {})
    """
    validated_label = validate_label(label)
    validated_prop = validate_property_name(property_name)

    query = f"CREATE INDEX FOR (n:{validated_label}) ON (n.{validated_prop})"
    return query, {}
