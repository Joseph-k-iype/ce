"""
Schema Manager Utility
======================
Handles loading and saving of graph schema metadata from config/schema_metadata.json.
Provides shared access to node type maps, lane definitions, and relationship types.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "schema_metadata.json")
_schema_cache: dict | None = None


def load_schema() -> dict:
    """Load schema metadata from config file with in-memory caching."""
    global _schema_cache
    if _schema_cache is not None:
        return _schema_cache
    
    path = os.path.normpath(_SCHEMA_PATH)
    if not os.path.exists(path):
        logger.error(f"Schema metadata file not found at {path}")
        return {"nodeTypes": [], "lanes": [], "relationshipTypes": []}
        
    with open(path, "r") as f:
        _schema_cache = json.load(f)
    return _schema_cache


def save_schema(schema: dict) -> None:
    """Persist schema metadata to config file and invalidate cache."""
    global _schema_cache
    path = os.path.normpath(_SCHEMA_PATH)
    with open(path, "w") as f:
        json.dump(schema, f, indent=2)
    _schema_cache = schema


def invalidate_schema_cache() -> None:
    """Force reload of schema on next call to load_schema()."""
    global _schema_cache
    _schema_cache = None


def get_lane_map() -> dict[str, str]:
    """Build label → laneId map from schema metadata."""
    schema = load_schema()
    return {nt["label"]: nt["laneId"] for nt in schema.get("nodeTypes", [])}


def get_node_type_map() -> dict[str, str]:
    """Build label → reactFlowType map from schema metadata."""
    schema = load_schema()
    return {nt["label"]: nt["reactFlowType"] for nt in schema.get("nodeTypes", [])}


def get_all_lanes() -> list[dict]:
    """Return all defined lanes sorted by order."""
    schema = load_schema()
    return sorted(schema.get("lanes", []), key=lambda l: l.get("order", 0))


def get_relationship_types() -> list[dict]:
    """Return all relationship types."""
    schema = load_schema()
    return schema.get("relationshipTypes", [])


def get_protected_relationships() -> set[str]:
    """Return relationship types that cannot be manually deleted."""
    schema = load_schema()
    return {rt["type"] for rt in schema.get("relationshipTypes", []) if rt.get("protected")}


def get_lane_for_label(label: str) -> str:
    """Get the lane ID for a given graph label."""
    # Special cases
    if label == "CountryGroup":
        return "originCountry"
    
    lane_map = get_lane_map()
    return lane_map.get(label, "extra")


def get_rf_type_for_label(label: str) -> str:
    """Get the React Flow node type for a given graph label."""
    type_map = get_node_type_map()
    return type_map.get(label, "caseModuleNode")
