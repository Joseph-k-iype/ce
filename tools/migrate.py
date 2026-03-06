#!/usr/bin/env python3
"""
Migration CLI — Export/import compliance engine state between environments.

Usage:
  python tools/migrate.py export --env dev --output migration_bundle.json
  python tools/migrate.py import --env uat --input migration_bundle.json --dry-run
  python tools/migrate.py import --env uat --input migration_bundle.json
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _set_env(env_name: str):
    """Set ENV variable so settings.py picks up the right .env.{env} file."""
    os.environ["ENV"] = env_name


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Export ───────────────────────────────────────────────────────────────────

def cmd_export(args):
    env = args.env
    _set_env(env)

    from config.settings import get_settings
    get_settings.cache_clear()
    settings = get_settings()

    from services.database import get_db_service
    from services.operational_store import get_operational_store

    print(f"[export] Connecting to FalkorDB at {settings.database.host}:{settings.database.port}...")
    db = get_db_service()
    if not db.check_connection():
        print("[export] ERROR: Cannot connect to database.", file=sys.stderr)
        sys.exit(1)

    # Export rules from FalkorDB
    print("[export] Fetching rules...")
    rules_raw = db.execute_rules_query("""
        MATCH (r:Rule)
        OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og)
        OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg)
        OPTIONAL MATCH (r)-[:HAS_ATTRIBUTE]->(a:Attribute)
        WITH r,
             collect(DISTINCT og.name) AS origin_scopes,
             collect(DISTINCT rg.name) AS receiving_scopes,
             collect(DISTINCT a.name) AS linked_attributes
        RETURN r.rule_id AS rule_id,
               r.name AS name,
               r.description AS description,
               r.rule_type AS rule_type,
               r.priority AS priority,
               r.outcome AS outcome,
               r.odrl_type AS odrl_type,
               r.odrl_action AS odrl_action,
               r.enabled AS enabled,
               r.logic_tree AS logic_tree,
               r.status AS status,
               r.version_id AS version_id,
               r.valid_from AS valid_from,
               r.valid_till AS valid_till,
               r.valid_until AS valid_until,
               r.workspace_id AS workspace_id,
               r.created_at AS created_at,
               r.updated_at AS updated_at,
               origin_scopes, receiving_scopes, linked_attributes
    """)

    rules = []
    for r in rules_raw:
        rule = dict(r)
        # Parse logic_tree JSON if stored as string
        if isinstance(rule.get("logic_tree"), str):
            try:
                rule["logic_tree"] = json.loads(rule["logic_tree"])
            except Exception:
                pass
        rules.append(rule)
    print(f"[export] Found {len(rules)} rules")

    # Export from operational store
    print("[export] Fetching operational store data...")
    store = get_operational_store()
    store.init()

    workspaces = store.list_workspaces()
    roles = store.list_roles()
    data_sources_raw = store.list_data_sources()
    # Remove auth_config from data sources for security
    data_sources = []
    for ds in data_sources_raw:
        ds_clean = {k: v for k, v in ds.items() if k != "auth_config"}
        data_sources.append(ds_clean)

    bundle = {
        "format_version": "1.0",
        "source_env": env,
        "exported_at": _now(),
        "rules": rules,
        "workspaces": workspaces,
        "roles": roles,
        "data_sources": data_sources,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, default=str)

    print(f"[export] Bundle written to: {output_path}")
    print(f"[export] Summary: {len(rules)} rules, {len(workspaces)} workspaces, {len(roles)} roles, {len(data_sources)} data sources")


# ── Import ───────────────────────────────────────────────────────────────────

def cmd_import(args):
    env = args.env
    dry_run = args.dry_run
    replace = args.replace
    _set_env(env)

    from config.settings import get_settings
    get_settings.cache_clear()
    settings = get_settings()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[import] ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    format_version = bundle.get("format_version", "unknown")
    source_env = bundle.get("source_env", "unknown")
    print(f"[import] Bundle: format={format_version}, source={source_env}, exported={bundle.get('exported_at','?')}")

    if format_version != "1.0":
        print(f"[import] WARNING: Unsupported format version '{format_version}'. Proceeding anyway.")

    from services.database import get_db_service
    from services.operational_store import get_operational_store

    db = get_db_service()
    if not db.check_connection():
        print("[import] ERROR: Cannot connect to database.", file=sys.stderr)
        sys.exit(1)

    store = get_operational_store()
    store.init()

    rules = bundle.get("rules", [])
    workspaces = bundle.get("workspaces", [])
    roles = bundle.get("roles", [])
    data_sources = bundle.get("data_sources", [])

    imported_rules = 0
    skipped_rules = 0
    errors = []

    if dry_run:
        print(f"[import] DRY RUN — no changes will be made")
        print(f"[import] Would import: {len(rules)} rules, {len(workspaces)} workspaces, {len(roles)} roles, {len(data_sources)} data sources")
        return

    # Import workspaces
    print(f"[import] Importing {len(workspaces)} workspaces...")
    for ws in workspaces:
        if ws.get("workspace_id") == "default":
            continue  # always exists
        existing = store.get_workspace(ws["workspace_id"])
        if not existing:
            try:
                store.create_workspace(
                    name=ws["name"],
                    description=ws.get("description", ""),
                    environment=ws.get("environment", env)
                )
            except Exception as e:
                errors.append(f"workspace {ws['name']}: {e}")

    # Import roles (custom only — don't overwrite built-ins)
    print(f"[import] Importing {len(roles)} roles...")
    builtin = {"admin", "editor", "user"}
    for role in roles:
        if role["name"] in builtin:
            continue
        existing = [r for r in store.list_roles() if r["name"] == role["name"]]
        if not existing:
            try:
                store.create_role(role["name"], role.get("permissions", []))
            except Exception as e:
                errors.append(f"role {role['name']}: {e}")

    # Import rules via Cypher MERGE (upsert by rule_id)
    print(f"[import] Importing {len(rules)} rules...")
    now = _now()
    today = datetime.now(timezone.utc).date().isoformat()
    for rule in rules:
        rule_id = rule.get("rule_id")
        if not rule_id:
            errors.append("rule missing rule_id — skipped")
            skipped_rules += 1
            continue
        try:
            logic_tree_str = json.dumps(rule.get("logic_tree") or {"type": "AND", "children": []})
            db.execute_rules_query("""
                MERGE (r:Rule {rule_id: $rule_id})
                SET r.name = $name,
                    r.description = $description,
                    r.rule_type = $rule_type,
                    r.priority = $priority,
                    r.outcome = $outcome,
                    r.odrl_type = $odrl_type,
                    r.odrl_action = $odrl_action,
                    r.enabled = $enabled,
                    r.logic_tree = $logic_tree,
                    r.status = 'draft',
                    r.version_id = coalesce(r.version_id, 0) + 1,
                    r.valid_from = $valid_from,
                    r.workspace_id = $workspace_id,
                    r.created_at = coalesce(r.created_at, $now),
                    r.updated_at = $now
            """, {
                "rule_id": rule_id,
                "name": rule.get("name", "Imported Rule"),
                "description": rule.get("description", ""),
                "rule_type": rule.get("rule_type", "case_matching"),
                "priority": rule.get("priority", "medium"),
                "outcome": rule.get("outcome", "permission"),
                "odrl_type": rule.get("odrl_type", "Permission"),
                "odrl_action": rule.get("odrl_action", "transfer"),
                "enabled": rule.get("enabled", True),
                "logic_tree": logic_tree_str,
                "valid_from": rule.get("valid_from") or today,
                "workspace_id": rule.get("workspace_id", "default"),
                "now": now,
            })
            imported_rules += 1
        except Exception as e:
            errors.append(f"rule {rule_id}: {e}")
            skipped_rules += 1

    print(f"[import] Rules: {imported_rules} imported, {skipped_rules} skipped")
    if errors:
        print(f"[import] Errors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
    else:
        print(f"[import] Complete — no errors")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Compliance Engine Migration Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # export
    exp = subparsers.add_parser("export", help="Export state to a migration bundle JSON")
    exp.add_argument("--env", required=True, help="Source environment name (dev|uat|prod)")
    exp.add_argument("--output", required=True, help="Output JSON file path")

    # import
    imp = subparsers.add_parser("import", help="Import a migration bundle into an environment")
    imp.add_argument("--env", required=True, help="Target environment name (dev|uat|prod)")
    imp.add_argument("--input", required=True, help="Input JSON bundle file path")
    imp.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    imp.add_argument("--replace", action="store_true", help="Replace existing records instead of merging")

    args = parser.parse_args()
    if args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)


if __name__ == "__main__":
    main()
