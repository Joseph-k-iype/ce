"""
Admin Router
=============
Full CRUD for rules, data dictionaries, and country groups.
All mutations go directly to FalkorDB and invalidate cache.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.database import get_db_service
from services.cache import get_cache_service
from utils.graph_builder import RulesGraphBuilder, build_rules_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_db():
    return get_db_service()


def invalidate_cache():
    cache = get_cache_service()
    cache.clear()


# ── Pydantic models ────────────────────────────────────────────────────

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    enabled: Optional[bool] = None

class RuleCreate(BaseModel):
    rule_id: str
    name: str
    description: str = ""
    rule_type: str = "case_matching"
    priority: str = "medium"
    outcome: str = "permission"
    origin_group: Optional[str] = None
    origin_countries: Optional[List[str]] = None
    receiving_group: Optional[str] = None
    receiving_countries: Optional[List[str]] = None
    odrl_type: str = "Permission"
    odrl_action: str = "transfer"
    odrl_target: str = "Data"
    requires_pii: bool = False
    requires_any_data: bool = False
    requires_personal_data: bool = False
    required_actions: List[str] = []

class CountryGroupUpdate(BaseModel):
    add_countries: List[str] = []
    remove_countries: List[str] = []

class CountryGroupCreate(BaseModel):
    name: str
    countries: List[str]

class DictionaryEntryCreate(BaseModel):
    name: str
    category: str = ""


# ── Rules CRUD ─────────────────────────────────────────────────────────

@router.get("/rules")
async def list_rules(db=Depends(get_db)):
    """List all rules from the graph."""
    query = """
    MATCH (r:Rule)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg)
    OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(pm:Permission)-[:CAN_HAVE_DUTY]->(d:Duty)
    RETURN r.rule_id AS rule_id, r.name AS name, r.description AS description,
           r.rule_type AS rule_type, r.priority AS priority, r.outcome AS outcome,
           r.origin_match_type AS origin_match_type, r.receiving_match_type AS receiving_match_type,
           r.enabled AS enabled, r.odrl_type AS odrl_type,
           collect(DISTINCT og.name) AS origin_scopes,
           collect(DISTINCT rg.name) AS receiving_scopes,
           collect(DISTINCT d.module) AS required_assessments
    ORDER BY r.priority_order
    """
    result = db.execute_rules_query(query)
    return result


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str, db=Depends(get_db)):
    """Get a single rule by ID."""
    query = """
    MATCH (r:Rule {rule_id: $rule_id})
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg)
    OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(pm:Permission)-[:CAN_HAVE_DUTY]->(d:Duty)
    RETURN r.rule_id AS rule_id, r.name AS name, r.description AS description,
           r.rule_type AS rule_type, r.priority AS priority, r.outcome AS outcome,
           r.origin_match_type AS origin_match_type, r.receiving_match_type AS receiving_match_type,
           r.enabled AS enabled, r.odrl_type AS odrl_type,
           r.has_pii_required AS requires_pii,
           r.requires_any_data AS requires_any_data,
           r.requires_personal_data AS requires_personal_data,
           collect(DISTINCT og.name) AS origin_scopes,
           collect(DISTINCT rg.name) AS receiving_scopes,
           collect(DISTINCT d.module) AS required_assessments
    """
    result = db.execute_rules_query(query, params={"rule_id": rule_id})
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")
    return result[0]


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, update: RuleUpdate, db=Depends(get_db)):
    """Update rule properties."""
    set_parts = []
    params = {"rule_id": rule_id}

    if update.name is not None:
        set_parts.append("r.name = $name")
        params["name"] = update.name
    if update.description is not None:
        set_parts.append("r.description = $description")
        params["description"] = update.description
    if update.priority is not None:
        set_parts.append("r.priority = $priority")
        params["priority"] = update.priority
    if update.enabled is not None:
        set_parts.append("r.enabled = $enabled")
        params["enabled"] = update.enabled

    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"MATCH (r:Rule {{rule_id: $rule_id}}) SET {', '.join(set_parts)} RETURN r.rule_id AS rule_id"
    result = db.execute_rules_query(query, params=params)
    if not result:
        raise HTTPException(status_code=404, detail="Rule not found")
    invalidate_cache()
    return {"status": "updated", "rule_id": rule_id}


@router.post("/rules")
async def create_rule(rule: RuleCreate, db=Depends(get_db)):
    """Create a new rule via the graph builder."""
    builder = RulesGraphBuilder()
    success = builder.add_rule(rule.model_dump())
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create rule")
    invalidate_cache()
    return {"status": "created", "rule_id": rule.rule_id}


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, db=Depends(get_db)):
    """Delete a rule and its relationships."""
    query = "MATCH (r:Rule {rule_id: $rule_id}) DETACH DELETE r"
    db.execute_rules_query(query, params={"rule_id": rule_id})
    invalidate_cache()
    return {"status": "deleted", "rule_id": rule_id}


# ── Country Groups CRUD ───────────────────────────────────────────────

@router.get("/country-groups")
async def list_country_groups(db=Depends(get_db)):
    """List all country groups with their countries."""
    query = """
    MATCH (g:CountryGroup)
    OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(g)
    RETURN g.name AS name, collect(c.name) AS countries
    ORDER BY g.name
    """
    return db.execute_rules_query(query)


@router.put("/country-groups/{name}")
async def update_country_group(name: str, update: CountryGroupUpdate, db=Depends(get_db)):
    """Add or remove countries from a group."""
    for country in update.add_countries:
        db.execute_rules_query(
            "MERGE (c:Country {name: $country}) "
            "WITH c MATCH (g:CountryGroup {name: $group}) "
            "MERGE (c)-[:BELONGS_TO]->(g)",
            params={"country": country, "group": name}
        )
    for country in update.remove_countries:
        db.execute_rules_query(
            "MATCH (c:Country {name: $country})-[rel:BELONGS_TO]->(g:CountryGroup {name: $group}) DELETE rel",
            params={"country": country, "group": name}
        )
    invalidate_cache()
    return {"status": "updated", "name": name}


@router.post("/country-groups")
async def create_country_group(group: CountryGroupCreate, db=Depends(get_db)):
    """Create a new country group."""
    db.execute_rules_query("CREATE (g:CountryGroup {name: $name})", params={"name": group.name})
    for country in group.countries:
        db.execute_rules_query(
            "MERGE (c:Country {name: $country}) "
            "WITH c MATCH (g:CountryGroup {name: $group}) "
            "MERGE (c)-[:BELONGS_TO]->(g)",
            params={"country": country, "group": group.name}
        )
    invalidate_cache()
    return {"status": "created", "name": group.name}


@router.delete("/country-groups/{name}")
async def delete_country_group(name: str, db=Depends(get_db)):
    """Delete a country group."""
    db.execute_rules_query("MATCH (g:CountryGroup {name: $name}) DETACH DELETE g", params={"name": name})
    invalidate_cache()
    return {"status": "deleted", "name": name}


# ── Data Dictionary CRUD ──────────────────────────────────────────────

DICT_TYPE_MAP = {
    "processes": "Process",
    "purposes": "Purpose",
    "data_subjects": "DataSubject",
    "gdc": "GDC",
}


@router.get("/dictionaries/{dict_type}")
async def list_dictionary_entries(dict_type: str, db=Depends(get_db)):
    """List entries for a data dictionary type."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")
    query = f"MATCH (n:{node_type}) RETURN n.name AS name, n.category AS category ORDER BY n.category, n.name"
    return db.execute_rules_query(query)


@router.post("/dictionaries/{dict_type}")
async def add_dictionary_entry(dict_type: str, entry: DictionaryEntryCreate, db=Depends(get_db)):
    """Add an entry to a data dictionary."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")
    query = f"MERGE (n:{node_type} {{name: $name}}) SET n.category = $category"
    db.execute_rules_query(query, params={"name": entry.name, "category": entry.category})
    invalidate_cache()
    return {"status": "created", "type": dict_type, "name": entry.name}


@router.delete("/dictionaries/{dict_type}/{name}")
async def delete_dictionary_entry(dict_type: str, name: str, db=Depends(get_db)):
    """Remove an entry from a data dictionary."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")
    query = f"MATCH (n:{node_type} {{name: $name}}) DETACH DELETE n"
    db.execute_rules_query(query, params={"name": name})
    invalidate_cache()
    return {"status": "deleted", "type": dict_type, "name": name}


# ── Graph Operations ──────────────────────────────────────────────────

@router.post("/rebuild-graph")
async def rebuild_graph():
    """Rebuild the entire rules graph from definitions."""
    try:
        build_rules_graph(clear_existing=True)
        invalidate_cache()
        return {"status": "success", "message": "Graph rebuilt successfully"}
    except Exception as e:
        logger.error(f"Graph rebuild failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph-stats")
async def get_graph_stats(db=Depends(get_db)):
    """Get graph statistics."""
    from config.settings import settings
    stats = db.get_graph_stats(settings.database.rules_graph_name)
    return stats
