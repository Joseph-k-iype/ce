"""
Graph Data Router
==================
Endpoints for graph visualization data.
Schema metadata is loaded from config/schema_metadata.json and drives lane/type maps dynamically.
"""

import json
import logging
import os
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from services.database import get_db_service
from services.cache import get_cache_service
from rules.dictionaries.country_groups import COUNTRY_GROUPS
from utils.schema_manager import (
    load_schema,
    save_schema,
    get_all_lanes,
    get_protected_relationships,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])

# ──────────────────────────────────────────────────────────
# Schema helper wrappers (delegating to schema_manager)
# ──────────────────────────────────────────────────────────

def _get_primary_lanes() -> list[dict]:
    return [l for l in get_all_lanes() if l.get("primary")]


def _get_extra_lanes() -> list[dict]:
    return [l for l in get_all_lanes() if not l.get("primary")]


def _get_rel_queries() -> list[tuple[str, str, str, str, str]]:
    """Build (source_label, rel_type, target_label, lane_id, rf_type) tuples from schema metadata.
    Excludes country-specific relationships (handled separately in get_editor_network)."""
    schema = load_schema()
    node_type_map = {nt["label"]: nt for nt in schema.get("nodeTypes", [])}
    country_rels = {"TRIGGERED_BY_ORIGIN", "TRIGGERED_BY_RECEIVING", "BELONGS_TO", "EXCLUDES_RECEIVING"}
    result = []
    for rt in schema.get("relationshipTypes", []):
        if rt["type"] in country_rels:
            continue
        source_label = rt["from"]
        target_label = rt["to"]
        nt = node_type_map.get(target_label)
        if nt:
            result.append((source_label, rt["type"], target_label, nt["laneId"], nt["reactFlowType"]))
    return result


def get_db():
    return get_db_service()


@router.get("/rules-network")
async def get_rules_network(db=Depends(get_db)):
    """
    Get rules network data for React Flow visualization.
    Returns countries, rules, and their relationships as nodes/edges.
    """
    cache = get_cache_service()
    cached = cache.get("rules_network", "metadata")
    if cached:
        return cached

    try:
        # Get all rules with their country group connections
        rules_query = """
        MATCH (r:Rule)
        OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og:CountryGroup)
        OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg:CountryGroup)
        OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(perm:Permission)
        OPTIONAL MATCH (r)-[:HAS_PROHIBITION]->(prohib:Prohibition)
        RETURN r.rule_id as rule_id,
               r.priority as priority,
               r.odrl_type as odrl_type,
               r.origin_match_type as origin_match_type,
               r.receiving_match_type as receiving_match_type,
               r.has_pii_required as has_pii_required,
               og.name as origin_group,
               rg.name as receiving_group,
               perm.name as permission_name,
               prohib.name as prohibition_name
        """
        rules_result = db.execute_rules_query(rules_query)

        # Get country groups with their countries
        groups_query = """
        MATCH (cg:CountryGroup)
        OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(cg)
        RETURN cg.name as group_name,
               collect(c.name) as countries
        """
        groups_result = db.execute_rules_query(groups_query)

        # Build nodes and edges
        nodes = []
        edges = []
        node_id_counter = 0

        # Add country group nodes as swimlane containers
        group_map = {}
        for group in groups_result:
            group_name = group.get('group_name', '')
            if group_name:
                node_id = f"group_{node_id_counter}"
                node_id_counter += 1
                group_map[group_name] = node_id
                nodes.append({
                    "id": node_id,
                    "type": "countryGroup",
                    "data": {
                        "label": group_name,
                        "countries": group.get('countries', []),
                        "country_count": len(group.get('countries', [])),
                    },
                    "position": {"x": 0, "y": 0},
                })

        # Add rule nodes
        for rule in rules_result:
            rule_id = rule.get('rule_id', '')
            if not rule_id:
                continue

            node_id = f"rule_{node_id_counter}"
            node_id_counter += 1
            odrl_type = rule.get('odrl_type', 'Permission')

            nodes.append({
                "id": node_id,
                "type": "ruleNode",
                "data": {
                    "rule_id": rule_id,
                    "priority": rule.get('priority', 0),
                    "odrl_type": odrl_type,
                    "has_pii_required": rule.get('has_pii_required', False),
                    "permission_name": rule.get('permission_name'),
                    "prohibition_name": rule.get('prohibition_name'),
                    "outcome": "prohibition" if odrl_type == "Prohibition" else "permission",
                },
                "position": {"x": 0, "y": 0},
            })

            # Add edges from origin group
            origin_group = rule.get('origin_group')
            if origin_group and origin_group in group_map:
                edges.append({
                    "id": f"edge_{len(edges)}",
                    "source": group_map[origin_group],
                    "target": node_id,
                    "type": "ruleEdge",
                    "data": {"relationship": "TRIGGERED_BY_ORIGIN"},
                })

            # Add edges to receiving group
            receiving_group = rule.get('receiving_group')
            if receiving_group and receiving_group in group_map:
                edges.append({
                    "id": f"edge_{len(edges)}",
                    "source": node_id,
                    "target": group_map[receiving_group],
                    "type": "ruleEdge",
                    "data": {"relationship": "TRIGGERED_BY_RECEIVING"},
                })

        result = {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_rules": len([n for n in nodes if n["type"] == "ruleNode"]),
                "total_groups": len([n for n in nodes if n["type"] == "countryGroup"]),
                "total_edges": len(edges),
            }
        }

        cache.set("rules_network", result, "metadata", ttl=300)
        return result

    except Exception as e:
        logger.error(f"Error fetching rules network: {e}")
        return {"nodes": [], "edges": [], "stats": {"total_rules": 0, "total_groups": 0, "total_edges": 0}}


@router.get("/country-groups")
async def get_country_groups(db=Depends(get_db)):
    """Get all country groups with their member countries."""
    cache = get_cache_service()
    cached = cache.get("country_groups", "metadata")
    if cached:
        return cached

    try:
        query = """
        MATCH (cg:CountryGroup)
        OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(cg)
        RETURN cg.name as group_name,
               collect(c.name) as countries
        ORDER BY cg.name
        """
        result = db.execute_rules_query(query)

        groups = {}
        for row in result:
            group_name = row.get('group_name', '')
            if group_name:
                groups[group_name] = row.get('countries', [])

        cache.set("country_groups", groups, "metadata", ttl=600)
        return groups

    except Exception as e:
        logger.error(f"Error fetching country groups: {e}")
        return {}


# ──────────────────────────────────────────────────────────
# Policy Editor endpoints
# ──────────────────────────────────────────────────────────

# Maps are now loaded dynamically from config/schema_metadata.json
# Use _get_lane_map(), _get_node_type_map(), _get_primary_lanes(), _get_extra_lanes()


@router.get("/editor-network")
async def get_editor_network(
    expand_countries: bool = Query(default=True, description="Expand country groups to individual countries"),
    db=Depends(get_db),
):
    """
    Get full graph data for the Policy Editor canvas.
    Returns all node types with lane assignments and all relationships as edges.
    When expand_countries=True (default), CountryGroups are resolved to individual Country nodes.
    """
    cache_key = f"editor_network_{'expanded' if expand_countries else 'grouped'}"
    cache = get_cache_service()
    cached = cache.get(cache_key, "metadata")
    if cached:
        return cached

    try:
        nodes = []
        edges = []
        seen_node_ids = {}  # graph_label:name → generated id
        edge_counter = 0

        # ── 1. Rules ──
        rules_query = """
        MATCH (r:Rule)
        RETURN r.rule_id as rule_id, r.name as name, r.description as description,
               r.priority as priority, r.odrl_type as odrl_type,
               r.has_pii_required as has_pii_required,
               r.origin_match_type as origin_match_type,
               r.receiving_match_type as receiving_match_type
        """
        for row in db.execute_rules_query(rules_query):
            rid = row.get('rule_id', '')
            if not rid:
                continue
            node_id = f"rule_{rid}"
            odrl_type = row.get('odrl_type', 'Permission')
            seen_node_ids[f"Rule:{rid}"] = node_id
            nodes.append({
                "id": node_id,
                "type": "ruleNode",
                "data": {
                    "label": row.get('name') or rid,
                    "nodeType": "Rule",
                    "lane": "rule",
                    "ruleId": rid,
                    "description": row.get('description', ''),
                    "odrlType": odrl_type,
                    "priority": row.get('priority', 0),
                    "hasPiiRequired": row.get('has_pii_required', False),
                },
                "position": {"x": 0, "y": 0},
            })

        # ── 2. Country handling ──
        if expand_countries:
            # Build group→countries membership from graph
            group_members = {}  # group_name → [country_name, ...]
            groups_query = """
            MATCH (cg:CountryGroup)
            OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(cg)
            RETURN cg.name as group_name, collect(c.name) as countries
            """
            for row in db.execute_rules_query(groups_query):
                gname = row.get('group_name', '')
                if gname:
                    group_members[gname] = [c for c in row.get('countries', []) if c]

            # Query origin group edges: Rule → CountryGroup
            origin_group_edges = []  # (rule_id, group_name)
            origin_query = """
            MATCH (r:Rule)-[:TRIGGERED_BY_ORIGIN]->(cg:CountryGroup)
            RETURN r.rule_id as rule_id, cg.name as group_name
            """
            for row in db.execute_rules_query(origin_query):
                rid = row.get('rule_id', '')
                gname = row.get('group_name', '')
                if rid and gname:
                    origin_group_edges.append((rid, gname))

            # Query origin direct country edges: Rule → Country
            origin_country_query = """
            MATCH (r:Rule)-[:TRIGGERED_BY_ORIGIN]->(c:Country)
            RETURN r.rule_id as rule_id, c.name as country_name
            """
            origin_direct_countries = []
            try:
                for row in db.execute_rules_query(origin_country_query):
                    rid = row.get('rule_id', '')
                    cname = row.get('country_name', '')
                    if rid and cname:
                        origin_direct_countries.append((rid, cname))
            except Exception:
                pass

            # Query receiving group edges: Rule → CountryGroup
            receiving_group_edges = []
            receiving_query = """
            MATCH (r:Rule)-[:TRIGGERED_BY_RECEIVING]->(cg:CountryGroup)
            RETURN r.rule_id as rule_id, cg.name as group_name
            """
            for row in db.execute_rules_query(receiving_query):
                rid = row.get('rule_id', '')
                gname = row.get('group_name', '')
                if rid and gname:
                    receiving_group_edges.append((rid, gname))

            # Query receiving direct country edges: Rule → Country
            receiving_country_query = """
            MATCH (r:Rule)-[:TRIGGERED_BY_RECEIVING]->(c:Country)
            RETURN r.rule_id as rule_id, c.name as country_name
            """
            receiving_direct_countries = []
            try:
                for row in db.execute_rules_query(receiving_country_query):
                    rid = row.get('rule_id', '')
                    cname = row.get('country_name', '')
                    if rid and cname:
                        receiving_direct_countries.append((rid, cname))
            except Exception:
                pass

            # Expand groups → deduplicated country nodes per lane
            # origin_countries_set: set of country names in origin lane
            origin_countries_set = set()
            origin_country_rule_edges = []  # (country_name, rule_id)

            for rid, gname in origin_group_edges:
                for country in group_members.get(gname, []):
                    origin_countries_set.add(country)
                    origin_country_rule_edges.append((country, rid))

            for rid, cname in origin_direct_countries:
                origin_countries_set.add(cname)
                origin_country_rule_edges.append((cname, rid))

            receiving_countries_set = set()
            receiving_country_rule_edges = []  # (country_name, rule_id)

            for rid, gname in receiving_group_edges:
                for country in group_members.get(gname, []):
                    receiving_countries_set.add(country)
                    receiving_country_rule_edges.append((country, rid))

            for rid, cname in receiving_direct_countries:
                receiving_countries_set.add(cname)
                receiving_country_rule_edges.append((cname, rid))

            # Create deduplicated origin country nodes
            for country in sorted(origin_countries_set):
                nid = f"country_{country.replace(' ', '_')}_origin"
                seen_node_ids[f"Country:{country}:origin"] = nid
                nodes.append({
                    "id": nid,
                    "type": "countryNode",
                    "data": {
                        "label": country,
                        "nodeType": "Country",
                        "lane": "originCountry",
                    },
                    "position": {"x": 0, "y": 0},
                })

            # Create deduplicated receiving country nodes
            for country in sorted(receiving_countries_set):
                nid = f"country_{country.replace(' ', '_')}_recv"
                seen_node_ids[f"Country:{country}:recv"] = nid
                nodes.append({
                    "id": nid,
                    "type": "countryNode",
                    "data": {
                        "label": country,
                        "nodeType": "Country",
                        "lane": "receivingCountry",
                    },
                    "position": {"x": 0, "y": 0},
                })

            # Create deduplicated edges: origin country → rule
            origin_edge_set = set()
            for country, rid in origin_country_rule_edges:
                src = seen_node_ids.get(f"Country:{country}:origin")
                tgt = seen_node_ids.get(f"Rule:{rid}")
                if src and tgt:
                    edge_key = (src, tgt)
                    if edge_key not in origin_edge_set:
                        origin_edge_set.add(edge_key)
                        edges.append({
                            "id": f"e_{edge_counter}",
                            "source": src,
                            "target": tgt,
                            "type": "laneEdge",
                            "data": {"relationship": "TRIGGERED_BY_ORIGIN"},
                        })
                        edge_counter += 1

            # Create deduplicated edges: rule → receiving country
            recv_edge_set = set()
            for country, rid in receiving_country_rule_edges:
                src = seen_node_ids.get(f"Rule:{rid}")
                tgt = seen_node_ids.get(f"Country:{country}:recv")
                if src and tgt:
                    edge_key = (src, tgt)
                    if edge_key not in recv_edge_set:
                        recv_edge_set.add(edge_key)
                        edges.append({
                            "id": f"e_{edge_counter}",
                            "source": src,
                            "target": tgt,
                            "type": "laneEdge",
                            "data": {"relationship": "TRIGGERED_BY_RECEIVING"},
                        })
                        edge_counter += 1

        else:
            # ── Group-level view (expand_countries=false) ──
            groups_query = """
            MATCH (cg:CountryGroup)
            OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(cg)
            RETURN cg.name as group_name, collect(c.name) as countries
            """
            for row in db.execute_rules_query(groups_query):
                gname = row.get('group_name', '')
                if not gname:
                    continue
                countries = row.get('countries', [])
                gid = f"cg_{gname.replace(' ', '_')}"
                seen_node_ids[f"CountryGroup:{gname}"] = gid
                nodes.append({
                    "id": gid,
                    "type": "countryGroupNode",
                    "data": {
                        "label": gname,
                        "nodeType": "CountryGroup",
                        "lane": "originCountry",
                        "countries": countries,
                        "countryCount": len(countries),
                    },
                    "position": {"x": 0, "y": 0},
                })

            origin_edges_query = """
            MATCH (r:Rule)-[:TRIGGERED_BY_ORIGIN]->(cg:CountryGroup)
            RETURN r.rule_id as rule_id, cg.name as group_name
            """
            origin_groups = set()
            for row in db.execute_rules_query(origin_edges_query):
                rid = row.get('rule_id', '')
                gname = row.get('group_name', '')
                src = seen_node_ids.get(f"CountryGroup:{gname}")
                tgt = seen_node_ids.get(f"Rule:{rid}")
                if src and tgt:
                    origin_groups.add(gname)
                    edges.append({
                        "id": f"e_{edge_counter}",
                        "source": src,
                        "target": tgt,
                        "type": "laneEdge",
                        "data": {"relationship": "TRIGGERED_BY_ORIGIN"},
                    })
                    edge_counter += 1

            receiving_edges_query = """
            MATCH (r:Rule)-[:TRIGGERED_BY_RECEIVING]->(cg:CountryGroup)
            RETURN r.rule_id as rule_id, cg.name as group_name
            """
            receiving_groups = set()
            for row in db.execute_rules_query(receiving_edges_query):
                rid = row.get('rule_id', '')
                gname = row.get('group_name', '')
                src = seen_node_ids.get(f"Rule:{rid}")
                tgt = seen_node_ids.get(f"CountryGroup:{gname}")
                if src and tgt:
                    receiving_groups.add(gname)
                    edges.append({
                        "id": f"e_{edge_counter}",
                        "source": src,
                        "target": tgt,
                        "type": "laneEdge",
                        "data": {"relationship": "TRIGGERED_BY_RECEIVING"},
                    })
                    edge_counter += 1

            # Fix lane assignments for groups
            new_recv_nodes = []
            for n in nodes:
                if n["data"].get("nodeType") == "CountryGroup":
                    gname = n["data"]["label"]
                    is_origin = gname in origin_groups
                    is_receiving = gname in receiving_groups
                    if is_receiving and not is_origin:
                        n["data"]["lane"] = "receivingCountry"
                    elif is_receiving and is_origin:
                        recv_id = f"{n['id']}_recv"
                        new_recv_nodes.append({
                            "id": recv_id,
                            "type": n["type"],
                            "data": {**n["data"], "lane": "receivingCountry"},
                            "position": {"x": 0, "y": 0},
                        })
                        seen_node_ids[f"CountryGroup:{gname}:recv"] = recv_id
                        for e in edges:
                            if (e["data"]["relationship"] == "TRIGGERED_BY_RECEIVING"
                                    and e["target"] == n["id"]):
                                e["target"] = recv_id
            nodes.extend(new_recv_nodes)

        # ── 3. Generic connected node types (loaded from schema metadata) ──
        rel_queries = _get_rel_queries()

        # Group queries by source label for efficient batching
        rule_rel_queries = [(s, r, t, l, rf) for s, r, t, l, rf in rel_queries if s == "Rule"]
        non_rule_rel_queries = [(s, r, t, l, rf) for s, r, t, l, rf in rel_queries if s != "Rule"]

        # ── 3a. Rule-source relationships ──
        for _, rel_type, node_label, lane_id, rf_type in rule_rel_queries:
            query = f"""
            MATCH (r:Rule)-[:{rel_type}]->(n:{node_label})
            RETURN r.rule_id as rule_id, n.name as name
            """
            try:
                results = db.execute_rules_query(query)
            except Exception:
                continue

            for row in results:
                rid = row.get('rule_id', '')
                nname = row.get('name', '')
                if not rid or not nname:
                    continue

                key = f"{node_label}:{nname}"
                if key not in seen_node_ids:
                    nid = f"{node_label.lower()}_{nname.replace(' ', '_')}"
                    seen_node_ids[key] = nid
                    node_data = {
                        "label": nname,
                        "nodeType": node_label,
                        "lane": lane_id,
                    }
                    # Add category for Process nodes
                    if node_label == "Process":
                        try:
                            cat_query = "MATCH (n:Process {name: $name}) RETURN n.category as category"
                            cat_result = db.execute_rules_query(cat_query, {"name": nname})
                            if cat_result:
                                node_data["category"] = cat_result[0].get("category", "")
                        except Exception:
                            pass
                    nodes.append({
                        "id": nid,
                        "type": rf_type,
                        "data": node_data,
                        "position": {"x": 0, "y": 0},
                    })

                src = seen_node_ids.get(f"Rule:{rid}")
                tgt = seen_node_ids[key]
                if src and tgt:
                    edges.append({
                        "id": f"e_{edge_counter}",
                        "source": src,
                        "target": tgt,
                        "type": "laneEdge",
                        "data": {"relationship": rel_type},
                    })
                    edge_counter += 1

        # ── 3b. Non-Rule-source relationships (Country->X, Permission->X, Process->X) ──
        for source_label, rel_type, target_label, lane_id, rf_type in non_rule_rel_queries:
            query = f"""
            MATCH (s:{source_label})-[:{rel_type}]->(t:{target_label})
            RETURN s.name as source_name, t.name as target_name
            """
            try:
                results = db.execute_rules_query(query)
            except Exception:
                continue

            for row in results:
                sname = row.get('source_name', '')
                tname = row.get('target_name', '')
                if not sname or not tname:
                    continue

                # Ensure source node exists (Country nodes may already exist from step 2)
                src_key = f"{source_label}:{sname}"
                if src_key not in seen_node_ids:
                    # Check for lane-specific country keys
                    if source_label == "Country":
                        src_key_origin = f"Country:{sname}:origin"
                        src_key_recv = f"Country:{sname}:recv"
                        if src_key_origin in seen_node_ids:
                            src_key = src_key_origin
                        elif src_key_recv in seen_node_ids:
                            src_key = src_key_recv
                        else:
                            # Create the country node in originCountry lane
                            src_nid = f"country_{sname.replace(' ', '_')}_origin"
                            seen_node_ids[src_key_origin] = src_nid
                            src_key = src_key_origin
                            src_nt = {nt["label"]: nt for nt in load_schema().get("nodeTypes", [])}.get(source_label)
                            nodes.append({
                                "id": src_nid,
                                "type": src_nt["reactFlowType"] if src_nt else "countryNode",
                                "data": {
                                    "label": sname,
                                    "nodeType": source_label,
                                    "lane": "originCountry",
                                },
                                "position": {"x": 0, "y": 0},
                            })
                    else:
                        # Create source node if it doesn't exist
                        src_nt = {nt["label"]: nt for nt in load_schema().get("nodeTypes", [])}.get(source_label)
                        if not src_nt:
                            continue
                        src_nid = f"{source_label.lower()}_{sname.replace(' ', '_')}"
                        seen_node_ids[src_key] = src_nid
                        nodes.append({
                            "id": src_nid,
                            "type": src_nt["reactFlowType"],
                            "data": {
                                "label": sname,
                                "nodeType": source_label,
                                "lane": src_nt["laneId"],
                            },
                            "position": {"x": 0, "y": 0},
                        })

                # Ensure target node exists
                tgt_key = f"{target_label}:{tname}"
                if tgt_key not in seen_node_ids:
                    tgt_nid = f"{target_label.lower()}_{tname.replace(' ', '_')}"
                    seen_node_ids[tgt_key] = tgt_nid
                    nodes.append({
                        "id": tgt_nid,
                        "type": rf_type,
                        "data": {
                            "label": tname,
                            "nodeType": target_label,
                            "lane": lane_id,
                        },
                        "position": {"x": 0, "y": 0},
                    })

                src_id = seen_node_ids.get(src_key)
                tgt_id = seen_node_ids.get(tgt_key)
                if src_id and tgt_id:
                    edges.append({
                        "id": f"e_{edge_counter}",
                        "source": src_id,
                        "target": tgt_id,
                        "type": "laneEdge",
                        "data": {"relationship": rel_type},
                    })
                    edge_counter += 1

        # ── 4. Excludes receiving edges ──
        try:
            if expand_countries:
                # For expanded view, excludes edges point to receiving countries
                excl_query = """
                MATCH (r:Rule)-[:EXCLUDES_RECEIVING]->(cg:CountryGroup)
                OPTIONAL MATCH (c:Country)-[:BELONGS_TO]->(cg)
                RETURN r.rule_id as rule_id, cg.name as group_name, collect(c.name) as countries
                """
                excl_edge_set = set()
                for row in db.execute_rules_query(excl_query):
                    rid = row.get('rule_id', '')
                    src = seen_node_ids.get(f"Rule:{rid}")
                    if not src:
                        continue
                    for country in row.get('countries', []):
                        tgt = seen_node_ids.get(f"Country:{country}:recv")
                        if tgt:
                            edge_key = (src, tgt, "EXCLUDES")
                            if edge_key not in excl_edge_set:
                                excl_edge_set.add(edge_key)
                                edges.append({
                                    "id": f"e_{edge_counter}",
                                    "source": src,
                                    "target": tgt,
                                    "type": "laneEdge",
                                    "data": {"relationship": "EXCLUDES_RECEIVING"},
                                })
                                edge_counter += 1
            else:
                excl_query = """
                MATCH (r:Rule)-[:EXCLUDES_RECEIVING]->(cg:CountryGroup)
                RETURN r.rule_id as rule_id, cg.name as group_name
                """
                for row in db.execute_rules_query(excl_query):
                    rid = row.get('rule_id', '')
                    gname = row.get('group_name', '')
                    src = seen_node_ids.get(f"Rule:{rid}")
                    tgt = (seen_node_ids.get(f"CountryGroup:{gname}:recv")
                           or seen_node_ids.get(f"CountryGroup:{gname}"))
                    if src and tgt:
                        edges.append({
                            "id": f"e_{edge_counter}",
                            "source": src,
                            "target": tgt,
                            "type": "laneEdge",
                            "data": {"relationship": "EXCLUDES_RECEIVING"},
                        })
                        edge_counter += 1
        except Exception:
            pass

        result = {
            "nodes": nodes,
            "edges": edges,
            "lanes": get_all_lanes(),
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            },
        }

        cache.set(cache_key, result, "metadata", ttl=120)
        return result

    except Exception as e:
        logger.error(f"Error fetching editor network: {e}")
        return {
            "nodes": [], "edges": [],
            "lanes": get_all_lanes(),
            "stats": {"total_nodes": 0, "total_edges": 0},
        }


@router.get("/node/{node_id}/neighbors")
async def get_node_neighbors(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=5),
    db=Depends(get_db),
):
    """Get ingress and egress neighbors for a node."""
    try:
        # Find the node by checking common ID patterns
        # node_id format: "rule_RULE_ID" or "cg_GroupName" etc.
        ingress_query = """
        MATCH (source)-[r]->(target)
        WHERE ID(target) = $node_id OR target.name = $name OR target.rule_id = $name
        RETURN source, type(r) as rel_type, target
        LIMIT 50
        """
        egress_query = """
        MATCH (source)-[r]->(target)
        WHERE ID(source) = $node_id OR source.name = $name OR source.rule_id = $name
        RETURN source, type(r) as rel_type, target
        LIMIT 50
        """
        name = _extract_node_name(node_id)
        params = {"node_id": node_id, "name": name}

        ingress = db.execute_rules_query(ingress_query, params)
        egress = db.execute_rules_query(egress_query, params)

        return {"ingress": ingress, "egress": egress}

    except Exception as e:
        logger.error(f"Error fetching neighbors for {node_id}: {e}")
        return {"ingress": [], "egress": []}


@router.get("/path")
async def get_shortest_path(
    source: str = Query(..., description="Source node identifier"),
    target: str = Query(..., description="Target node identifier"),
    db=Depends(get_db),
):
    """Find shortest path between two nodes using BFS."""
    try:
        s_name = _extract_node_name(source)
        t_name = _extract_node_name(target)

        query = """
        MATCH (a), (b)
        WHERE (a.name = $s_name OR a.rule_id = $s_name)
          AND (b.name = $t_name OR b.rule_id = $t_name)
        WITH a, b
        MATCH p = shortestPath((a)-[*..10]-(b))
        RETURN nodes(p) as path_nodes, relationships(p) as path_edges
        LIMIT 1
        """
        result = db.execute_rules_query(query, {
            "s_name": s_name,
            "t_name": t_name,
        })

        if not result:
            raise HTTPException(status_code=404, detail="No path found")

        return {
            "path_nodes": result[0].get("path_nodes", []),
            "path_edges": result[0].get("path_edges", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding path from {source} to {target}: {e}")
        raise HTTPException(status_code=500, detail="Path search failed")
    
    
# ──────────────────────────────────────────────────────────
# CRUD endpoints for Policy Editor
# ──────────────────────────────────────────────────────────

# Protected relationships loaded dynamically from schema metadata
def _get_protected_rels():
    return get_protected_relationships()


def _extract_node_name(node_id: str) -> str:
    """Extract the graph node name from a frontend node_id.

    Handles patterns:
      rule_RULE_1         -> RULE_1  (matched by rule_id)
      country_United_Kingdom_origin -> United Kingdom
      country_United_Kingdom_recv   -> United Kingdom
      cg_EU_EEA           -> EU_EEA
      permission_Transfer  -> Transfer
      duty_Complete_PIA_Module -> Complete PIA Module
      datacategory_Health_Data -> Health Data
    """
    if not node_id:
        return node_id

    # Strip known lane suffixes from country node IDs
    stripped = node_id
    for suffix in ('_origin', '_recv'):
        if stripped.endswith(suffix):
            stripped = stripped[:-len(suffix)]
            break

    # Split off the type prefix (first segment before _)
    parts = stripped.split('_', 1)
    if len(parts) <= 1:
        return node_id

    prefix = parts[0].lower()
    raw_name = parts[1]

    # Rule IDs keep underscores (e.g. RULE_1, RULE_2_EU_ADEQUACY)
    if prefix == 'rule':
        return raw_name

    # CountryGroup names keep underscores (e.g. EU_EEA, BCR_COUNTRIES)
    if prefix == 'cg':
        return raw_name

    # Everything else: replace underscores with spaces
    return raw_name.replace('_', ' ')


class UpdateNodeRequest(BaseModel):
    properties: dict


class CreateNodeRequest(BaseModel):
    label: str
    type: str
    lane: str
    properties: dict = {}


class CreateEdgeRequest(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict = {}


def _invalidate_editor_cache():
    """Invalidate editor network cache after mutations."""
    cache = get_cache_service()
    cache.delete("editor_network_expanded", "metadata")
    cache.delete("editor_network_grouped", "metadata")


@router.put("/editor/node/{node_id}")
async def update_editor_node(
    node_id: str,
    request: UpdateNodeRequest,
    db=Depends(get_db),
):
    """Update node properties in FalkorDB."""
    try:
        name = _extract_node_name(node_id)

        # Build SET clause from properties
        props = request.properties
        if not props:
            raise HTTPException(status_code=400, detail="No properties to update")

        set_clauses = []
        params = {"name": name}
        for i, (key, value) in enumerate(props.items()):
            param_name = f"p{i}"
            set_clauses.append(f"n.{key} = ${param_name}")
            params[param_name] = value

        set_str = ", ".join(set_clauses)
        query = f"""
        MATCH (n)
        WHERE n.name = $name OR n.rule_id = $name
        SET {set_str}
        RETURN n
        """
        result = db.execute_rules_query(query, params)
        if not result:
            raise HTTPException(status_code=404, detail="Node not found")

        _invalidate_editor_cache()
        return {"status": "ok", "updated": len(result)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating node {node_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update node")


@router.delete("/editor/node/{node_id}")
async def delete_editor_node(
    node_id: str,
    db=Depends(get_db),
):
    """Delete a node and its edges from FalkorDB. Blocked if node has protected relationships."""
    try:
        name = _extract_node_name(node_id)

        # Check for protected relationships
        check_query = """
        MATCH (n)-[r]-()
        WHERE n.name = $name OR n.rule_id = $name
        RETURN type(r) as rel_type
        """
        rels = db.execute_rules_query(check_query, {"name": name})
        for rel in rels:
            if rel.get("rel_type") in _get_protected_rels():
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete node with protected relationship: {rel['rel_type']}"
                )

        # Delete node and its edges
        delete_query = """
        MATCH (n)
        WHERE n.name = $name OR n.rule_id = $name
        DETACH DELETE n
        """
        db.execute_rules_query(delete_query, {"name": name})
        _invalidate_editor_cache()
        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting node {node_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete node")


@router.post("/editor/node")
async def create_editor_node(
    request: CreateNodeRequest,
    db=Depends(get_db),
):
    """Create a new node in FalkorDB."""
    try:
        node_label = request.type
        props = {**request.properties, "name": request.label}

        # Build property string
        prop_items = []
        params = {}
        for i, (key, value) in enumerate(props.items()):
            param_name = f"p{i}"
            prop_items.append(f"{key}: ${param_name}")
            params[param_name] = value

        prop_str = ", ".join(prop_items)
        query = f"CREATE (n:{node_label} {{{prop_str}}}) RETURN n"
        result = db.execute_rules_query(query, params)

        _invalidate_editor_cache()
        return {"status": "ok", "created": len(result)}

    except Exception as e:
        logger.error(f"Error creating node: {e}")
        raise HTTPException(status_code=500, detail="Failed to create node")


@router.post("/editor/edge")
async def create_editor_edge(
    request: CreateEdgeRequest,
    db=Depends(get_db),
):
    """Create a new edge between two nodes. Protected relationship types are blocked."""
    if request.relationship_type in _get_protected_rels():
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create protected relationship type: {request.relationship_type}"
        )

    try:
        src_name = _extract_node_name(request.source_id)
        tgt_name = _extract_node_name(request.target_id)

        rel_type = request.relationship_type

        # Build property string for edge
        prop_str = ""
        params = {"src_name": src_name, "tgt_name": tgt_name}
        if request.properties:
            prop_items = []
            for i, (key, value) in enumerate(request.properties.items()):
                param_name = f"ep{i}"
                prop_items.append(f"{key}: ${param_name}")
                params[param_name] = value
            prop_str = f" {{{', '.join(prop_items)}}}"

        query = f"""
        MATCH (a), (b)
        WHERE (a.name = $src_name OR a.rule_id = $src_name)
          AND (b.name = $tgt_name OR b.rule_id = $tgt_name)
        CREATE (a)-[r:{rel_type}{prop_str}]->(b)
        RETURN r
        """
        result = db.execute_rules_query(query, params)
        if not result:
            raise HTTPException(status_code=404, detail="Source or target node not found")

        _invalidate_editor_cache()
        return {"status": "ok", "created": len(result)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating edge: {e}")
        raise HTTPException(status_code=500, detail="Failed to create edge")


@router.delete("/editor/edge/{edge_id}")
async def delete_editor_edge(
    edge_id: str,
    source_name: str = "",
    target_name: str = "",
    relationship_type: str = "",
    db=Depends(get_db),
):
    """Delete an edge. Protected relationship types are blocked.

    The edge_id is synthetic (e.g., "e_0"). Actual deletion uses
    source_name, target_name, and relationship_type query params
    to identify the edge in FalkorDB.
    """
    try:
        # If relationship_type is provided, use it to find and delete the edge
        if relationship_type and source_name and target_name:
            if relationship_type in _get_protected_rels():
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete protected relationship type: {relationship_type}"
                )

            query = f"""
            MATCH (a)-[r:{relationship_type}]->(b)
            WHERE (a.name = $src OR a.rule_id = $src)
              AND (b.name = $tgt OR b.rule_id = $tgt)
            DELETE r
            RETURN count(r) as deleted
            """
            result = db.execute_rules_query(query, {"src": source_name, "tgt": target_name})
            deleted = result[0].get("deleted", 0) if result else 0

            if deleted == 0:
                raise HTTPException(status_code=404, detail="Edge not found")

            _invalidate_editor_cache()
            return {"status": "ok", "deleted": deleted}

        # Fallback: try to extract info from the edge_id composite format
        # Format: "sourceId__relType__targetId"
        if "__" in edge_id:
            parts = edge_id.split("__", 2)
            if len(parts) == 3:
                src, rel_type, tgt = parts
                if rel_type in _get_protected_rels():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete protected relationship type: {rel_type}"
                    )

                src_name = _extract_node_name(src)
                tgt_name = _extract_node_name(tgt)

                query = f"""
                MATCH (a)-[r:{rel_type}]->(b)
                WHERE (a.name = $src OR a.rule_id = $src)
                  AND (b.name = $tgt OR b.rule_id = $tgt)
                DELETE r
                RETURN count(r) as deleted
                """
                result = db.execute_rules_query(query, {"src": src_name, "tgt": tgt_name})
                _invalidate_editor_cache()
                return {"status": "ok", "deleted": result[0].get("deleted", 0) if result else 0}

        raise HTTPException(
            status_code=400,
            detail="Cannot identify edge. Provide source_name, target_name, and relationship_type query params."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting edge {edge_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete edge")
    



# ──────────────────────────────────────────────────────────
# Schema management endpoints
# ──────────────────────────────────────────────────────────

class CreateNodeTypeRequest(BaseModel):
    label: str
    laneId: str
    laneName: str | None = None
    reactFlowType: str = "caseModuleNode"
    properties: list[str] = ["name", "description"]
    primary: bool = False
    order: int | None = None


class CreateRelationshipTypeRequest(BaseModel):
    type: str
    fromLabel: str = "Rule"
    toLabel: str
    protected: bool = False


@router.get("/schema")
async def get_schema():
    """Return the current graph schema metadata."""
    return load_schema()


@router.post("/schema/node-type")
async def create_node_type(
    request: CreateNodeTypeRequest,
    db=Depends(get_db),
):
    """Register a new node type in the schema and create a FalkorDB index."""
    schema = load_schema()

    # Check if label already exists
    existing_labels = {nt["label"] for nt in schema["nodeTypes"]}
    if request.label in existing_labels:
        raise HTTPException(status_code=409, detail=f"Node type '{request.label}' already exists")

    # Determine order
    order = request.order
    if order is None:
        max_order = max((l["order"] for l in schema["lanes"]), default=12)
        order = max_order + 1

    # Add node type
    schema["nodeTypes"].append({
        "label": request.label,
        "laneId": request.laneId,
        "reactFlowType": request.reactFlowType,
        "properties": request.properties,
        "primary": request.primary,
        "order": order,
    })

    # Add lane if laneId doesn't exist yet
    existing_lane_ids = {l["id"] for l in schema["lanes"]}
    if request.laneId not in existing_lane_ids:
        schema["lanes"].append({
            "id": request.laneId,
            "label": request.laneName or request.label,
            "order": order,
            "primary": request.primary,
        })

    save_schema(schema)

    # Create FalkorDB index
    try:
        db.execute_rules_query(f"CREATE INDEX FOR (n:{request.label}) ON (n.name)")
    except Exception as e:
        logger.warning(f"Index creation for {request.label} may have failed (might already exist): {e}")

    _invalidate_editor_cache()
    return {"status": "ok", "label": request.label, "laneId": request.laneId}


@router.post("/schema/relationship-type")
async def create_relationship_type(request: CreateRelationshipTypeRequest):
    """Register a new relationship type in the schema."""
    schema = load_schema()

    existing_types = {rt["type"] for rt in schema["relationshipTypes"]}
    if request.type in existing_types:
        raise HTTPException(status_code=409, detail=f"Relationship type '{request.type}' already exists")

    # Verify from/to labels exist
    existing_labels = {nt["label"] for nt in schema["nodeTypes"]}
    if request.fromLabel not in existing_labels:
        raise HTTPException(status_code=400, detail=f"Source label '{request.fromLabel}' not found in schema")
    if request.toLabel not in existing_labels:
        raise HTTPException(status_code=400, detail=f"Target label '{request.toLabel}' not found in schema")

    schema["relationshipTypes"].append({
        "type": request.type,
        "from": request.fromLabel,
        "to": request.toLabel,
        "protected": request.protected,
    })

    save_schema(schema)
    _invalidate_editor_cache()
    return {"status": "ok", "type": request.type}


@router.delete("/schema/node-type/{label}")
async def delete_node_type(
    label: str,
    db=Depends(get_db),
):
    """Remove a node type from the schema. Fails if nodes of this type exist in the graph."""
    schema = load_schema()

    # Prevent deletion of core types
    core_types = {"Rule", "Country", "CountryGroup"}
    if label in core_types:
        raise HTTPException(status_code=400, detail=f"Cannot delete core node type '{label}'")

    # Check if any nodes exist
    try:
        count_result = db.execute_rules_query(f"MATCH (n:{label}) RETURN count(n) as cnt")
        cnt = count_result[0].get("cnt", 0) if count_result else 0
        if cnt > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete node type '{label}': {cnt} nodes exist. Delete them first."
            )
    except HTTPException:
        raise
    except Exception:
        pass

    # Remove node type
    schema["nodeTypes"] = [nt for nt in schema["nodeTypes"] if nt["label"] != label]

    # Remove associated relationship types
    schema["relationshipTypes"] = [
        rt for rt in schema["relationshipTypes"]
        if rt["from"] != label and rt["to"] != label
    ]

    # Remove lane if no other node types use it
    removed_lane_ids = set()
    for nt in [nt for nt in load_schema()["nodeTypes"] if nt["label"] == label]:
        lane_id = nt["laneId"]
        still_used = any(
            other["laneId"] == lane_id
            for other in schema["nodeTypes"]
        )
        if not still_used:
            schema["lanes"] = [l for l in schema["lanes"] if l["id"] != lane_id]
            removed_lane_ids.add(lane_id)

    save_schema(schema)
    _invalidate_editor_cache()
    return {"status": "ok", "deleted": label, "removedLanes": list(removed_lane_ids)}
