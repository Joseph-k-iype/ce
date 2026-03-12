"""
schema_extract.py
=================
Standalone full extraction of the Compliance Engine's RulesGraph.

Outputs
-------
  falkordb_schema.xlsx   — multi-sheet Excel workbook:
      1. Rules             one row per rule, all fields
      2. Conditions        flattened leaf conditions per rule
      3. Rule Relationships origin/receiving scopes, actions, assessments, attributes
      4. Logic Trees       raw JSON logic_tree + human-readable expression
      5. Node Attributes   graph schema: node labels & their property keys
      6. Graph Topology    source → relationship → target counts
      7. Rel Attributes    properties on relationship types
      8. Policy Schema     glossary: dimensions, outcomes, operators, statuses

  compliance_policies_export.json  — identical to GET /api/admin/export/full

Usage
-----
  python3 schema_extract.py
  python3 schema_extract.py --host localhost --port 6379 --graph RulesGraph
"""

import argparse
import json
import sys
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from datetime import datetime, timezone

import pandas as pd
from falkordb import FalkorDB
from config.settings import settings as _settings

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_HOST       = _settings.database.host
DEFAULT_PORT       = _settings.database.port
DEFAULT_GRAPH      = _settings.database.rules_graph_name
DEFAULT_EXCEL_OUT  = "falkordb_schema.xlsx"
DEFAULT_JSON_OUT   = "compliance_policies_export.json"

# ── policy schema glossary (mirrors _POLICY_SCHEMA in admin.py) ───────────────
POLICY_SCHEMA = {
    "dimensions": {
        "DataCategory":          "Category of personal/sensitive data being processed (e.g. 'Financial Data', 'Health Data')",
        "Purpose":               "Purpose of processing the data (e.g. 'Marketing', 'Fraud Prevention')",
        "Process":               "Business process triggering the data transfer",
        "Regulator":             "Regulatory body governing the rule (e.g. 'GDPR', 'CCPA')",
        "Authority":             "Supervisory authority with jurisdiction",
        "DataSubject":           "Category of individuals whose data is processed (e.g. 'Employee', 'Customer')",
        "SensitiveDataCategory": "Special-category sensitive data (e.g. 'Biometric', 'Genetic')",
        "GDC":                   "Global Data Classification label",
        "OriginCountry":         "Country where the data originates",
        "ReceivingCountry":      "Country receiving the data",
        "LegalEntity":           "Legal entity initiating or receiving the transfer",
    },
    "outcomes": {
        "permission":  "Data transfer is allowed when all conditions are met",
        "prohibition": "Data transfer is blocked when conditions are met",
    },
    "logic_operators": {
        "AND":       "All child conditions must be true",
        "OR":        "At least one child condition must be true",
        "NOT":       "The child condition must be false",
        "CONDITION": "Leaf node — a single dimension/value check",
    },
    "status_values": {
        "draft":     "Rule is being authored and has not been reviewed",
        "submitted": "Rule has been submitted for approval",
        "approved":  "Rule is live and enforced",
        "archived":  "Rule has been retired",
    },
    "priority_levels": ["critical", "high", "medium", "low"],
}


# ── logic tree helpers ─────────────────────────────────────────────────────────

def _flatten_logic_tree(node: dict, conditions: list | None = None) -> list:
    """Return a flat list of every CONDITION leaf node in the tree.

    Each entry: {"dimension": str, "operator": "IN", "values": [str, ...]}
    """
    if conditions is None:
        conditions = []
    if not isinstance(node, dict):
        return conditions
    if node.get("type") == "CONDITION":
        dim = node.get("dimension", "")
        raw_val = node.get("value", "") or ""
        values = [v.strip() for v in raw_val.split(",") if v.strip()]
        if dim:
            conditions.append({"dimension": dim, "operator": "IN", "values": values})
    for child in node.get("children", []):
        _flatten_logic_tree(child, conditions)
    return conditions


def _logic_tree_to_expression(node: dict, depth: int = 0) -> str:
    """Convert a logic tree to a human-readable boolean expression string.

    Example: (DataCategory IN ["Health Data"] AND Purpose IN ["Marketing"])
    """
    if not isinstance(node, dict):
        return ""
    ntype = node.get("type", "AND")
    if ntype == "CONDITION":
        dim = node.get("dimension", "?")
        raw_val = node.get("value", "") or ""
        values = [v.strip() for v in raw_val.split(",") if v.strip()]
        vals_str = ", ".join(f'"{v}"' for v in values) if values else '""'
        return f"{dim} IN [{vals_str}]"
    children = node.get("children", [])
    if not children:
        return f"({ntype})"
    child_exprs = [_logic_tree_to_expression(c, depth + 1) for c in children if isinstance(c, dict)]
    if ntype == "NOT":
        inner = child_exprs[0] if child_exprs else ""
        return f"NOT ({inner})"
    joiner = f" {ntype} "
    expr = joiner.join(child_exprs)
    if depth > 0 or len(child_exprs) > 1:
        expr = f"({expr})"
    return expr


def _parse_logic_tree(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {"type": "AND", "children": []}


# ── FalkorDB query helpers ────────────────────────────────────────────────────

def _rows(result) -> list:
    return result.result_set if result and result.result_set else []


def _col(row, idx, default=None):
    try:
        v = row[idx]
        return v if v is not None else default
    except IndexError:
        return default


# ── extraction functions ───────────────────────────────────────────────────────

def extract_rules(g) -> list[dict]:
    """Fetch all rules with full metadata and linked entities."""
    print("  Extracting rules...")
    query = """
    MATCH (r:Rule)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og)
    OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg)
    OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(pm:Permission)-[:CAN_HAVE_DUTY]->(d:Duty)
    OPTIONAL MATCH (r)-[:HAS_ATTRIBUTE]->(a:Attribute)
    WITH r,
         collect(DISTINCT og.name) AS origin_scopes,
         collect(DISTINCT rg.name) AS receiving_scopes,
         collect(DISTINCT a.name)  AS linked_attributes,
         collect(DISTINCT CASE WHEN d.module IS NOT NULL AND d.module <> 'action' THEN d.module ELSE null END) AS required_assessments,
         collect(DISTINCT CASE WHEN d.module = 'action' THEN d.name ELSE null END) AS required_actions
    RETURN
        r.rule_id              AS rule_id,
        r.name                 AS name,
        r.description          AS description,
        r.rule_type            AS rule_type,
        r.priority             AS priority,
        r.outcome              AS outcome,
        r.status               AS status,
        r.version_id           AS version_id,
        r.workspace_id         AS workspace_id,
        r.enabled              AS enabled,
        r.odrl_type            AS odrl_type,
        r.odrl_action          AS odrl_action,
        r.odrl_target          AS odrl_target,
        r.logic_tree           AS logic_tree,
        r.priority_order       AS priority_order,
        r.valid_from           AS valid_from,
        r.valid_till           AS valid_till,
        r.valid_until          AS valid_until,
        r.has_pii_required     AS requires_pii,
        r.requires_any_data    AS requires_any_data,
        r.requires_personal_data AS requires_personal_data,
        r.origin_match_type    AS origin_match_type,
        r.receiving_match_type AS receiving_match_type,
        r.created_at           AS created_at,
        r.updated_at           AS updated_at,
        origin_scopes, receiving_scopes,
        required_assessments, required_actions, linked_attributes
    ORDER BY priority_order
    """
    rows = _rows(g.query(query))
    cols = [
        "rule_id", "name", "description", "rule_type", "priority", "outcome",
        "status", "version_id", "workspace_id", "enabled",
        "odrl_type", "odrl_action", "odrl_target", "logic_tree", "priority_order",
        "valid_from", "valid_till", "valid_until",
        "requires_pii", "requires_any_data", "requires_personal_data",
        "origin_match_type", "receiving_match_type", "created_at", "updated_at",
        "origin_scopes", "receiving_scopes",
        "required_assessments", "required_actions", "linked_attributes",
    ]
    rules = []
    for row in rows:
        rule = {col: _col(row, i) for i, col in enumerate(cols)}

        # Parse logic tree and enrich
        lt = _parse_logic_tree(rule.get("logic_tree"))
        rule["logic_tree"] = lt
        rule["conditions_flattened"] = _flatten_logic_tree(lt)
        rule["logic_tree_expression"] = _logic_tree_to_expression(lt)

        # Normalise list fields
        for lf in ("origin_scopes", "receiving_scopes", "required_assessments",
                   "required_actions", "linked_attributes"):
            if rule.get(lf) is None:
                rule[lf] = []

        rules.append(rule)

    print(f"    → {len(rules)} rules found")
    return rules


def extract_node_schema(g) -> pd.DataFrame:
    print("  Extracting node schema...")
    query = """
    MATCH (n)
    UNWIND labels(n) AS Label
    UNWIND keys(n) AS Attribute
    RETURN Label, collect(DISTINCT Attribute) AS Properties
    ORDER BY Label
    """
    data = []
    for row in _rows(g.query(query)):
        data.append({"Node Label": _col(row, 0), "Attributes": ", ".join(_col(row, 1, []))})
    return pd.DataFrame(data)


def extract_graph_topology(g) -> pd.DataFrame:
    print("  Extracting graph topology...")
    query = """
    MATCH (a)-[r]->(b)
    UNWIND labels(a) AS SourceLabel
    UNWIND labels(b) AS TargetLabel
    RETURN SourceLabel, type(r) AS RelationshipType, TargetLabel, count(*) AS ConnectionCount
    ORDER BY SourceLabel, RelationshipType
    """
    data = []
    for row in _rows(g.query(query)):
        data.append({
            "Source Node":       _col(row, 0),
            "Relationship Type": _col(row, 1),
            "Target Node":       _col(row, 2),
            "Count":             _col(row, 3),
        })
    return pd.DataFrame(data)


def extract_rel_attributes(g) -> pd.DataFrame:
    print("  Extracting relationship attributes...")
    query = """
    MATCH ()-[r]->()
    UNWIND keys(r) AS Attribute
    RETURN type(r) AS RelationshipType, collect(DISTINCT Attribute) AS Properties
    ORDER BY RelationshipType
    """
    data = []
    for row in _rows(g.query(query)):
        data.append({
            "Relationship Type": _col(row, 0),
            "Attributes":        ", ".join(_col(row, 1, [])),
        })
    return pd.DataFrame(data)


# ── dataframe builders ────────────────────────────────────────────────────────

def build_rules_df(rules: list[dict]) -> pd.DataFrame:
    rows = []
    for r in rules:
        rows.append({
            "rule_id":                r.get("rule_id"),
            "name":                   r.get("name"),
            "description":            r.get("description"),
            "rule_type":              r.get("rule_type"),
            "priority":               r.get("priority"),
            "outcome":                r.get("outcome"),
            "status":                 r.get("status"),
            "version_id":             r.get("version_id"),
            "workspace_id":           r.get("workspace_id"),
            "enabled":                r.get("enabled"),
            "odrl_type":              r.get("odrl_type"),
            "odrl_action":            r.get("odrl_action"),
            "odrl_target":            r.get("odrl_target"),
            "requires_pii":           r.get("requires_pii"),
            "requires_any_data":      r.get("requires_any_data"),
            "requires_personal_data": r.get("requires_personal_data"),
            "valid_from":             r.get("valid_from"),
            "valid_till":             r.get("valid_till") or r.get("valid_until"),
            "created_at":             r.get("created_at"),
            "updated_at":             r.get("updated_at"),
            "origin_match_type":      r.get("origin_match_type"),
            "receiving_match_type":   r.get("receiving_match_type"),
            "logic_tree_expression":  r.get("logic_tree_expression"),
            "logic_tree_json":        json.dumps(r.get("logic_tree", {})),
        })
    return pd.DataFrame(rows)


def build_conditions_df(rules: list[dict]) -> pd.DataFrame:
    rows = []
    for r in rules:
        for c in r.get("conditions_flattened", []):
            rows.append({
                "rule_id":   r.get("rule_id"),
                "rule_name": r.get("name"),
                "dimension": c.get("dimension"),
                "operator":  c.get("operator"),
                "values":    ", ".join(c.get("values", [])),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["rule_id", "rule_name", "dimension", "operator", "values"]
    )


def build_relationships_df(rules: list[dict]) -> pd.DataFrame:
    rows = []
    for r in rules:
        rule_id   = r.get("rule_id")
        rule_name = r.get("name")
        for scope in r.get("origin_scopes", []):
            rows.append({"rule_id": rule_id, "rule_name": rule_name,
                         "relationship": "ORIGIN_SCOPE", "value": scope})
        for scope in r.get("receiving_scopes", []):
            rows.append({"rule_id": rule_id, "rule_name": rule_name,
                         "relationship": "RECEIVING_SCOPE", "value": scope})
        for action in r.get("required_actions", []):
            rows.append({"rule_id": rule_id, "rule_name": rule_name,
                         "relationship": "REQUIRED_ACTION", "value": action})
        for assessment in r.get("required_assessments", []):
            rows.append({"rule_id": rule_id, "rule_name": rule_name,
                         "relationship": "REQUIRED_ASSESSMENT", "value": assessment})
        for attr in r.get("linked_attributes", []):
            rows.append({"rule_id": rule_id, "rule_name": rule_name,
                         "relationship": "LINKED_ATTRIBUTE", "value": attr})
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["rule_id", "rule_name", "relationship", "value"]
    )


def build_logic_trees_df(rules: list[dict]) -> pd.DataFrame:
    rows = []
    for r in rules:
        lt = r.get("logic_tree", {})
        rows.append({
            "rule_id":              r.get("rule_id"),
            "rule_name":            r.get("name"),
            "logic_tree_expression": r.get("logic_tree_expression"),
            "condition_count":      len(r.get("conditions_flattened", [])),
            "logic_tree_json":      json.dumps(lt),
        })
    return pd.DataFrame(rows)


def build_policy_schema_df() -> pd.DataFrame:
    rows = []
    for dim, desc in POLICY_SCHEMA["dimensions"].items():
        rows.append({"section": "dimensions", "key": dim, "description": desc})
    for k, v in POLICY_SCHEMA["outcomes"].items():
        rows.append({"section": "outcomes", "key": k, "description": v})
    for k, v in POLICY_SCHEMA["logic_operators"].items():
        rows.append({"section": "logic_operators", "key": k, "description": v})
    for k, v in POLICY_SCHEMA["status_values"].items():
        rows.append({"section": "status_values", "key": k, "description": v})
    for level in POLICY_SCHEMA["priority_levels"]:
        rows.append({"section": "priority_levels", "key": level, "description": ""})
    return pd.DataFrame(rows)


# ── column width helper ───────────────────────────────────────────────────────

def _autofit(writer):
    for sheet in writer.sheets.values():
        for col in sheet.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=10)
            sheet.column_dimensions[col[0].column_letter].width = min(max_len + 2, 80)


# ── main ──────────────────────────────────────────────────────────────────────

def run(host: str, port: int, graph: str, excel_out: str, json_out: str):
    print(f"Connecting to FalkorDB at {host}:{port}, graph='{graph}' ...")
    db = FalkorDB(
        host=host, port=port,
        username=_settings.database.username,
        password=_settings.database.password
    )
    g  = db.select_graph(graph)
    print("Connected.\n")

    # ── rule / policy data ────────────────────────────────────────────────────
    rules          = extract_rules(g)
    df_rules       = build_rules_df(rules)
    df_conditions  = build_conditions_df(rules)
    df_rule_rels   = build_relationships_df(rules)
    df_logic_trees = build_logic_trees_df(rules)

    # ── raw graph schema ──────────────────────────────────────────────────────
    df_nodes     = extract_node_schema(g)
    df_topology  = extract_graph_topology(g)
    df_rel_attrs = extract_rel_attributes(g)

    # ── glossary ──────────────────────────────────────────────────────────────
    df_schema = build_policy_schema_df()

    # ── write Excel ───────────────────────────────────────────────────────────
    print(f"\nWriting Excel → {excel_out}")
    with pd.ExcelWriter(excel_out, engine="openpyxl") as writer:
        df_rules.to_excel(writer,       sheet_name="Rules",            index=False)
        df_conditions.to_excel(writer,  sheet_name="Conditions",       index=False)
        df_rule_rels.to_excel(writer,   sheet_name="Rule Relationships",index=False)
        df_logic_trees.to_excel(writer, sheet_name="Logic Trees",      index=False)
        df_nodes.to_excel(writer,       sheet_name="Node Attributes",   index=False)
        df_topology.to_excel(writer,    sheet_name="Graph Topology",    index=False)
        df_rel_attrs.to_excel(writer,   sheet_name="Rel Attributes",    index=False)
        df_schema.to_excel(writer,      sheet_name="Policy Schema",     index=False)
        _autofit(writer)
    print(f"  → {len(rules)} rules, 8 sheets written")

    # ── write JSON ────────────────────────────────────────────────────────────
    print(f"Writing JSON  → {json_out}")
    bundle = {
        "format_version": "2.0",
        "exported_at":    datetime.now(timezone.utc).isoformat(),
        "source":         f"falkordb://{host}:{port}/{graph}",
        "total_rules":    len(rules),
        "policy_schema":  POLICY_SCHEMA,
        "rules":          rules,
    }
    with open(json_out, "w") as f:
        json.dump(bundle, f, indent=2, default=str)
    print(f"  → {len(rules)} rules written")

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract full Compliance Engine schema + policies from FalkorDB")
    parser.add_argument("--host",      default=DEFAULT_HOST,      help="FalkorDB host (default: localhost)")
    parser.add_argument("--port",      default=DEFAULT_PORT,      type=int, help="FalkorDB port (default: 6379)")
    parser.add_argument("--graph",     default=DEFAULT_GRAPH,     help="Graph name (default: RulesGraph)")
    parser.add_argument("--excel-out", default=DEFAULT_EXCEL_OUT, help=f"Excel output path (default: {DEFAULT_EXCEL_OUT})")
    parser.add_argument("--json-out",  default=DEFAULT_JSON_OUT,  help=f"JSON output path (default: {DEFAULT_JSON_OUT})")
    args = parser.parse_args()

    try:
        run(args.host, args.port, args.graph, args.excel_out, args.json_out)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
