"""
Admin Router
=============
Full CRUD for rules, data dictionaries, and country groups.
All mutations go directly to FalkorDB and invalidate cache.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
import io

from services.backup_service import get_backup_service
from services.sandbox_service import get_sandbox_service
from utils.cypher_safety import validate_label, validate_relationship

def _sync_logic_tree_edges(db, rule_id: str, logic_tree: dict):
    # Wipe old graph edges driven by logic tree
    db.execute_rules_query("""
    MATCH (r:Rule {rule_id: $rule_id})-[rel:HAS_DATA_CATEGORY|HAS_PURPOSE|HAS_PROCESS|HAS_REGULATOR|HAS_AUTHORITY|HAS_DATA_SUBJECT|HAS_SENSITIVE_DATA_CATEGORY|HAS_GDC|TRIGGERED_BY_ORIGIN|TRIGGERED_BY_RECEIVING|ORIGINATES_FROM|RECEIVED_IN]->()
    DELETE rel
    """, {"rule_id": rule_id})

    if not logic_tree:
        return

    # Dimensions
    dim_maps = {
        'DataCategory': ('DataCategory', 'HAS_DATA_CATEGORY'),
        'Purpose': ('PurposeOfProcessing', 'HAS_PURPOSE'),
        'Process': ('Process', 'HAS_PROCESS'),
        'Regulator': ('Regulator', 'HAS_REGULATOR'),
        'Authority': ('Authority', 'HAS_AUTHORITY'),
        'DataSubject': ('DataSubject', 'HAS_DATA_SUBJECT'),
        'SensitiveDataCategory': ('SensitiveDataCategory', 'HAS_SENSITIVE_DATA_CATEGORY'),
        'GDC': ('GDC', 'HAS_GDC'),
        'OriginCountry': ('Country', 'ORIGINATES_FROM'),
        'ReceivingCountry': ('Country', 'RECEIVED_IN'),
        'LegalEntity': ('LegalEntity', 'TRIGGERED_BY_ORIGIN')  # Treating all logic_tree LEs as origins for simplicity or just general triggers
    }
    
    # Also collect group bindings separately
    origin_countries = set()
    receiving_countries = set()

    def walk_tree(node):
        if not isinstance(node, dict): return
        if node.get('type') == 'CONDITION':
            dim = node.get('dimension')
            val = node.get('value')
            if not val: return
            
            # Values can be comma separated
            values = [v.strip() for v in val.split(',') if v.strip()]
            
            for v in values:
                if dim == 'OriginCountry':
                    origin_countries.add(v)
                elif dim == 'ReceivingCountry':
                    receiving_countries.add(v)
                
                if dim in dim_maps:
                    label, rel = dim_maps[dim]
                    # Create the physical linkage
                    db.execute_rules_query(f"""
                    MATCH (r:Rule {{rule_id: $rule_id}})
                    MERGE (n:{label} {{name: $val_name}})
                    MERGE (r)-[:{rel}]->(n)
                    """, {"rule_id": rule_id, "val_name": v})
                    
        elif node.get('type') in ['AND', 'OR', 'NOT']:
            for child in node.get('children', []):
                walk_tree(child)

    walk_tree(logic_tree)
    
    # Helper to resolve Origin/Receiving Groups versus Specific Countries
    def link_scopes(scopes, is_origin=True):
        has_groups = False
        for scope in scopes:
            res = db.execute_rules_query("MATCH (g:CountryGroup {name: $name}) RETURN g LIMIT 1", {"name": scope})
            is_group = len(res) > 0
            
            if is_group:
                has_groups = True
                if is_origin:
                    db.execute_rules_query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (g:CountryGroup {name: $name})
                    MERGE (r)-[:TRIGGERED_BY_ORIGIN]->(g)
                    """, {"rule_id": rule_id, "name": scope})
                else:
                    db.execute_rules_query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (g:CountryGroup {name: $name})
                    MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(g)
                    """, {"rule_id": rule_id, "name": scope})
            else:
                if is_origin:
                    db.execute_rules_query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (c:Country {name: $name})
                    MERGE (r)-[:TRIGGERED_BY_ORIGIN]->(c)
                    """, {"rule_id": rule_id, "name": scope})
                else:
                    db.execute_rules_query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (c:Country {name: $name})
                    MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(c)
                    """, {"rule_id": rule_id, "name": scope})

    if origin_countries:
        link_scopes(origin_countries, is_origin=True)
    if receiving_countries:
        link_scopes(receiving_countries, is_origin=False)
from pydantic import BaseModel, field_validator
import pandas as pd
import io
import math
import uuid
from models.schemas import MappingsUpdate

from services.database import get_db_service
from services.cache import get_cache_service
from utils.graph_builder import RulesGraphBuilder, build_rules_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Internal - Admin & Taxonomy"])


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
    logic_tree: Optional[dict] = None
    outcome: Optional[str] = None
    odrl_type: Optional[str] = None
    linked_attributes: Optional[List[str]] = None
    requires_pii: Optional[bool] = None
    valid_until: Optional[str] = None
    required_assessments: Optional[List[str]] = None
    required_actions: Optional[List[str]] = None

    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v):
        """Normalize priority from integer or string to valid string."""
        if v is None:
            return None

        # If already a valid string, return lowercase
        if isinstance(v, str) and v.lower() in ['low', 'medium', 'high']:
            return v.lower()

        # Convert integer to string
        if isinstance(v, int):
            priority_map = {1: 'high', 2: 'medium', 3: 'low'}
            return priority_map.get(v, 'medium')

        # Convert numeric string to text
        if isinstance(v, str) and v.isdigit():
            priority_map = {'1': 'high', '2': 'medium', '3': 'low'}
            return priority_map.get(v, 'medium')

        return 'medium'  # Default fallback

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
    logic_tree: Optional[dict] = None
    valid_until: Optional[str] = None
    required_assessments: Optional[List[str]] = None
    linked_attributes: Optional[List[str]] = None

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

@router.post("/rules/create")
async def create_rule(db=Depends(get_db)):
    """Create a new blank rule in the graph with a generated ID."""
    rule_id = f"RULE_CUSTOM_{uuid.uuid4().hex[:8].upper()}"
    
    query = """
    MERGE (r:Rule {rule_id: $rule_id})
    SET r.name = "New Custom Rule",
        r.description = "",
        r.priority = "medium",
        r.outcome = "permission",
        r.rule_type = "case_matching",
        r.enabled = true,
        r.odrl_type = "Permission",
        r.odrl_action = "transfer",
        r.odrl_target = "Data",
        r.has_pii_required = false,
        r.requires_any_data = false,
        r.requires_personal_data = false,
        r.priority_order = 100,
        r.logic_tree = '{"type":"AND","children":[]}'
    RETURN r.rule_id as rule_id
    """
    try:
        db.execute_rules_query(query, {"rule_id": rule_id})
        invalidate_cache()
        return {"status": "success", "rule_id": rule_id}
    except Exception as e:
        logger.error(f"Error creating custom rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create rule")


@router.get("/rules")
async def list_rules(db=Depends(get_db)):
    """List all rules from the graph."""
    query = """
    MATCH (r:Rule)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg)
    OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(pm:Permission)-[:CAN_HAVE_DUTY]->(d:Duty)
    OPTIONAL MATCH (r)-[:HAS_ATTRIBUTE]->(a:Attribute)
    WITH r,
         collect(DISTINCT og.name) AS origin_scopes,
         collect(DISTINCT rg.name) AS receiving_scopes,
         collect(DISTINCT a.name) AS linked_attributes,
         collect(DISTINCT CASE WHEN d.module IS NOT NULL AND d.module <> 'action' THEN d.module ELSE null END) AS required_assessments,
         collect(DISTINCT CASE WHEN d.module = 'action' THEN d.name ELSE null END) AS required_actions
    RETURN r.rule_id AS rule_id, r.name AS name, r.description AS description,
           r.rule_type AS rule_type, r.priority AS priority, r.outcome AS outcome,
           r.origin_match_type AS origin_match_type, r.receiving_match_type AS receiving_match_type,
           r.enabled AS enabled, r.odrl_type AS odrl_type, r.logic_tree AS logic_tree,
           r.priority_order AS priority_order, r.valid_until AS valid_until, r.has_pii_required AS requires_pii,
           origin_scopes, receiving_scopes, required_assessments, required_actions, linked_attributes
    ORDER BY priority_order
    """
    result = db.execute_rules_query(query)
    return result


@router.get("/rules/template")
async def download_template():
    """Download an empty Excel rules template."""
    columns = [
        "Rule ID", "Rule Name", "Description", "Priority", "Outcome", "Rule Type",
        "Origin Countries", "Receiving Countries", "Required Actions", "Required Assessments",
        "Regulators", "Data Categories", "Purposes", "Processes", "Data Subjects", "Authorities",
        "Valid Until", "Requires PII"
    ]
    df = pd.DataFrame(columns=columns)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rules_template.xlsx"}
    )


@router.get("/rules/export")
async def export_rules(db=Depends(get_db)):
    """Export all rules to an Excel file."""
    results = await list_rules(db)
    rows = []
    for r in results:
        rows.append({
            "Rule ID": r.get("rule_id", ""),
            "Rule Name": r.get("name", ""),
            "Description": r.get("description", ""),
            "Priority": r.get("priority", "medium"),
            "Outcome": r.get("outcome", "permission"),
            "Rule Type": r.get("rule_type", "case_matching"),
            "Origin Countries": ",".join(r.get("origin_scopes") or []),
            "Receiving Countries": ",".join(r.get("receiving_scopes") or []),
            "Required Actions": ",".join(r.get("required_actions") or []),
            "Required Assessments": ",".join(r.get("required_assessments") or []),
            "Attributes": ",".join(r.get("linked_attributes") or []),
            "Valid Until": r.get("valid_until", ""),
            "Requires PII": "TRUE" if r.get("requires_pii") else "FALSE",
            "Logic Tree JSON": r.get("logic_tree", "")
        })
    df = pd.DataFrame(rows)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rules_export.xlsx"}
    )


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str, db=Depends(get_db)):
    """Get a single rule by ID."""
    query = """
    MATCH (r:Rule {rule_id: $rule_id})
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg)
    OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(pm:Permission)-[:CAN_HAVE_DUTY]->(d:Duty)
    OPTIONAL MATCH (r)-[:HAS_ATTRIBUTE]->(a:Attribute)
    RETURN r.rule_id AS rule_id, r.name AS name, r.description AS description,
           r.rule_type AS rule_type, r.priority AS priority, r.outcome AS outcome,
           r.origin_match_type AS origin_match_type, r.receiving_match_type AS receiving_match_type,
           r.enabled AS enabled, r.odrl_type AS odrl_type, r.logic_tree AS logic_tree,
           r.has_pii_required AS requires_pii,
           r.requires_any_data AS requires_any_data,
           r.requires_personal_data AS requires_personal_data,
           r.valid_until AS valid_until,
           collect(DISTINCT og.name) AS origin_scopes,
           collect(DISTINCT rg.name) AS receiving_scopes,
           collect(DISTINCT CASE WHEN d.module IS NOT NULL AND d.module <> 'action' THEN d.module ELSE null END) AS required_assessments,
           collect(DISTINCT CASE WHEN d.module = 'action' THEN d.name ELSE null END) AS required_actions,
           collect(DISTINCT a.name) AS linked_attributes
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
    if update.logic_tree is not None:
        import json
        set_parts.append("r.logic_tree = $logic_tree")
        params["logic_tree"] = json.dumps(update.logic_tree)

    if update.outcome is not None:
        set_parts.append("r.outcome = $outcome")
        params["outcome"] = update.outcome
        # Also sync odrl_type implicitly based on outcome
        if update.odrl_type is not None:
             set_parts.append("r.odrl_type = $odrl_type")
             params["odrl_type"] = update.odrl_type
        else:
             set_parts.append("r.odrl_type = $odrl_type")
             params["odrl_type"] = "Prohibition" if update.outcome == "prohibition" else "Permission"

    if update.requires_pii is not None:
        set_parts.append("r.has_pii_required = $has_pii_required")
        params["has_pii_required"] = update.requires_pii
        
    if update.valid_until is not None:
        # If passed an empty string, set it back to null
        if update.valid_until.strip() == "":
            set_parts.append("r.valid_until = null")
        else:
            set_parts.append("r.valid_until = $valid_until")
            params["valid_until"] = update.valid_until

    if not set_parts and update.linked_attributes is None and update.outcome is None and update.required_assessments is None and update.required_actions is None:
        raise HTTPException(status_code=400, detail="No fields to update")

    if set_parts:
        query = f"MATCH (r:Rule {{rule_id: $rule_id}}) SET {', '.join(set_parts)} RETURN r.rule_id AS rule_id"
        result = db.execute_rules_query(query, params=params)
        if not result:
            raise HTTPException(status_code=404, detail="Rule not found")

    # If logic_tree changed, we must sync the graph schema edges
    if update.logic_tree is not None:
        _sync_logic_tree_edges(db, rule_id, update.logic_tree)

    # If outcome changed, re-map graph edges
    if update.outcome is not None:
        db.execute_rules_query("""
        MATCH (r:Rule {rule_id: $rule_id})-[rel:HAS_PERMISSION|HAS_PROHIBITION]->()
        DELETE rel
        """, params={"rule_id": rule_id})
        
        # We need rule name, let's just MERGE based on rule_id string for simplicity, or we can fetch it.
        if update.outcome == 'prohibition':
            db.execute_rules_query("""
            MATCH (r:Rule {rule_id: $rule_id})
            MERGE (pb:Prohibition {name: r.name})
            MERGE (r)-[:HAS_PROHIBITION]->(pb)
            """, params={"rule_id": rule_id})
        else:
            db.execute_rules_query("""
            MATCH (r:Rule {rule_id: $rule_id})
            MERGE (p:Permission {name: "Transfer Permission (" + r.name + ")"})
            MERGE (r)-[:HAS_PERMISSION]->(p)
            """, params={"rule_id": rule_id})

    # If attributes were provided, map them
    if update.linked_attributes is not None:
        db.execute_rules_query("""
        MATCH (r:Rule {rule_id: $rule_id})-[rel:HAS_ATTRIBUTE]->()
        DELETE rel
        """, params={"rule_id": rule_id})
        
        for attr in update.linked_attributes:
            if attr.strip():
                db.execute_rules_query("""
                MATCH (r:Rule {rule_id: $rule_id})
                MERGE (a:Attribute {name: $attr_name})
                MERGE (r)-[:HAS_ATTRIBUTE]->(a)
                """, params={"rule_id": rule_id, "attr_name": attr.strip()})

    # If assessments or actions were provided, rebuild the duties
    if update.required_assessments is not None or update.required_actions is not None:
        db.execute_rules_query("""
        MATCH (r:Rule {rule_id: $rule_id})-[:HAS_PERMISSION]->(p:Permission)-[rel:CAN_HAVE_DUTY]->(d:Duty)
        DELETE rel
        """, params={"rule_id": rule_id})

        # Find rule and permission 
        rule_data = db.execute_rules_query("MATCH (r:Rule {rule_id: $rule_id}) RETURN r.outcome AS outcome", {"rule_id": rule_id})
        current_outcome = rule_data[0]['outcome'] if rule_data else 'permission'

        if current_outcome != 'prohibition':
            if update.required_assessments is not None:
                for assessment in update.required_assessments:
                    if assessment.strip():
                        assessment_upper = str(assessment).strip().upper()
                        duty_name = f"Complete {assessment_upper} Module"
                        db.execute_rules_query("""
                        MERGE (d:Duty {name: $duty_name, module: $module, value: 'Completed'})
                        WITH d
                        MATCH (r:Rule {rule_id: $rule_id})-[:HAS_PERMISSION]->(p:Permission)
                        MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                        """, params={"duty_name": duty_name, "module": assessment_upper, "rule_id": rule_id})
                        
            if update.required_actions is not None:
                for action in update.required_actions:
                    if action.strip():
                        db.execute_rules_query("""
                        MERGE (d:Duty {name: $action_name, module: 'action', value: 'required'})
                        WITH d
                        MATCH (r:Rule {rule_id: $rule_id})-[:HAS_PERMISSION]->(p:Permission)
                        MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                        """, params={"action_name": action.strip(), "rule_id": rule_id})

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


@router.post("/rules/create-full")
async def create_rule_full(request: RuleUpdate, db=Depends(get_db)):
    """
    Create a fully-configured rule with all properties and graph relationships in one call.
    This combines rule creation with entity mapping, duties, and logic tree synchronization.
    """
    import uuid
    import json

    # Generate new rule ID
    rule_id = f"RULE_CUSTOM_{uuid.uuid4().hex[:8].upper()}"

    # Build rule properties
    rule_props = {
        "rule_id": rule_id,
        "name": request.name or "New Custom Rule",
        "description": request.description or "",
        "priority": request.priority or "medium",
        "outcome": request.outcome or "permission",
        "rule_type": "attribute",
        "enabled": request.enabled if request.enabled is not None else True,
        "odrl_type": "Prohibition" if request.outcome == "prohibition" else "Permission",
        "odrl_action": "transfer",
        "odrl_target": "Data",
        "has_pii_required": request.requires_pii if request.requires_pii is not None else False,
        "requires_any_data": False,
        "requires_personal_data": request.requires_pii if request.requires_pii is not None else False,
        "priority_order": 100
    }

    if request.logic_tree:
        rule_props["logic_tree"] = json.dumps(request.logic_tree)
    else:
        rule_props["logic_tree"] = '{"type":"AND","children":[]}'

    if request.valid_until and request.valid_until.strip():
        rule_props["valid_until"] = request.valid_until

    # Create rule node
    set_parts = [f"r.{k} = ${k}" for k in rule_props.keys()]
    query = f"MERGE (r:Rule {{rule_id: $rule_id}}) SET {', '.join(set_parts)} RETURN r.rule_id as rule_id"

    try:
        result = db.execute_rules_query(query, params=rule_props)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create rule")

        # Sync logic tree to graph edges
        if request.logic_tree:
            _sync_logic_tree_edges(db, rule_id, request.logic_tree)

        # Create Permission/Prohibition node
        if request.outcome == "prohibition":
            db.execute_rules_query("""
            MATCH (r:Rule {rule_id: $rule_id})
            MERGE (pb:Prohibition {name: r.name})
            MERGE (r)-[:HAS_PROHIBITION]->(pb)
            """, params={"rule_id": rule_id})
        else:
            db.execute_rules_query("""
            MATCH (r:Rule {rule_id: $rule_id})
            MERGE (p:Permission {name: "Transfer Permission (" + r.name + ")"})
            MERGE (r)-[:HAS_PERMISSION]->(p)
            """, params={"rule_id": rule_id})

        # Link attributes
        if request.linked_attributes:
            for attr in request.linked_attributes:
                if attr.strip():
                    db.execute_rules_query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MERGE (a:Attribute {name: $attr_name})
                    MERGE (r)-[:HAS_ATTRIBUTE]->(a)
                    """, params={"rule_id": rule_id, "attr_name": attr.strip()})

        # Create duties (assessments and actions)
        if request.outcome != "prohibition":
            if request.required_assessments:
                for assessment in request.required_assessments:
                    if assessment.strip():
                        assessment_upper = str(assessment).strip().upper()
                        duty_name = f"Complete {assessment_upper} Module"
                        db.execute_rules_query("""
                        MERGE (d:Duty {name: $duty_name, module: $module, value: 'Completed'})
                        WITH d
                        MATCH (r:Rule {rule_id: $rule_id})-[:HAS_PERMISSION]->(p:Permission)
                        MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                        """, params={"duty_name": duty_name, "module": assessment_upper, "rule_id": rule_id})

            if request.required_actions:
                for action in request.required_actions:
                    if action.strip():
                        db.execute_rules_query("""
                        MERGE (d:Duty {name: $action_name, module: 'action', value: 'required'})
                        WITH d
                        MATCH (r:Rule {rule_id: $rule_id})-[:HAS_PERMISSION]->(p:Permission)
                        MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                        """, params={"action_name": action.strip(), "rule_id": rule_id})

        invalidate_cache()
        return {"status": "created", "rule_id": rule_id}

    except Exception as e:
        logger.error(f"Error creating full rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create rule: {str(e)}")


@router.post("/rules/test")
async def test_rule(request: dict, db=Depends(get_db)):
    """
    Test a rule definition against a scenario without saving to graph.
    Creates temporary sandbox graph, loads rule, evaluates, and cleans up.
    """
    from services.sandbox_service import SandboxService
    from services.rules_evaluator import RulesEvaluator

    rule_def = request.get("rule_def")
    test_scenario = request.get("test_scenario")

    if not rule_def or not test_scenario:
        raise HTTPException(status_code=400, detail="Missing rule_def or test_scenario")

    try:
        # Create temporary sandbox graph
        sandbox = get_sandbox_service()
        graph_name = sandbox.create_sandbox("test_session")

        # Load rule into sandbox
        success = sandbox.add_rule_to_sandbox(graph_name, rule_def)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to load rule into sandbox")

        # Run evaluator
        temp_graph = db.db.select_graph(graph_name)
        evaluator = RulesEvaluator(rules_graph=temp_graph)

        result = evaluator.evaluate(
            origin_country=test_scenario.get("origin_country"),
            receiving_country=test_scenario.get("receiving_country"),
            pii=test_scenario.get("pii", False),
            purposes=test_scenario.get("purposes", []),
            data_categories=test_scenario.get("data_categories", []),
            processes=test_scenario.get("processes", []),
            regulators=test_scenario.get("regulators", []),
            authorities=test_scenario.get("authorities", []),
            data_subjects=test_scenario.get("data_subjects", [])
        )

        # Cleanup sandbox
        sandbox.cleanup_sandbox(graph_name)

        # Check if rule matched
        rule_matched = rule_def.get("rule_id") in [r.rule_id for r in result.triggered_rules]

        return {
            "matched": rule_matched,
            "evaluation_result": result.model_dump() if hasattr(result, 'model_dump') else result
        }

    except Exception as e:
        logger.error(f"Error testing rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test rule: {str(e)}")


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, db=Depends(get_db)):
    """Delete a rule and its relationships."""
    query = "MATCH (r:Rule {rule_id: $rule_id}) DETACH DELETE r"
    db.execute_rules_query(query, params={"rule_id": rule_id})
    invalidate_cache()
    return {"status": "deleted", "rule_id": rule_id}


@router.post("/rules/bulk-insert")
async def bulk_create_rules(rules: List[RuleCreate], db=Depends(get_db)):
    """Bulk create multiple rules via the graph builder."""
    builder = RulesGraphBuilder()
    success_count = 0
    for rule in rules:
        if builder.add_rule(rule.model_dump()):
            success_count += 1
    
    if success_count > 0:
        invalidate_cache()
    
    return {"status": "success", "inserted": success_count, "total": len(rules)}


@router.post("/rules/parse-excel")
async def parse_excel(file: UploadFile = File(...)):
    """Parse a flexible Excel rules template and generate structural Logic Trees for UI review."""
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(400, "File must be an Excel or CSV file")
        
    try:
        content = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
            
        # Clean col names
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        parsed_rules = []
        for idx, row in df.iterrows():
            def val(col_names):
                for c in col_names:
                    if c in df.columns:
                        v = row[c]
                        if pd.isna(v): return ""
                        return str(v).strip()
                return ""
            
            rule_id = val(['rule id', 'rule_id', 'id']) or f"RULE_{uuid.uuid4().hex[:8].upper()}"
            name = val(['rule name', 'name', 'title']) or f"Imported Rule {idx+1}"
            desc = val(['description', 'desc', 'summary'])
            r_type = val(['rule type', 'type']) or 'attribute'
            outcome = val(['outcome', 'action']).lower() or 'permission'
            priority = val(['priority', 'severity']).lower() or 'medium'
            
            required_actions = [x.strip() for x in val(['required actions', 'actions', 'duties']).split(',') if x.strip()]
            
            # Entities
            regulators = [x.strip() for x in val(['regulators', 'required regulators']).split(',') if x.strip()]
            data_cats = [x.strip() for x in val(['data categories', 'categories']).split(',') if x.strip()]
            purposes = [x.strip() for x in val(['purposes', 'purpose of processing']).split(',') if x.strip()]
            processes = [x.strip() for x in val(['processes']).split(',') if x.strip()]
            data_subs = [x.strip() for x in val(['data subjects']).split(',') if x.strip()]
            authorities = [x.strip() for x in val(['authorities', 'supervisory authorities']).split(',') if x.strip()]
            
            # Additional export columns
            origin_countries = [x.strip() for x in val(['origin countries', 'origin_countries', 'origin']).split(',') if x.strip()]
            receiving_countries = [x.strip() for x in val(['receiving countries', 'receiving_countries', 'receiving']).split(',') if x.strip()]
            valid_until = val(['valid until', 'valid_until']) or None
            requires_pii_val = val(['requires pii', 'requires_pii']).lower()
            requires_pii = requires_pii_val in ['true', 'yes', '1', 'y']
            required_assessments = [x.strip() for x in val(['required assessments', 'assessments']).split(',') if x.strip()]
            linked_attributes = [x.strip() for x in val(['attributes', 'linked attributes', 'linked_attributes']).split(',') if x.strip()]
            
            # Build Logic Tree (auto-assemble all parsed columns into an AND tree)
            children = []
            for r in regulators: children.append({"type": "CONDITION", "dimension": "Regulator", "value": r})
            for c in data_cats: children.append({"type": "CONDITION", "dimension": "DataCategory", "value": c})
            for p in purposes: children.append({"type": "CONDITION", "dimension": "Purpose", "value": p})
            for pr in processes: children.append({"type": "CONDITION", "dimension": "Process", "value": pr})
            for ds in data_subs: children.append({"type": "CONDITION", "dimension": "DataSubject", "value": ds})
            for a in authorities: children.append({"type": "CONDITION", "dimension": "Authority", "value": a})
            
            logic_tree_json_str = val(['logic tree json', 'logic_tree_json', 'logic tree'])
            logic_tree = None
            if logic_tree_json_str:
                import json
                try:
                    logic_tree = json.loads(logic_tree_json_str)
                except Exception:
                    pass
            elif children:
                logic_tree = {
                    "type": "AND",
                    "children": children
                }
                
            parsed_rules.append(RuleCreate(
                rule_id=rule_id,
                name=name,
                description=desc,
                rule_type=r_type,
                outcome=outcome,
                priority=priority,
                required_actions=required_actions,
                logic_tree=logic_tree,
                origin_countries=origin_countries,
                receiving_countries=receiving_countries,
                valid_until=valid_until,
                requires_pii=requires_pii,
                required_assessments=required_assessments,
                linked_attributes=linked_attributes
            ))
            
        return {"status": "success", "rules": [r.model_dump() for r in parsed_rules]}
        
    except Exception as e:
        logger.error(f"Excel parsing failed: {e}")
        raise HTTPException(500, f"Failed to parse file: {str(e)}")


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
    "countries": "Country",
    "country_groups": "CountryGroup",
    "legal_entities": "LegalEntity",
    "data_categories": "DataCategory",
    "sensitive_data_categories": "SensitiveDataCategory",
    "regulators": "Regulator",
    "authorities": "Authority",
    "global_business_functions": "GlobalBusinessFunction"
}


@router.get("/dictionaries/{dict_type}")
async def list_dictionary_entries(dict_type: str, db=Depends(get_db)):
    """List entries for a data dictionary type."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")

    # Validate label to prevent injection
    try:
        validated_label = validate_label(node_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid node type: {e}")

    query = f"MATCH (n:{validated_label}) RETURN n.name AS name, n.category AS category ORDER BY n.category, n.name"
    return db.execute_rules_query(query)


@router.post("/dictionaries/{dict_type}")
async def add_dictionary_entry(dict_type: str, entry: DictionaryEntryCreate, db=Depends(get_db)):
    """Add an entry to a data dictionary."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")

    # Validate label to prevent injection
    try:
        validated_label = validate_label(node_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid node type: {e}")

    query = f"MERGE (n:{validated_label} {{name: $name}}) SET n.category = $category"
    db.execute_rules_query(query, params={"name": entry.name, "category": entry.category})
    invalidate_cache()
    return {"status": "created", "type": dict_type, "name": entry.name}


@router.delete("/dictionaries/{dict_type}/{name}")
async def delete_dictionary_entry(dict_type: str, name: str, db=Depends(get_db)):
    """Remove an entry from a data dictionary."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")

    # Validate label to prevent injection
    try:
        validated_label = validate_label(node_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid node type: {e}")

    query = f"MATCH (n:{validated_label} {{name: $name}}) DETACH DELETE n"
    db.execute_rules_query(query, params={"name": name})
    invalidate_cache()
    return {"status": "deleted", "type": dict_type, "name": name}

@router.post("/dictionaries/{dict_type}/upload")
async def upload_dictionary_csv(dict_type: str, file: UploadFile = File(...), db=Depends(get_db)):
    """Upload a CSV to bulk insert dictionary entities."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")
    
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
        df = df.fillna("")
        records = df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")
        
    # Validate label to prevent injection
    try:
        validated_label = validate_label(node_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid node type: {e}")

    from utils.cypher_safety import validate_property_name

    for record in records:
        key_field = 'id' if 'id' in record else 'name'
        if not key_field in record: continue

        # Validate all property names to prevent injection
        try:
            validated_key = validate_property_name(key_field)
            validated_props = {validate_property_name(k): v for k, v in record.items() if k != key_field}
        except ValueError as e:
            logger.warning(f"Skipping record with invalid property name: {e}")
            continue

        props_str = ", ".join([f"n.{k} = ${k}" for k in validated_props.keys()])
        query = f"MERGE (n:{validated_label} {{{validated_key}: ${validated_key}}})"
        if props_str:
            query += f" SET {props_str}"

        params = {validated_key: record[key_field], **validated_props}
        db.execute_rules_query(query, params=params)
        
    invalidate_cache()
    return {"status": "success", "inserted": len(records), "type": dict_type}

@router.get("/dictionaries/{dict_type}/template")
async def download_dictionary_template(dict_type: str):
    """Download a simple sample CSV template for the dictionary."""
    node_type = DICT_TYPE_MAP.get(dict_type)
    if not node_type:
        raise HTTPException(status_code=400, detail=f"Invalid dictionary type: {dict_type}")
    
    # Generic generic template headers
    if dict_type == "countries":
        df = pd.DataFrame(columns=["name", "code", "region"])
    elif dict_type == "legal_entities":
        df = pd.DataFrame(columns=["name", "category"]) # category often empty
    else:
        df = pd.DataFrame(columns=["name", "category", "description"])
        
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={dict_type}_sample.csv"}
    )

@router.get("/mappings/{mapping_type}")
async def get_mappings(mapping_type: str, db=Depends(get_db)):
    """Get existing mappings for a given type."""
    if mapping_type == "country-group":
        query = "MATCH (c:Country)-[:BELONGS_TO]->(g:CountryGroup) RETURN g.name AS source, collect(c.name) AS targets"
    elif mapping_type == "legal-entity":
        query = "MATCH (c:Country)-[:HAS_LEGAL_ENTITY]->(l:LegalEntity) RETURN c.name AS source, collect(l.name) AS targets"
    else:
        raise HTTPException(status_code=400, detail="Unknown mapping type")
    
    res = db.execute_rules_query(query)
    return {"mappings": res}

@router.post("/mappings/{mapping_type}")
async def update_mappings(mapping_type: str, mapping: MappingsUpdate, db=Depends(get_db)):
    """Update mappings for a destination entity."""
    if mapping_type == "country-group":
        rel = "BELONGS_TO"
        dest_label = "CountryGroup"

        # Validate labels and relationships to prevent injection
        try:
            validated_dest = validate_label(dest_label)
            validated_rel = validate_relationship(rel)
            validated_country = validate_label("Country")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid label or relationship: {e}")

        db.execute_rules_query(f"MERGE (d:{validated_dest} {{name: $dest_name}})", params={"dest_name": mapping.source_id})
        db.execute_rules_query(
            f"MATCH (c:{validated_country})-[r:{validated_rel}]->(d:{validated_dest} {{name: $dest_name}}) DELETE r",
            params={"dest_name": mapping.source_id}
        )
        for target in mapping.target_ids:
            query = f"""
            MATCH (c:{validated_country} {{name: $target_name}})
            MATCH (d:{validated_dest} {{name: $dest_name}})
            MERGE (c)-[:{validated_rel}]->(d)
            """
            db.execute_rules_query(query, params={"dest_name": mapping.source_id, "target_name": target})

    elif mapping_type == "legal-entity":
        rel = "HAS_LEGAL_ENTITY"
        dest_label = "Country"

        # Validate labels and relationships to prevent injection
        try:
            validated_dest = validate_label(dest_label)
            validated_rel = validate_relationship(rel)
            validated_legal = validate_label("LegalEntity")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid label or relationship: {e}")

        # source_id is the Country, target_ids are the Legal Entities
        db.execute_rules_query(f"MERGE (d:{validated_dest} {{name: $dest_name}})", params={"dest_name": mapping.source_id})
        db.execute_rules_query(
            f"MATCH (d:{validated_dest} {{name: $dest_name}})-[r:{validated_rel}]->(l:{validated_legal}) DELETE r",
            params={"dest_name": mapping.source_id}
        )
        for target in mapping.target_ids:
            query = f"""
            MATCH (d:{validated_dest} {{name: $dest_name}})
            MERGE (l:{validated_legal} {{name: $target_name}})
            MERGE (d)-[:{validated_rel}]->(l)
            """
            db.execute_rules_query(query, params={"dest_name": mapping.source_id, "target_name": target})
    else:
        raise HTTPException(status_code=400, detail="Unknown mapping type")

    invalidate_cache()
    return {"status": "success"}


# ── Graph Operations ──────────────────────────────────────────────────

@router.post("/backup/create")
async def create_backup():
    """Manually trigger a full graph backup to disk."""
    try:
        backup = get_backup_service()
        data = backup.create_backup()
        return {
            "status": "success", 
            "message": "Backup created successfully", 
            "node_count": len(data["nodes"]), 
            "edge_count": len(data["edges"])
        }
    except Exception as e:
        logger.error(f"Manual backup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backup/restore")
async def restore_backup():
    """Restore the rules graph from the latest disk backup."""
    try:
        backup = get_backup_service()
        backup.restore_backup()
        invalidate_cache()
        return {"status": "success", "message": "Backup restored successfully"}
    except Exception as e:
        logger.error(f"Manual restore failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
