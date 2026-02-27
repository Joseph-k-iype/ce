"""
Rules Overview Router
======================
Endpoints for rules overview - table-friendly data for homepage.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query

from models.schemas import (
    RulesOverviewResponse, RulesOverviewTableResponse,
    RuleOverview, RuleTableRow,
)
from services.database import get_db_service
from services.cache import get_cache_service
from rules.dictionaries.rules_definitions import (
    get_enabled_case_matching_rules,
    get_enabled_transfer_rules,
    get_enabled_attribute_rules,
)
from rules.dictionaries.country_groups import COUNTRY_GROUPS, get_all_countries
from rules.templates.cypher_templates import list_templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["External - Rules Data"])


def get_db():
    return get_db_service()


@router.get("/rules-overview-table")
async def get_rules_overview_table(
    db=Depends(get_db),
    search: Optional[str] = Query(None, description="Global search across all columns"),
    risk: Optional[str] = Query(None, description="Filter by risk level: high, medium, low"),
    duty: Optional[str] = Query(None, description="Filter by duty name"),
    group_data_category: Optional[str] = Query(None, description="Filter by group data category"),
    purpose: Optional[str] = Query(None, description="Filter by purpose of processing"),
    process: Optional[str] = Query(None, description="Filter by process"),
    country: Optional[str] = Query(None, description="Filter by country"),
):
    """Get rules overview as table-friendly data for homepage.
    Returns rows with sending/receiving country, rule name, details, permission/prohibition, duty.
    """
    cache = get_cache_service()

    # Build rows from rules graph
    try:
        query = """
        MATCH (r:Rule)
        WHERE r.enabled = true
        OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(oc:Country)
        OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rc:Country)
        OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(p:Permission)-[:CAN_HAVE_DUTY]->(d:Duty)
        OPTIONAL MATCH (r)-[:HAS_PROHIBITION]->(pb:Prohibition)
        RETURN
            r.rule_id AS rule_id,
            r.name AS name,
            r.description AS description,
            r.logic_tree AS logic_tree,
            r.priority AS priority,
            r.outcome AS outcome,
            r.odrl_type AS odrl_type,
            r.origin_match_type AS origin_match_type,
            r.receiving_match_type AS receiving_match_type,
            collect(DISTINCT oc.name) AS origin_names,
            collect(DISTINCT rc.name) AS receiving_names,
            collect(DISTINCT d.name) AS duties,
            collect(DISTINCT pb.name) AS prohibitions,
            r.priority AS sort_priority
        ORDER BY sort_priority
        """
        raw_rows = db.execute_rules_query(query)
    except Exception as e:
        logger.warning(f"Error querying rules graph: {e}")
        raw_rows = []

    # Fallback: if graph query returns empty, build rows from predefined rules
    if not raw_rows:
        case_rules = get_enabled_case_matching_rules()
        for rule_key, rule in case_rules.items():
            origin = rule.origin_group or (", ".join(sorted(rule.origin_countries)[:3]) if rule.origin_countries else "Any")
            receiving = rule.receiving_group or (", ".join(sorted(rule.receiving_countries)[:3]) if rule.receiving_countries else "Any")
            if rule.receiving_not_in:
                receiving = f"Not in {', '.join(rule.receiving_not_in)}"
            duties = rule.required_assessments.to_list()
            raw_rows.append({
                'rule_id': rule.rule_id,
                'name': rule.name,
                'description': rule.description,
                'priority': rule.priority,
                'outcome': 'permission',
                'origin_names': [origin],
                'receiving_names': [receiving],
                'duties': [f"Complete {a} Module" for a in duties],
                'prohibitions': [],
            })

    def _parse_logic_tree(node: dict) -> str:
        if not isinstance(node, dict): return ""
        typ = node.get('type')
        if typ == 'CONDITION':
            d = node.get('dimension', '')
            v = node.get('value', '')
            return f"{d} = {v}"
        elif typ in ['AND', 'OR']:
            children = [_parse_logic_tree(c) for c in node.get('children', [])]
            children = [c for c in children if c]
            if not children: return ""
            if len(children) == 1: return children[0]
            joiner = f" {typ} "
            res = joiner.join(children)
            return f"({res})"
        return ""

    # Build table rows
    rows = []
    all_duties = set()
    all_countries_set = set()

    for row in raw_rows:
        origin_names = [n for n in (row.get('origin_names') or []) if n]
        receiving_names = [n for n in (row.get('receiving_names') or []) if n]
        duties = [d for d in (row.get('duties') or []) if d]
        prohibitions = [p for p in (row.get('prohibitions') or []) if p]

        sending = ", ".join(origin_names[:3]) if origin_names else "Any"
        receiving = ", ".join(receiving_names[:3]) if receiving_names else "Any"
        duty_str = ", ".join(duties) if duties else "None"
        outcome = row.get('outcome', 'permission')
        perm_prohib = "Prohibition" if outcome == 'prohibition' or prohibitions else "Permission"

        all_duties.update(duties)
        all_countries_set.update(origin_names)
        all_countries_set.update(receiving_names)

        logic_str = ""
        logic_tree_data = row.get('logic_tree')
        if logic_tree_data:
            import json
            try:
                tree = json.loads(logic_tree_data) if isinstance(logic_tree_data, str) else logic_tree_data
                logic_str = _parse_logic_tree(tree)
            except:
                pass
        
        # If there is logic, show it. Otherwise, fallback to a sensible default or the description if no logic was ever set.
        details_text = logic_str if logic_str else (row.get('description', '') or "Standard compliance criteria apply.")
        desc_text = row.get('description', '')

        rows.append(RuleTableRow(
            rule_id=row.get('rule_id', ''),
            sending_country=sending,
            receiving_country=receiving,
            rule_name=row.get('name', ''),
            rule_details=details_text,
            rule_description=desc_text,
            permission_prohibition=perm_prohib,
            duty=duty_str,
            priority=row.get('priority', 'low'),
        ))

    # Apply filters
    if search:
        search_lower = search.lower()
        rows = [r for r in rows if (
            search_lower in r.sending_country.lower() or
            search_lower in r.receiving_country.lower() or
            search_lower in r.rule_name.lower() or
            search_lower in r.rule_details.lower() or
            search_lower in r.rule_description.lower() or
            search_lower in r.permission_prohibition.lower() or
            search_lower in r.duty.lower()
        )]

    if risk:
        rows = [r for r in rows if r.priority.lower() == risk.lower()]

    if duty:
        rows = [r for r in rows if duty.lower() in r.duty.lower()]

    if country:
        country_lower = country.lower()
        rows = [r for r in rows if (
            country_lower in r.sending_country.lower() or
            country_lower in r.receiving_country.lower()
        )]

    # Count unique countries
    total_countries = len(get_all_countries())

    # Build filter options
    filters = {
        "risk": ["high", "medium", "low"],
        "duties": sorted(all_duties),
        "countries": sorted(all_countries_set),
    }

    return RulesOverviewTableResponse(
        total_rules=len(rows),
        total_countries=total_countries,
        rows=rows,
        filters=filters,
    )


@router.get("/rules-overview", response_model=RulesOverviewResponse)
async def get_rules_overview():
    """Get overview of all enabled rules (legacy format)."""
    case_matching = get_enabled_case_matching_rules()
    transfer = get_enabled_transfer_rules()
    attribute = get_enabled_attribute_rules()

    def build_overview(rule, rule_type: str) -> RuleOverview:
        if rule_type == "case_matching":
            origin_scope = ", ".join(sorted(rule.origin_countries)) if rule.origin_countries else "Any"
            receiving_scope = ", ".join(sorted(rule.receiving_countries)) if rule.receiving_countries else "Any"
            if getattr(rule, 'receiving_not_in', None):
                receiving_scope = "Not in " + ", ".join(rule.receiving_not_in)
            required = rule.required_assessments.to_list()
            conditions = []
            if rule.requires_pii:
                conditions.append("Requires PII")
            if rule.requires_personal_data:
                conditions.append("Requires Personal Data")
        elif rule_type == "transfer":
            origin_scope = "Specific countries"
            receiving_scope = "Specific countries"
            required = rule.required_actions
            conditions = []
            if rule.requires_pii:
                conditions.append("Requires PII")
            if getattr(rule, 'requires_any_data', False):
                conditions.append("Any data")
        else:
            origin_scope = ", ".join(sorted(rule.origin_countries)) if rule.origin_countries else "Any"
            receiving_scope = ", ".join(sorted(rule.receiving_countries)) if rule.receiving_countries else "Any"
            required = []
            conditions = [f"Attribute: {getattr(rule, 'attribute_name', 'Unknown')}"]
            if getattr(rule, 'requires_pii', False):
                conditions.append("Requires PII")

        return RuleOverview(
            rule_id=rule.rule_id,
            name=rule.name,
            description=rule.description,
            rule_type=rule_type,
            priority=rule.priority,
            origin_scope=origin_scope,
            receiving_scope=receiving_scope,
            outcome=rule.odrl_type,
            required_assessments=required,
            conditions=conditions,
            enabled=rule.enabled,
        )

    return RulesOverviewResponse(
        total_rules=len(case_matching) + len(transfer) + len(attribute),
        case_matching_rules=[build_overview(r, "case_matching") for r in case_matching.values()],
        transfer_rules=[build_overview(r, "transfer") for r in transfer.values()],
        attribute_rules=[build_overview(r, "attribute") for r in attribute.values()],
    )


@router.get("/cypher-templates")
async def get_cypher_templates():
    """Get list of available Cypher query templates."""
    return list_templates()
