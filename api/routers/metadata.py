"""
Metadata Router
================
Graph-native endpoints for countries, purposes, processes, legal entities,
regulators, authorities, GBGF, data categories, and dropdown values.
All data is served from the RulesGraph — no runtime file I/O.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends

from services.database import get_db_service
from services.cache import get_cache_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["metadata"])


def get_db():
    return get_db_service()


# ─── Helper ─────────────────────────────────────────────────────────────

def _rules_query(db, query: str, params: dict = None) -> list:
    """Execute a Cypher query against the rules graph and return list of dicts."""
    try:
        result = db.get_rules_graph().query(query, params)
        if not hasattr(result, 'result_set') or not result.result_set:
            return []
        headers = result.header
        rows = []
        for row in result.result_set:
            row_dict = {}
            for i, header in enumerate(headers):
                col_name = header[1] if isinstance(header, (list, tuple)) else header
                row_dict[col_name] = row[i]
            rows.append(row_dict)
        return rows
    except Exception as e:
        logger.warning(f"Rules graph query error: {e}")
        return []


# ─── Countries ──────────────────────────────────────────────────────────

@router.get("/countries")
async def get_countries(db=Depends(get_db)):
    """Get list of all countries with ISO codes."""
    cache = get_cache_service()
    cached = cache.get("countries_list", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (c:Country)
    RETURN c.name as name, c.iso2 as iso2, c.iso3 as iso3
    ORDER BY c.name
    """)
    countries = [r.get('name') for r in rows if r.get('name')]

    cache.set("countries_list", countries, "metadata", ttl=600)
    return countries


@router.get("/countries/detailed")
async def get_countries_detailed(db=Depends(get_db)):
    """Get countries with full details including ISO codes and RTN."""
    cache = get_cache_service()
    cached = cache.get("countries_detailed", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (c:Country)
    RETURN c.name as name, c.iso2 as iso2, c.iso3 as iso3, c.rtn_code as rtn_code
    ORDER BY c.name
    """)
    result = [
        {"name": r["name"], "iso2": r.get("iso2", ""), "iso3": r.get("iso3", ""), "rtn_code": r.get("rtn_code", "")}
        for r in rows if r.get("name")
    ]

    cache.set("countries_detailed", result, "metadata", ttl=600)
    return result


# ─── Purposes ───────────────────────────────────────────────────────────

@router.get("/purposes")
async def get_purposes(db=Depends(get_db)):
    """Get list of all purposes (from PurposeOfProcessing and Purpose nodes)."""
    cache = get_cache_service()
    cached = cache.get("purposes_list", "metadata")
    if cached:
        return cached

    # Try PurposeOfProcessing first, fall back to Purpose
    rows = _rules_query(db, """
    MATCH (p:PurposeOfProcessing)
    RETURN p.name as name, p.description as description
    ORDER BY p.name
    """)
    if not rows:
        rows = _rules_query(db, """
        MATCH (p:Purpose)
        RETURN p.name as name
        ORDER BY p.name
        """)

    purposes = [r.get('name') for r in rows if r.get('name')]

    cache.set("purposes_list", purposes, "metadata", ttl=600)
    return purposes


@router.get("/purpose-of-processing")
async def get_purpose_of_processing(db=Depends(get_db)):
    """Get purpose of processing reference list from graph."""
    cache = get_cache_service()
    cached = cache.get("purpose_of_processing", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (p:PurposeOfProcessing)
    RETURN p.name as name, p.description as description
    ORDER BY p.name
    """)
    result = [{"name": r["name"], "description": r.get("description", "")} for r in rows if r.get("name")]

    # If no PurposeOfProcessing nodes, fall back to Purpose nodes
    if not result:
        rows = _rules_query(db, "MATCH (p:Purpose) RETURN p.name as name ORDER BY p.name")
        result = [{"name": r["name"], "description": ""} for r in rows if r.get("name")]

    cache.set("purpose_of_processing", result, "metadata", ttl=600)
    return result


# ─── Processes ──────────────────────────────────────────────────────────

@router.get("/processes")
async def get_processes(db=Depends(get_db)):
    """Get list of all processes by level, derived from Process nodes."""
    cache = get_cache_service()
    cached = cache.get("processes_list", "metadata")
    if cached:
        return cached

    processes: dict = {"l1": [], "l2": [], "l3": [], "hierarchy": []}

    rows = _rules_query(db, """
    MATCH (p:Process)
    RETURN p.name as name, p.l1 as l1, p.l2 as l2, p.l3 as l3,
           p.global_business_function as gbgf, p.definition as definition
    ORDER BY p.name
    """)

    l1_set: set = set()
    l2_set: set = set()
    l3_set: set = set()
    hierarchy: dict = {}

    for r in rows:
        l1 = r.get('l1') or ''
        l2 = r.get('l2') or ''
        l3 = r.get('l3') or ''
        if l1:
            l1_set.add(l1)
            if l1 not in hierarchy:
                hierarchy[l1] = {}
        if l2:
            l2_set.add(l2)
            if l1 and l2 not in hierarchy.get(l1, {}):
                if l1 not in hierarchy:
                    hierarchy[l1] = {}
                hierarchy[l1][l2] = []
        if l3:
            l3_set.add(l3)
            if l1 and l2 and l3 not in hierarchy.get(l1, {}).get(l2, []):
                if l1 not in hierarchy:
                    hierarchy[l1] = {}
                if l2 not in hierarchy[l1]:
                    hierarchy[l1][l2] = []
                hierarchy[l1][l2].append(l3)

    processes["l1"] = sorted(l1_set)
    processes["l2"] = sorted(l2_set)
    processes["l3"] = sorted(l3_set)
    processes["hierarchy"] = hierarchy

    cache.set("processes_list", processes, "metadata", ttl=600)
    return processes


# ─── Legal Entities (graph-native) ──────────────────────────────────────

@router.get("/legal-entities")
async def get_legal_entities(db=Depends(get_db)):
    """Get all legal entities with country mapping from graph."""
    cache = get_cache_service()
    cached = cache.get("legal_entities", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (c:Country)-[:HAS_LEGAL_ENTITY]->(le:LegalEntity)
    RETURN c.name as country, le.name as entity_name
    ORDER BY c.name, le.name
    """)

    result: dict = {}
    for r in rows:
        country = r.get('country', '')
        entity = r.get('entity_name', '')
        if country and entity:
            if country not in result:
                result[country] = []
            result[country].append(entity)

    cache.set("legal_entities", result, "metadata", ttl=600)
    return result


@router.get("/legal-entities/{country}")
async def get_legal_entities_for_country(country: str, db=Depends(get_db)):
    """Get legal entities for a specific country from graph."""
    rows = _rules_query(db, """
    MATCH (c:Country)-[:HAS_LEGAL_ENTITY]->(le:LegalEntity)
    WHERE toLower(c.name) = toLower($country) OR c.iso2 = $country OR c.iso3 = $country
    RETURN le.name as entity_name
    ORDER BY le.name
    """, {"country": country})

    return [r.get('entity_name') for r in rows if r.get('entity_name')]


# ─── Group Data Categories ──────────────────────────────────────────────

@router.get("/group-data-categories")
async def get_group_data_categories(db=Depends(get_db)):
    """Get group data categories from the rules graph."""
    cache = get_cache_service()
    cached = cache.get("group_data_categories", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (n:GDC)
    RETURN n.name as name, n.category as category, n.data_domain as data_domain,
           n.data_privacy_indicator as data_privacy_indicator,
           n.gdc_level_2 as gdc_level_2, n.gdc_level_3 as gdc_level_3
    ORDER BY n.category, n.name
    """)
    categories = [
        {"name": r["name"], "category": r.get("category", ""), "data_domain": r.get("data_domain", "")}
        for r in rows if r.get("name")
    ]

    cache.set("group_data_categories", categories, "metadata", ttl=600)
    return categories


# ─── Regulators (NEW) ───────────────────────────────────────────────────

@router.get("/regulators")
async def get_regulators(db=Depends(get_db)):
    """Get all regulators from graph."""
    cache = get_cache_service()
    cached = cache.get("regulators_list", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (reg:Regulator)
    RETURN reg.name as name, reg.country_code as country_code, reg.region as region,
           reg.regulator as regulator, reg.regulator_type as regulator_type,
           reg.regulator_definition as definition
    ORDER BY reg.name
    """)
    result = [
        {
            "name": r["name"], "country_code": r.get("country_code", ""),
            "region": r.get("region", ""), "regulator": r.get("regulator", ""),
            "regulator_type": r.get("regulator_type", ""), "definition": r.get("definition", ""),
        }
        for r in rows if r.get("name")
    ]

    cache.set("regulators_list", result, "metadata", ttl=600)
    return result


@router.get("/regulators/{country_iso2}")
async def get_regulators_for_country(country_iso2: str, db=Depends(get_db)):
    """Get regulators for a specific country by ISO 2 code."""
    rows = _rules_query(db, """
    MATCH (c:Country)-[:HAS_REGULATOR]->(reg:Regulator)
    WHERE c.iso2 = $iso2 OR toLower(c.name) = toLower($iso2)
    RETURN reg.name as name, reg.country_code as country_code,
           reg.regulator_type as regulator_type, reg.regulator_definition as definition
    ORDER BY reg.name
    """, {"iso2": country_iso2})

    return [
        {"name": r["name"], "country_code": r.get("country_code", ""),
         "regulator_type": r.get("regulator_type", ""), "definition": r.get("definition", "")}
        for r in rows if r.get("name")
    ]


# ─── Authorities (NEW) ──────────────────────────────────────────────────

@router.get("/authorities")
async def get_authorities(db=Depends(get_db)):
    """Get all authorities from graph."""
    cache = get_cache_service()
    cached = cache.get("authorities_list", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (auth:Authority)
    RETURN auth.name as name, auth.country_code as country_code
    ORDER BY auth.name
    """)
    result = [{"name": r["name"], "country_code": r.get("country_code", "")} for r in rows if r.get("name")]

    cache.set("authorities_list", result, "metadata", ttl=600)
    return result


@router.get("/authorities/{country_iso2}")
async def get_authorities_for_country(country_iso2: str, db=Depends(get_db)):
    """Get authorities for a specific country by ISO 2 code."""
    rows = _rules_query(db, """
    MATCH (c:Country)-[:HAS_AUTHORITY]->(auth:Authority)
    WHERE c.iso2 = $iso2 OR toLower(c.name) = toLower($iso2)
    RETURN auth.name as name, auth.country_code as country_code
    ORDER BY auth.name
    """, {"iso2": country_iso2})

    return [{"name": r["name"], "country_code": r.get("country_code", "")} for r in rows if r.get("name")]


# ─── Global Business Functions (NEW) ────────────────────────────────────

@router.get("/global-business-functions")
async def get_global_business_functions(db=Depends(get_db)):
    """Get all global business functions from graph."""
    cache = get_cache_service()
    cached = cache.get("gbgf_list", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (gbgf:GlobalBusinessFunction)
    RETURN gbgf.name as name, gbgf.rtn_code as rtn_code,
           gbgf.gbgf_level_1 as gbgf_level_1, gbgf.privacy_notice as privacy_notice,
           gbgf.gbgf_level_2 as gbgf_level_2
    ORDER BY gbgf.name
    """)
    result = [
        {
            "name": r["name"], "rtn_code": r.get("rtn_code", ""),
            "gbgf_level_1": r.get("gbgf_level_1", ""), "gbgf_level_2": r.get("gbgf_level_2", ""),
        }
        for r in rows if r.get("name")
    ]

    cache.set("gbgf_list", result, "metadata", ttl=600)
    return result


# ─── Sensitive Data Categories (NEW) ────────────────────────────────────

@router.get("/sensitive-data-categories")
async def get_sensitive_data_categories(db=Depends(get_db)):
    """Get all sensitive data categories from graph."""
    cache = get_cache_service()
    cached = cache.get("sdc_list", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (sdc:SensitiveDataCategory)
    RETURN sdc.name as name, sdc.country_code as country_code,
           sdc.definition as definition,
           sdc.sensitive_data_category_name as sensitive_data_category_name
    ORDER BY sdc.country_code, sdc.name
    """)
    result = [
        {
            "name": r["name"], "country_code": r.get("country_code", ""),
            "definition": r.get("definition", ""),
            "sensitive_data_category_name": r.get("sensitive_data_category_name", ""),
        }
        for r in rows if r.get("name")
    ]

    cache.set("sdc_list", result, "metadata", ttl=600)
    return result


# ─── Data Categories (NEW) ──────────────────────────────────────────────

@router.get("/data-categories")
async def get_data_categories(db=Depends(get_db)):
    """Get all data categories with GDPR info from graph."""
    cache = get_cache_service()
    cached = cache.get("data_categories_list", "metadata")
    if cached:
        return cached

    rows = _rules_query(db, """
    MATCH (dc:DataCategory)
    RETURN dc.name as name, dc.definition as definition,
           dc.gdpr_category_name as gdpr_category_name
    ORDER BY dc.gdpr_category_name, dc.name
    """)
    result = [
        {
            "name": r["name"], "definition": r.get("definition", ""),
            "gdpr_category_name": r.get("gdpr_category_name", ""),
        }
        for r in rows if r.get("name")
    ]

    cache.set("data_categories_list", result, "metadata", ttl=600)
    return result


# ─── All Dropdown Values (unified) ──────────────────────────────────────

@router.get("/all-dropdown-values")
async def get_all_dropdown_values(db=Depends(get_db)):
    """Get all dropdown values in one call — purely graph-based.
    Includes dynamically-created node types from schema metadata."""
    cache = get_cache_service()
    cached = cache.get("all_dropdown_values", "metadata")
    if cached:
        return cached

    result = {}

    # Core dropdown values
    result["countries"] = await get_countries(db)
    result["purposes"] = await get_purposes(db)
    result["processes"] = await get_processes(db)

    # Dictionary-based values from the rules graph
    for node_type, key in [("Process", "processes_dict"), ("Purpose", "purposes_dict"),
                            ("DataSubject", "data_subjects"), ("GDC", "gdc")]:
        rows = _rules_query(db, f"""
        MATCH (n:{node_type})
        RETURN n.name as name, n.category as category
        ORDER BY n.category, n.name
        """)
        result[key] = [{"name": r["name"], "category": r.get("category", "")} for r in rows if r.get("name")]

    # Legal entities (graph-native)
    result["legal_entities"] = await get_legal_entities(db)

    # Purpose of processing
    result["purpose_of_processing"] = await get_purpose_of_processing(db)

    # Group data categories
    result["group_data_categories"] = await get_group_data_categories(db)

    # New entity types
    result["regulators"] = await get_regulators(db)
    result["authorities"] = await get_authorities(db)
    result["global_business_functions"] = await get_global_business_functions(db)
    result["sensitive_data_categories"] = await get_sensitive_data_categories(db)
    result["data_categories"] = await get_data_categories(db)

    # Dynamic node types from schema metadata
    try:
        import json, os
        schema_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "schema_metadata.json"))
        with open(schema_path, "r") as f:
            schema = json.load(f)
        # Already-covered node types
        covered = {
            "Country", "CountryGroup", "Rule", "Process", "Purpose", "DataSubject",
            "GDC", "LegalEntity", "PurposeOfProcessing", "DataCategory",
            "SensitiveDataCategory", "Regulator", "Authority", "GlobalBusinessFunction",
            "Duty", "Action", "Permission", "Prohibition", "Attribute",
        }
        for nt in schema.get("nodeTypes", []):
            label = nt["label"]
            if label not in covered:
                key = label[0].lower() + label[1:] + "s"
                rows = _rules_query(db, f"MATCH (n:{label}) RETURN n.name as name ORDER BY n.name")
                result[key] = [r["name"] for r in rows if r.get("name")]
    except Exception as e:
        logger.debug(f"Could not load dynamic node types for dropdowns: {e}")

    cache.set("all_dropdown_values", result, "metadata", ttl=600)
    return result
