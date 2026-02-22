"""
Cypher Query Templates
======================
Standard templates for rule evaluation and case matching.
Developers can define custom templates here.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class QueryType(Enum):
    """Types of Cypher queries"""
    CASE_SEARCH = "case_search"
    RULE_MATCH = "rule_match"
    ATTRIBUTE_CHECK = "attribute_check"
    TRANSFER_CHECK = "transfer_check"
    AGGREGATION = "aggregation"


@dataclass
class CypherTemplate:
    """
    Cypher Query Template Definition

    Allows developers to define reusable query patterns.
    Use {placeholders} for dynamic values.
    """
    template_id: str
    name: str
    description: str
    query_type: QueryType
    query_template: str
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    timeout_ms: int = 60000
    enabled: bool = True


# =============================================================================
# CASE SEARCH TEMPLATES
# =============================================================================

CASE_SEARCH_BASE = """
MATCH (c:Case)
WHERE c.case_status IN ['Completed', 'Complete', 'Active', 'Published']
{origin_filter}
{receiving_filter}
{purpose_filter}
{process_filter}
{personal_data_filter}
{pii_filter}
{assessment_filter}
RETURN c
{limit_clause}
"""

CASE_SEARCH_WITH_COUNT = """
MATCH (c:Case)
WHERE c.case_status IN ['Completed', 'Complete', 'Active', 'Published']
{origin_filter}
{receiving_filter}
{purpose_filter}
{process_filter}
{personal_data_filter}
{pii_filter}
{assessment_filter}
WITH c
RETURN count(c) as total_matches,
       count(CASE WHEN c.pia_status = 'Completed' THEN 1 END) as pia_completed,
       count(CASE WHEN c.tia_status = 'Completed' THEN 1 END) as tia_completed,
       count(CASE WHEN c.hrpr_status = 'Completed' THEN 1 END) as hrpr_completed
"""

CASE_SEARCH_EXACT_MATCH = """
MATCH (c:Case)
WHERE c.case_status IN ['Completed', 'Complete', 'Active', 'Published']
MATCH (c)-[:ORIGINATES_FROM]->(origin:Country {{name: $origin_country}})
MATCH (c)-[:TRANSFERS_TO]->(receiving:Jurisdiction {{name: $receiving_country}})
{purpose_filter}
{process_filter}
{personal_data_filter}
{assessment_requirements}
RETURN c, origin, receiving
LIMIT 1
"""


# =============================================================================
# RULE MATCHING TEMPLATES
# =============================================================================

RULE_MATCH_BY_COUNTRIES = """
MATCH (r:Rule)-[:TRIGGERED_BY_ORIGIN]->(og:CountryGroup)
OPTIONAL MATCH (oc:Country {name: $origin_country})-[:BELONGS_TO]->(og)
WHERE og.name = 'ANY' OR oc IS NOT NULL
MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg:CountryGroup)
OPTIONAL MATCH (rc:Country {name: $receiving_country})-[:BELONGS_TO]->(rg)
WHERE rg.name = 'ANY' OR rc IS NOT NULL
OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(p:Permission)
OPTIONAL MATCH (r)-[:HAS_PROHIBITION]->(pb:Prohibition)
OPTIONAL MATCH (p)-[:CAN_HAVE_DUTY]->(d1:Duty)
OPTIONAL MATCH (pb)-[:CAN_HAVE_DUTY]->(d2:Duty)
RETURN r, p, pb, collect(DISTINCT d1) as permission_duties, collect(DISTINCT d2) as prohibition_duties
ORDER BY r.priority ASC
"""

RULE_CHECK_TRANSFER_PROHIBITION = """
MATCH (r:Rule)-[:TRIGGERED_BY_ORIGIN]->(og:CountryGroup)<-[:BELONGS_TO]-(oc:Country {{name: $origin_country}})
MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg:CountryGroup)<-[:BELONGS_TO]-(rc:Country {{name: $receiving_country}})
MATCH (r)-[:HAS_PROHIBITION]->(pb:Prohibition)
RETURN r, pb
ORDER BY r.priority ASC
LIMIT 1
"""


# =============================================================================
# ATTRIBUTE CHECK TEMPLATES
# =============================================================================

ATTRIBUTE_RULE_CHECK = """
MATCH (r:Rule)-[:TRIGGERED_BY_ORIGIN]->(og:CountryGroup)
OPTIONAL MATCH (oc:Country {{name: $origin_country}})-[:BELONGS_TO]->(og)
WHERE og.name = 'ANY' OR oc IS NOT NULL
MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg:CountryGroup)
OPTIONAL MATCH (rc:Country {{name: $receiving_country}})-[:BELONGS_TO]->(rg)
WHERE rg.name = 'ANY' OR rc IS NOT NULL
RETURN r
ORDER BY r.priority ASC
"""

HEALTH_DATA_CHECK = """
MATCH (r:Rule)-[:TRIGGERED_BY_ORIGIN]->(og:CountryGroup)
OPTIONAL MATCH (oc:Country {{name: $origin_country}})-[:BELONGS_TO]->(og)
WHERE og.name = 'ANY' OR oc IS NOT NULL
OPTIONAL MATCH (r)-[:HAS_PROHIBITION]->(pb:Prohibition)
RETURN r, pb, r.priority as priority
ORDER BY priority ASC
LIMIT 1
"""


# =============================================================================
# ASSESSMENT CHECK TEMPLATES
# =============================================================================

ASSESSMENT_COMPLIANCE_CHECK = """
MATCH (c:Case)
WHERE c.case_ref_id = $case_ref_id
RETURN c.pia_status as pia_status,
       c.tia_status as tia_status,
       c.hrpr_status as hrpr_status,
       CASE WHEN c.pia_status = 'Completed' THEN true ELSE false END as pia_compliant,
       CASE WHEN c.tia_status = 'Completed' THEN true ELSE false END as tia_compliant,
       CASE WHEN c.hrpr_status = 'Completed' THEN true ELSE false END as hrpr_compliant
"""


# =============================================================================
# AGGREGATION TEMPLATES
# =============================================================================

CASE_STATISTICS = """
MATCH (c:Case)
WHERE c.case_status IN ['Completed', 'Complete', 'Active', 'Published']
OPTIONAL MATCH (c)-[:ORIGINATES_FROM]->(origin:Country)
OPTIONAL MATCH (c)-[:TRANSFERS_TO]->(receiving:Jurisdiction)
WITH c, origin.name as origin_country, receiving.name as receiving_country
RETURN count(c) as total_cases,
       count(DISTINCT origin_country) as unique_origins,
       count(DISTINCT receiving_country) as unique_destinations,
       count(CASE WHEN c.pia_status = 'Completed' THEN 1 END) as pia_completed_count,
       count(CASE WHEN c.tia_status = 'Completed' THEN 1 END) as tia_completed_count,
       count(CASE WHEN c.hrpr_status = 'Completed' THEN 1 END) as hrpr_completed_count
"""

COUNTRY_TRANSFER_SUMMARY = """
MATCH (c:Case)-[:ORIGINATES_FROM]->(origin:Country)
MATCH (c)-[:TRANSFERS_TO]->(receiving:Jurisdiction)
WHERE c.case_status IN ['Completed', 'Complete', 'Active', 'Published']
WITH origin.name as origin_country, receiving.name as receiving_country, count(c) as transfer_count
RETURN origin_country, receiving_country, transfer_count
ORDER BY transfer_count DESC
LIMIT $limit
"""


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

CYPHER_TEMPLATES: Dict[str, CypherTemplate] = {
    # Case Search Templates
    "case_search_base": CypherTemplate(
        template_id="case_search_base",
        name="Basic Case Search",
        description="Search for cases with flexible filtering",
        query_type=QueryType.CASE_SEARCH,
        query_template=CASE_SEARCH_BASE,
        required_params=[],
        optional_params=["origin_filter", "receiving_filter", "purpose_filter",
                        "process_filter", "personal_data_filter", "pii_filter",
                        "assessment_filter", "limit_clause"],
    ),

    "case_search_with_count": CypherTemplate(
        template_id="case_search_with_count",
        name="Case Search with Statistics",
        description="Search cases and return aggregate counts",
        query_type=QueryType.CASE_SEARCH,
        query_template=CASE_SEARCH_WITH_COUNT,
        required_params=[],
        optional_params=["origin_filter", "receiving_filter", "purpose_filter",
                        "process_filter", "personal_data_filter", "pii_filter",
                        "assessment_filter"],
    ),

    "case_search_exact_match": CypherTemplate(
        template_id="case_search_exact_match",
        name="Exact Case Match",
        description="Find a single case that exactly matches all criteria",
        query_type=QueryType.CASE_SEARCH,
        query_template=CASE_SEARCH_EXACT_MATCH,
        required_params=["origin_country", "receiving_country"],
    ),

    # Rule Matching Templates
    "rule_match_by_countries": CypherTemplate(
        template_id="rule_match_by_countries",
        name="Rule Match by Countries",
        description="Find rules triggered by origin/receiving countries",
        query_type=QueryType.RULE_MATCH,
        query_template=RULE_MATCH_BY_COUNTRIES,
        required_params=["origin_country", "receiving_country"],
    ),

    "rule_check_transfer_prohibition": CypherTemplate(
        template_id="rule_check_transfer_prohibition",
        name="Check Transfer Prohibition",
        description="Check if a transfer is prohibited by rules",
        query_type=QueryType.TRANSFER_CHECK,
        query_template=RULE_CHECK_TRANSFER_PROHIBITION,
        required_params=["origin_country", "receiving_country"],
    ),

    # Attribute Check Templates
    "attribute_rule_check": CypherTemplate(
        template_id="attribute_rule_check",
        name="Attribute Rule Check",
        description="Check for attribute-based rules",
        query_type=QueryType.ATTRIBUTE_CHECK,
        query_template=ATTRIBUTE_RULE_CHECK,
        required_params=["attribute_name", "origin_country", "receiving_country"],
    ),

    "health_data_check": CypherTemplate(
        template_id="health_data_check",
        name="Health Data Rule Check",
        description="Check for health data restrictions",
        query_type=QueryType.ATTRIBUTE_CHECK,
        query_template=HEALTH_DATA_CHECK,
        required_params=["origin_country"],
    ),

    # Assessment Templates
    "assessment_compliance_check": CypherTemplate(
        template_id="assessment_compliance_check",
        name="Assessment Compliance Check",
        description="Check if a case has completed required assessments",
        query_type=QueryType.CASE_SEARCH,
        query_template=ASSESSMENT_COMPLIANCE_CHECK,
        required_params=["case_ref_id"],
    ),

    # Aggregation Templates
    "case_statistics": CypherTemplate(
        template_id="case_statistics",
        name="Case Statistics",
        description="Get aggregate statistics for all cases",
        query_type=QueryType.AGGREGATION,
        query_template=CASE_STATISTICS,
        required_params=[],
    ),

    "country_transfer_summary": CypherTemplate(
        template_id="country_transfer_summary",
        name="Country Transfer Summary",
        description="Get summary of transfers between countries",
        query_type=QueryType.AGGREGATION,
        query_template=COUNTRY_TRANSFER_SUMMARY,
        required_params=[],
        optional_params=["limit"],
    ),
}


# =============================================================================
# FILTER BUILDERS
# =============================================================================

def build_origin_filter(country: Optional[str], use_index: bool = True) -> str:
    """Build Cypher filter for origin country (uses $origin_country param)"""
    if not country:
        return ""
    if use_index:
        return "MATCH (c)-[:ORIGINATES_FROM]->(origin:Country {name: $origin_country})"
    return "MATCH (c)-[:ORIGINATES_FROM]->(origin:Country) WHERE origin.name = $origin_country"


def build_receiving_filter(country: Optional[str], use_index: bool = True) -> str:
    """Build Cypher filter for receiving country (uses $receiving_country param)"""
    if not country:
        return ""
    if use_index:
        return "MATCH (c)-[:TRANSFERS_TO]->(receiving:Jurisdiction {name: $receiving_country})"
    return "MATCH (c)-[:TRANSFERS_TO]->(receiving:Jurisdiction) WHERE receiving.name = $receiving_country"


def build_purpose_filter(purposes: Optional[List[str]]) -> str:
    """Build Cypher filter for purposes (uses $purposes param)"""
    if not purposes:
        return ""
    return "MATCH (c)-[:HAS_PURPOSE]->(p:Purpose) WHERE p.name IN $purposes"


def build_process_filter(process_l1: Optional[List[str]] = None,
                        process_l2: Optional[List[str]] = None,
                        process_l3: Optional[List[str]] = None) -> str:
    """Build Cypher filter for processes (uses $process_l1/$process_l2/$process_l3 params)"""
    filters = []
    if process_l1:
        filters.append("MATCH (c)-[:HAS_PROCESS_L1]->(pl1:ProcessL1) WHERE pl1.name IN $process_l1")
    if process_l2:
        filters.append("MATCH (c)-[:HAS_PROCESS_L2]->(pl2:ProcessL2) WHERE pl2.name IN $process_l2")
    if process_l3:
        filters.append("MATCH (c)-[:HAS_PROCESS_L3]->(pl3:ProcessL3) WHERE pl3.name IN $process_l3")
    return "\n".join(filters)


def build_pii_filter(pii: Optional[bool]) -> str:
    """Build Cypher filter for PII"""
    if pii is None:
        return ""
    return f"AND c.pii = {str(pii).lower()}"


def build_assessment_filter(pia_required: bool = False,
                           tia_required: bool = False,
                           hrpr_required: bool = False,
                           completed_only: bool = True) -> str:
    """Build Cypher filter for assessment requirements"""
    if not any([pia_required, tia_required, hrpr_required]):
        return ""

    conditions = []
    status_value = "'Completed'" if completed_only else "'Completed', 'In Progress'"

    if pia_required:
        conditions.append(f"c.pia_status IN [{status_value}]")
    if tia_required:
        conditions.append(f"c.tia_status IN [{status_value}]")
    if hrpr_required:
        conditions.append(f"c.hrpr_status IN [{status_value}]")

    return "AND " + " AND ".join(conditions)


def build_query_from_template(template_id: str, params: Dict[str, Any]) -> str:
    """
    Build a complete Cypher query from a template and parameters.

    Args:
        template_id: The ID of the template to use
        params: Dictionary of parameters to fill in the template

    Returns:
        Complete Cypher query string
    """
    template = CYPHER_TEMPLATES.get(template_id)
    if not template:
        raise ValueError(f"Unknown template: {template_id}")

    query = template.query_template

    # Replace placeholders with empty strings if not provided
    for param in template.optional_params:
        if param not in params:
            params[param] = ""

    # Format the query with parameters
    try:
        query = query.format(**params)
    except KeyError as e:
        raise ValueError(f"Missing required parameter: {e}")

    # Clean up empty lines
    query = "\n".join(line for line in query.split("\n") if line.strip())

    return query


def get_template(template_id: str) -> Optional[CypherTemplate]:
    """Get a template by ID"""
    return CYPHER_TEMPLATES.get(template_id)


def list_templates() -> List[Dict[str, Any]]:
    """List all available templates"""
    return [
        {
            "template_id": t.template_id,
            "name": t.name,
            "description": t.description,
            "query_type": t.query_type.value,
            "required_params": t.required_params,
            "optional_params": t.optional_params,
        }
        for t in CYPHER_TEMPLATES.values()
        if t.enabled
    ]
