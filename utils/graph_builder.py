"""
Graph Builder
=============
Builds the RulesGraph from rule definitions — the single source of truth.

RulesGraph Schema:
- Country: name, iso2, iso3, rtn_code
- CountryGroup: name
- LegalEntity: name, country
- Rule: rule_id, rule_type, name, description, priority, priority_order,
        origin_match_type, receiving_match_type, outcome,
        odrl_type, odrl_action, odrl_target,
        has_pii_required, requires_any_data, requires_personal_data,
        valid_until, enabled
- Action: name
- Permission: name
- Prohibition: name
- Duty: name, module, value
- Process: name, definition, global_business_function, process_level_indicator,
           level_1_name, level_2_name, level_3_name
- PurposeOfProcessing: name, description
- DataSubject: name, definition
- GDC: name, definition, data_domain, data_privacy_indicator, gdc_level_2, gdc_level_3
- DataCategory: name, definition, gdpr_category_name
- SensitiveDataCategory: name, definition, country_code, sensitive_data_category_name
- Regulator: name, country_code, region, regulator_type, regulator_definition,
             regulator_address, notification_m, notification_nm, approval_m, approval_nm,
             approval_time, internal_engagement, automated_notification,
             regulator_original_name
- Authority: name, country_code
- GlobalBusinessFunction: name, rtn_code, gbgf_level_1, privacy_notice, gbgf_level_2
- Attribute: name

Relationships:
- Country -[:BELONGS_TO]-> CountryGroup
- Country -[:HAS_LEGAL_ENTITY]-> LegalEntity
- Country -[:HAS_REGULATOR]-> Regulator
- Country -[:HAS_AUTHORITY]-> Authority
- Country -[:HAS_GBGF]-> GlobalBusinessFunction
- Country -[:HAS_SENSITIVE_DATA_CATEGORY]-> SensitiveDataCategory
- Rule -[:TRIGGERED_BY_ORIGIN]-> CountryGroup | Country | LegalEntity
- Rule -[:TRIGGERED_BY_RECEIVING]-> CountryGroup | Country | LegalEntity
- Rule -[:EXCLUDES_RECEIVING]-> CountryGroup
- Rule -[:ORIGINATES_FROM]-> Country
- Rule -[:RECEIVED_IN]-> Country
- Rule -[:HAS_ACTION]-> Action
- Rule -[:HAS_PERMISSION]-> Permission
- Rule -[:HAS_PROHIBITION]-> Prohibition
- Permission -[:CAN_HAVE_DUTY]-> Duty
  (Prohibitions do NOT have duties)
- Rule -[:HAS_DATA_CATEGORY]-> DataCategory
- Rule -[:HAS_PURPOSE]-> PurposeOfProcessing
- Rule -[:HAS_PROCESS]-> Process
- Rule -[:HAS_GDC]-> GDC
- Rule -[:HAS_ATTRIBUTE]-> Attribute
- Rule -[:LINKED_TO]-> Regulator|Authority|PurposeOfProcessing|DataCategory|
                        SensitiveDataCategory|Process|GDC|DataSubject|
                        LegalEntity|GlobalBusinessFunction
- Process -[:HAS_SUBPROCESS]-> Process
- Process -[:BELONGS_TO_GBGF]-> GlobalBusinessFunction
"""

import csv
import json
import logging
from typing import Set, Dict, Any, List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.database import get_db_service
from services.cache import get_cache_service
from rules.dictionaries.country_groups import COUNTRY_GROUPS, get_all_countries
from rules.dictionaries.rules_definitions import (
    get_enabled_case_matching_rules,
    PRIORITY_ORDER,
)
from config.settings import settings

logger = logging.getLogger(__name__)

# Map priority string to integer for graph sorting
def _priority_order(priority: str) -> int:
    return PRIORITY_ORDER.get(priority, 2)


def validate_csv_schema(
    csv_file: Path,
    required_cols: List[str],
    optional_cols: List[str] | None = None,
) -> List[str]:
    """Validate CSV file has required columns. Returns list of error strings (empty = valid)."""
    errors: List[str] = []
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            for col in required_cols:
                if col not in headers:
                    errors.append(f"Missing required column '{col}' in {csv_file.name}")
    except Exception as e:
        errors.append(f"Failed to read {csv_file.name}: {e}")
    return errors


def _csv_dir() -> Path:
    return Path(__file__).parent.parent / "rules" / "data_dictionaries" / "csv"


def _read_csv(filename: str) -> List[Dict[str, str]]:
    """Read a CSV file from the data_dictionaries/csv directory."""
    csv_file = _csv_dir() / filename
    if not csv_file.exists():
        logger.warning(f"CSV file not found: {csv_file}")
        return []
    rows = []
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {}
                for k, v in row.items():
                    if k is None:
                        # Extra columns beyond headers — skip
                        continue
                    if isinstance(v, str):
                        cleaned[k] = v.strip()
                    elif v is None:
                        cleaned[k] = ''
                    else:
                        # Non-string (e.g. list from restkey) — skip
                        cleaned[k] = str(v).strip() if v else ''
                rows.append(cleaned)
    except Exception as e:
        logger.error(f"Failed to read {filename}: {e}")
    return rows


class RulesGraphBuilder:
    """Builds the RulesGraph — the single source of truth for all rule evaluation."""

    def __init__(self, graph=None):
        self.db = get_db_service()
        self.graph = graph if graph is not None else self.db.get_rules_graph()
        self._created_duties: Set[str] = set()
        self._created_countries: Set[str] = set()
        self._created_legal_entities: Set[str] = set()

    def _invalidate_cache(self):
        """Clear rules and queries caches after graph mutations."""
        try:
            cache = get_cache_service()
            cache.clear("rules")
            cache.clear("queries")
            cache.clear("metadata")
            logger.debug("Cache invalidated after graph mutation")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

    def build(self, clear_existing: bool = True):
        """Build the complete RulesGraph."""
        logger.info("Building RulesGraph...")

        if clear_existing:
            self._clear_graph()

        self._create_indexes()
        self._build_countries_from_csv()
        self._build_country_groups()
        self._build_countries_from_groups()
        self._build_legal_entities_v2()
        self._build_regulators()
        self._build_authorities()
        self._build_global_business_functions()
        self._build_actions()
        self._build_case_matching_rules()
        self._ingest_data_dictionaries_v2()

        logger.info("RulesGraph build complete!")
        self._print_stats()
        self._invalidate_cache()

    def build_incremental(self):
        """Build the RulesGraph incrementally — no clearing, uses MERGE for all operations."""
        logger.info("Building RulesGraph incrementally (no clear)...")

        self._create_indexes()
        self._build_countries_from_csv()
        self._build_country_groups_merge()
        self._build_countries_from_groups_merge()
        self._build_legal_entities_v2()
        self._build_regulators()
        self._build_authorities()
        self._build_global_business_functions()
        self._build_actions_merge()
        self._build_case_matching_rules()
        self._ingest_data_dictionaries_v2()

        logger.info("RulesGraph incremental build complete!")
        self._print_stats()
        self._invalidate_cache()

    def _clear_graph(self):
        logger.info("Clearing existing RulesGraph data...")
        try:
            self.graph.query("MATCH (n) DETACH DELETE n")
        except Exception as e:
            logger.warning(f"Error clearing graph: {e}")

    def _create_indexes(self):
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Country) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Country) ON (n.iso2)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Country) ON (n.iso3)",
            "CREATE INDEX IF NOT EXISTS FOR (n:CountryGroup) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:LegalEntity) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Rule) ON (n.rule_id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Action) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Permission) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Prohibition) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Duty) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Process) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:PurposeOfProcessing) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:DataSubject) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:GDC) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:DataCategory) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:SensitiveDataCategory) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Attribute) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Regulator) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Authority) ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:GlobalBusinessFunction) ON (n.name)",
            # Keep old Purpose index for backward compatibility during migration
            "CREATE INDEX IF NOT EXISTS FOR (n:Purpose) ON (n.name)",
        ]
        for index in indexes:
            try:
                self.graph.query(index)
            except Exception as e:
                logger.debug(f"Index creation note: {e}")

    # -------------------------------------------------------------------------
    # Countries — from CSV (with iso2, iso3, rtn_code)
    # -------------------------------------------------------------------------

    def _build_countries_from_csv(self):
        """Build Country nodes from countries.csv with ISO codes and RTN codes."""
        rows = _read_csv("countries.csv")
        if not rows:
            logger.info("No countries.csv found, will use country_groups fallback")
            return

        count = 0
        for row in rows:
            name = row.get('country_name', '')
            iso2 = row.get('iso_2', '')
            iso3 = row.get('iso_3', '')
            rtn_code = row.get('rtn_code', '')
            if not name:
                continue

            self.graph.query("""
            MERGE (c:Country {name: $name})
            SET c.iso2 = $iso2, c.iso3 = $iso3, c.rtn_code = $rtn_code
            """, {"name": name, "iso2": iso2, "iso3": iso3, "rtn_code": rtn_code})
            self._created_countries.add(name)
            count += 1

        logger.info(f"Merged {count} country nodes from countries.csv")

    def _build_country_groups(self):
        logger.info("Building country groups...")
        for group_name in COUNTRY_GROUPS.keys():
            self.graph.query("CREATE (g:CountryGroup {name: $name})", {"name": group_name})
        logger.info(f"Created {len(COUNTRY_GROUPS)} country groups")

    def _build_country_groups_merge(self):
        logger.info("Building country groups (merge)...")
        for group_name in COUNTRY_GROUPS.keys():
            self.graph.query("MERGE (g:CountryGroup {name: $name})", {"name": group_name})
        logger.info(f"Merged {len(COUNTRY_GROUPS)} country groups")

    def _build_countries_from_groups(self):
        """Build/link countries from country_groups that weren't in CSV."""
        logger.info("Building countries from country groups...")
        all_countries = get_all_countries()
        new_count = 0
        for country in all_countries:
            if country not in self._created_countries:
                self.graph.query("CREATE (c:Country {name: $name})", {"name": country})
                self._created_countries.add(country)
                new_count += 1
            for group_name, group_countries in COUNTRY_GROUPS.items():
                if country in group_countries:
                    self.graph.query("""
                    MATCH (c:Country {name: $country})
                    MATCH (g:CountryGroup {name: $group})
                    CREATE (c)-[:BELONGS_TO]->(g)
                    """, {"country": country, "group": group_name})
        logger.info(f"Created {new_count} additional country nodes from groups, linked all to groups")

    def _build_countries_from_groups_merge(self):
        """Build/link countries from country_groups (merge mode)."""
        logger.info("Building countries from country groups (merge)...")
        all_countries = get_all_countries()
        for country in all_countries:
            if country not in self._created_countries:
                self.graph.query("MERGE (c:Country {name: $name})", {"name": country})
                self._created_countries.add(country)
            for group_name, group_countries in COUNTRY_GROUPS.items():
                if country in group_countries:
                    self.graph.query("""
                    MATCH (c:Country {name: $country})
                    MATCH (g:CountryGroup {name: $group})
                    MERGE (c)-[:BELONGS_TO]->(g)
                    """, {"country": country, "group": group_name})
        logger.info(f"Merged country nodes from groups")

    def _ensure_country(self, country_name: str):
        """Create a Country node if it doesn't already exist in the graph."""
        if country_name not in self._created_countries:
            self.graph.query("MERGE (c:Country {name: $name})", {"name": country_name})
            self._created_countries.add(country_name)

    # -------------------------------------------------------------------------
    # Legal Entities — from CSV (new schema: id, name)
    # -------------------------------------------------------------------------

    def _build_legal_entities_v2(self):
        """Load legal entities from legal_entities.csv and link via countries.csv."""
        logger.info("Building legal entities...")

        # First, ingest standalone legal entity nodes
        le_rows = _read_csv("legal_entities.csv")
        le_count = 0
        for row in le_rows:
            name = row.get('name', '')
            if not name:
                continue
            self.graph.query("MERGE (le:LegalEntity {name: $name})", {"name": name})
            le_count += 1

        # Then link via countries.csv (country → HAS_LEGAL_ENTITY → legal entity)
        country_rows = _read_csv("countries.csv")
        link_count = 0
        for row in country_rows:
            country_name = row.get('country_name', '')
            le_name = row.get('legal_entity_name', '')
            if not country_name or not le_name:
                continue
            self._ensure_country(country_name)
            # Ensure the LE exists (it may come from countries.csv but not be in legal_entities.csv)
            self.graph.query("MERGE (le:LegalEntity {name: $name})", {"name": le_name})
            self.graph.query("""
            MATCH (c:Country {name: $country})
            MATCH (le:LegalEntity {name: $le_name})
            MERGE (c)-[:HAS_LEGAL_ENTITY]->(le)
            """, {"country": country_name, "le_name": le_name})
            link_count += 1

        logger.info(f"Merged {le_count} legal entity nodes, linked {link_count} to countries")

    # -------------------------------------------------------------------------
    # Regulators — from CSV
    # -------------------------------------------------------------------------

    def _build_regulators(self):
        """Build Regulator nodes from regulators.csv and link to countries."""
        logger.info("Building regulators...")
        rows = _read_csv("regulators.csv")
        count = 0
        for row in rows:
            name = row.get('regulator_name', '')
            country_code = row.get('country_code_iso_2', '')
            if not name:
                continue

            self.graph.query("""
            MERGE (reg:Regulator {name: $name})
            SET reg.country_code = $country_code,
                reg.region = $region,
                reg.regulator = $regulator,
                reg.regulator_type = $regulator_type,
                reg.regulator_definition = $regulator_definition,
                reg.regulator_address = $regulator_address,
                reg.regulator_original_name = $regulator_original_name,
                reg.notification_m = $notification_m,
                reg.notification_nm = $notification_nm,
                reg.approval_m = $approval_m,
                reg.approval_nm = $approval_nm,
                reg.approval_time = $approval_time,
                reg.internal_engagement = $internal_engagement,
                reg.automated_notification = $automated_notification
            """, {
                "name": name,
                "country_code": country_code,
                "region": row.get('region', ''),
                "regulator": row.get('regulator', ''),
                "regulator_type": row.get('regulator_type', ''),
                "regulator_definition": row.get('regulator_definition', ''),
                "regulator_address": row.get('regulator_address', ''),
                "regulator_original_name": row.get('regulator_original_name', ''),
                "notification_m": row.get('notification_m', ''),
                "notification_nm": row.get('notification_nm', ''),
                "approval_m": row.get('approval_m', ''),
                "approval_nm": row.get('approval_nm', ''),
                "approval_time": row.get('approval_time', ''),
                "internal_engagement": row.get('internal_engagement', ''),
                "automated_notification": row.get('automated_notification', ''),
            })

            # Link to country via ISO 2 code
            if country_code:
                self.graph.query("""
                MATCH (c:Country)
                WHERE c.iso2 = $iso2 OR c.name = $iso2
                MATCH (reg:Regulator {name: $reg_name})
                MERGE (c)-[:HAS_REGULATOR]->(reg)
                """, {"iso2": country_code, "reg_name": name})
            count += 1

        logger.info(f"Merged {count} regulator nodes")

    # -------------------------------------------------------------------------
    # Authorities — from CSV
    # -------------------------------------------------------------------------

    def _build_authorities(self):
        """Build Authority nodes from authorities.csv and link to countries."""
        logger.info("Building authorities...")
        rows = _read_csv("authorities.csv")
        count = 0
        for row in rows:
            name = row.get('name', '')
            country_code = row.get('country_code_iso_2', '')
            if not name:
                continue

            self.graph.query("""
            MERGE (auth:Authority {name: $name})
            SET auth.country_code = $country_code
            """, {"name": name, "country_code": country_code})

            if country_code:
                self.graph.query("""
                MATCH (c:Country)
                WHERE c.iso2 = $iso2 OR c.name = $iso2
                MATCH (auth:Authority {name: $auth_name})
                MERGE (c)-[:HAS_AUTHORITY]->(auth)
                """, {"iso2": country_code, "auth_name": name})
            count += 1

        logger.info(f"Merged {count} authority nodes")

    # -------------------------------------------------------------------------
    # Global Business Functions — from CSV
    # -------------------------------------------------------------------------

    def _build_global_business_functions(self):
        """Build GlobalBusinessFunction nodes from global_business_functions.csv."""
        logger.info("Building global business functions...")
        rows = _read_csv("global_business_functions.csv")
        count = 0
        for row in rows:
            name = row.get('name', '')
            rtn_code = row.get('rtn_code', '')
            if not name:
                continue

            self.graph.query("""
            MERGE (gbgf:GlobalBusinessFunction {name: $name})
            SET gbgf.rtn_code = $rtn_code,
                gbgf.gbgf_level_1 = $gbgf_level_1,
                gbgf.privacy_notice = $privacy_notice,
                gbgf.gbgf_level_2 = $gbgf_level_2
            """, {
                "name": name,
                "rtn_code": rtn_code,
                "gbgf_level_1": row.get('gbgf_level_1', ''),
                "privacy_notice": row.get('privacy_notice', ''),
                "gbgf_level_2": row.get('gbgf_level_2', ''),
            })

            # Link countries to GBGF via matching RTN code
            if rtn_code:
                self.graph.query("""
                MATCH (c:Country)
                WHERE c.rtn_code IS NOT NULL AND c.rtn_code <> ''
                MATCH (gbgf:GlobalBusinessFunction {name: $name})
                MERGE (c)-[:HAS_GBGF]->(gbgf)
                """, {"name": name})
            count += 1

        logger.info(f"Merged {count} global business function nodes")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def _build_actions(self):
        logger.info("Building actions...")
        actions = [
            "Transfer Data", "Transfer PII", "Store in Cloud", "Process Data",
            "Anonymisation", "Consent", "Consult/Approve Legal",
            "Consult/Approve Risk and Compliance", "Notification to Regulator",
            "Privacy Notice", "Local Authority/Regulatory Approval",
            "Enhanced Technical and Organisational Security Measures",
            "Public Availability", "Services Agreement", "Storage Limitation",
            "Outsourcing Agreement", "Explicit Consent",
        ]
        for name in actions:
            self.graph.query("CREATE (a:Action {name: $name})", {"name": name})
        logger.info(f"Created {len(actions)} action nodes")

    def _build_actions_merge(self):
        logger.info("Building actions (merge)...")
        actions = [
            "Transfer Data", "Transfer PII", "Store in Cloud", "Process Data",
            "Anonymisation", "Consent", "Consult/Approve Legal",
            "Consult/Approve Risk and Compliance", "Notification to Regulator",
            "Privacy Notice", "Local Authority/Regulatory Approval",
            "Enhanced Technical and Organisational Security Measures",
            "Public Availability", "Services Agreement", "Storage Limitation",
            "Outsourcing Agreement", "Explicit Consent",
        ]
        for name in actions:
            self.graph.query("MERGE (a:Action {name: $name})", {"name": name})
        logger.info(f"Merged {len(actions)} action nodes")

    def _create_duty(self, name: str, module: str, value: str):
        duty_key = f"{name}:{module}:{value}"
        if duty_key not in self._created_duties:
            self.graph.query("""
            MERGE (d:Duty {name: $name, module: $module, value: $value})
            """, {"name": name, "module": module, "value": value})
            self._created_duties.add(duty_key)

    # -------------------------------------------------------------------------
    # Case-Matching Rules
    # -------------------------------------------------------------------------

    def _build_case_matching_rules(self):
        logger.info("Building case-matching rules...")
        rules = get_enabled_case_matching_rules()

        for rule_key, rule in rules.items():
            origin_match_type = "group" if rule.origin_group else ("specific" if rule.origin_countries else "any")
            receiving_match_type = (
                "not_in" if rule.receiving_not_in else
                "group" if rule.receiving_group else
                ("specific" if rule.receiving_countries else "any")
            )

            self.graph.query("""
            MERGE (r:Rule {rule_id: $rule_id})
            SET r.rule_type = 'case_matching',
                r.name = $name,
                r.description = $description,
                r.priority = $priority,
                r.priority_order = $priority_order,
                r.origin_match_type = $origin_match_type,
                r.receiving_match_type = $receiving_match_type,
                r.outcome = 'permission',
                r.odrl_type = $odrl_type,
                r.odrl_action = $odrl_action,
                r.odrl_target = $odrl_target,
                r.has_pii_required = $has_pii_required,
                r.requires_any_data = false,
                r.requires_personal_data = $requires_personal_data,
                r.enabled = true
            """, {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "priority": rule.priority,
                "priority_order": _priority_order(rule.priority),
                "origin_match_type": origin_match_type,
                "receiving_match_type": receiving_match_type,
                "odrl_type": rule.odrl_type,
                "odrl_action": rule.odrl_action,
                "odrl_target": rule.odrl_target,
                "has_pii_required": rule.requires_pii,
                "requires_personal_data": rule.requires_personal_data,
            })

            # Permission + Duties (assessments)
            perm_name = f"Transfer Permission ({rule.name})"
            self.graph.query("""
            MATCH (r:Rule {rule_id: $rule_id})
            MERGE (p:Permission {name: $name})
            MERGE (r)-[:HAS_PERMISSION]->(p)
            """, {"rule_id": rule.rule_id, "name": perm_name})

            for assessment in rule.required_assessments.to_list():
                duty_name = f"Complete {assessment} Module"
                self._create_duty(duty_name, assessment, "Completed")
                self.graph.query("""
                MATCH (p:Permission {name: $perm_name})
                MATCH (d:Duty {name: $duty_name, module: $module, value: $value})
                MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                """, {"perm_name": perm_name, "duty_name": duty_name, "module": assessment, "value": "Completed"})

            # Origin relationships
            if rule.origin_group:
                self.graph.query("""
                MATCH (r:Rule {rule_id: $rule_id})
                MATCH (g:CountryGroup {name: $group})
                MERGE (r)-[:TRIGGERED_BY_ORIGIN]->(g)
                """, {"rule_id": rule.rule_id, "group": rule.origin_group})

            if rule.origin_countries:
                for country in rule.origin_countries:
                    self._ensure_country(country)
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (c:Country {name: $country})
                    MERGE (r)-[:TRIGGERED_BY_ORIGIN]->(c)
                    """, {"rule_id": rule.rule_id, "country": country})

            # Receiving relationships
            if rule.receiving_group:
                self.graph.query("""
                MATCH (r:Rule {rule_id: $rule_id})
                MATCH (g:CountryGroup {name: $group})
                MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(g)
                """, {"rule_id": rule.rule_id, "group": rule.receiving_group})

            if rule.receiving_countries:
                for country in rule.receiving_countries:
                    self._ensure_country(country)
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (c:Country {name: $country})
                    MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(c)
                    """, {"rule_id": rule.rule_id, "country": country})

            # Receiving exclusion
            if rule.receiving_not_in:
                for group_marker in rule.receiving_not_in:
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (g:CountryGroup {name: $group})
                    MERGE (r)-[:EXCLUDES_RECEIVING]->(g)
                    """, {"rule_id": rule.rule_id, "group": group_marker})

            # Link to Action
            self.graph.query("""
            MATCH (r:Rule {rule_id: $rule_id})
            MATCH (a:Action {name: 'Transfer Data'})
            MERGE (r)-[:HAS_ACTION]->(a)
            """, {"rule_id": rule.rule_id})

        logger.info(f"Created {len(rules)} case-matching rules")

    # -------------------------------------------------------------------------
    # Data Dictionary Ingestion v2 (all 11 CSVs)
    # -------------------------------------------------------------------------

    def _ingest_data_dictionaries_v2(self):
        """Load all data dictionaries from CSV files."""
        logger.info("Ingesting data dictionaries v2...")

        self._ingest_purpose_of_processing()
        self._ingest_data_categories()
        self._ingest_sensitive_data_categories()
        self._ingest_processes()
        self._ingest_data_subjects()
        self._ingest_gdc()

    def _ingest_purpose_of_processing(self):
        """Ingest purpose_of_processing.csv into PurposeOfProcessing nodes."""
        rows = _read_csv("purpose_of_processing.csv")
        count = 0
        for row in rows:
            name = row.get('name', '')
            if not name:
                continue
            self.graph.query("""
            MERGE (p:PurposeOfProcessing {name: $name})
            SET p.description = $description
            """, {"name": name, "description": row.get('description', '')})
            # Also create backward-compatible Purpose node
            self.graph.query("MERGE (p:Purpose {name: $name})", {"name": name})
            count += 1
        logger.info(f"Ingested {count} PurposeOfProcessing nodes")

    def _ingest_data_categories(self):
        """Ingest data_categories.csv into DataCategory nodes."""
        rows = _read_csv("data_categories.csv")
        count = 0
        for row in rows:
            name = row.get('name', '')
            if not name:
                continue
            self.graph.query("""
            MERGE (dc:DataCategory {name: $name})
            SET dc.definition = $definition,
                dc.gdpr_category_name = $gdpr_category_name
            """, {
                "name": name,
                "definition": row.get('definition', ''),
                "gdpr_category_name": row.get('gdpr_category_name', ''),
            })
            count += 1
        logger.info(f"Ingested {count} DataCategory nodes")

    def _ingest_sensitive_data_categories(self):
        """Ingest sensitive_data_categories.csv and link to countries."""
        rows = _read_csv("sensitive_data_categories.csv")
        count = 0
        for row in rows:
            name = row.get('name', '')
            country_code = row.get('country_code', '')
            if not name:
                continue
            self.graph.query("""
            MERGE (sdc:SensitiveDataCategory {name: $name, country_code: $country_code})
            SET sdc.definition = $definition,
                sdc.sensitive_data_category_name = $sensitive_data_category_name
            """, {
                "name": name,
                "country_code": country_code,
                "definition": row.get('definition', ''),
                "sensitive_data_category_name": row.get('sensitive_data_category_name', ''),
            })

            if country_code:
                self.graph.query("""
                MATCH (c:Country)
                WHERE c.iso2 = $iso2 OR c.name = $iso2
                MATCH (sdc:SensitiveDataCategory {name: $name, country_code: $country_code})
                MERGE (c)-[:HAS_SENSITIVE_DATA_CATEGORY]->(sdc)
                """, {"iso2": country_code, "name": name, "country_code": country_code})
            count += 1
        logger.info(f"Ingested {count} SensitiveDataCategory nodes")

    def _ingest_processes(self):
        """Ingest processes.csv with hierarchy and GBGF linkage."""
        rows = _read_csv("processes.csv")
        count = 0
        l1_created: Set[str] = set()

        for row in rows:
            name = row.get('name', '')
            if not name:
                continue

            gbgf = row.get('global_business_function', '')
            level_indicator = row.get('process_level_indicator', '')
            l1_name = row.get('level_1_name', '')
            l2_name = row.get('level_2_name', '')
            l3_name = row.get('level_3_name', '')

            self.graph.query("""
            MERGE (p:Process {name: $name})
            SET p.definition = $definition,
                p.global_business_function = $gbgf,
                p.process_level_indicator = $level_indicator,
                p.level_1_name = $l1_name,
                p.level_2_name = $l2_name,
                p.level_3_name = $l3_name,
                p.category = $l1_name,
                p.l1 = $l1_name,
                p.l2 = $l2_name,
                p.l3 = $l3_name
            """, {
                "name": name,
                "definition": row.get('definition', ''),
                "gbgf": gbgf,
                "level_indicator": level_indicator,
                "l1_name": l1_name,
                "l2_name": l2_name,
                "l3_name": l3_name,
            })
            count += 1

            # Build L1 parent node and HAS_SUBPROCESS relationship
            if l1_name and l1_name != name:
                if l1_name not in l1_created:
                    self.graph.query("""
                    MERGE (p:Process {name: $name})
                    SET p.category = $name, p.l1 = $name,
                        p.process_level_indicator = 'L1',
                        p.global_business_function = $gbgf
                    """, {"name": l1_name, "gbgf": gbgf})
                    l1_created.add(l1_name)

                self.graph.query("""
                MATCH (parent:Process {name: $parent_name})
                MATCH (child:Process {name: $child_name})
                MERGE (parent)-[:HAS_SUBPROCESS]->(child)
                """, {"parent_name": l1_name, "child_name": name})

            # Link process to GBGF
            if gbgf:
                self.graph.query("""
                MATCH (p:Process {name: $proc_name})
                MATCH (gbgf:GlobalBusinessFunction {name: $gbgf_name})
                MERGE (p)-[:BELONGS_TO_GBGF]->(gbgf)
                """, {"proc_name": name, "gbgf_name": gbgf})

        logger.info(f"Ingested {count} Process nodes")

    def _ingest_data_subjects(self):
        """Ingest data_subjects.csv into DataSubject nodes."""
        rows = _read_csv("data_subjects.csv")
        count = 0
        for row in rows:
            name = row.get('name', '')
            if not name:
                continue
            self.graph.query("""
            MERGE (ds:DataSubject {name: $name})
            SET ds.definition = $definition
            """, {"name": name, "definition": row.get('definition', '')})
            count += 1
        logger.info(f"Ingested {count} DataSubject nodes")

    def _ingest_gdc(self):
        """Ingest gdc.csv into GDC nodes with enriched schema."""
        rows = _read_csv("gdc.csv")
        count = 0
        for row in rows:
            name = row.get('name', '')
            if not name:
                continue
            self.graph.query("""
            MERGE (g:GDC {name: $name})
            SET g.definition = $definition,
                g.data_domain = $data_domain,
                g.data_privacy_indicator = $data_privacy_indicator,
                g.gdc_level_2 = $gdc_level_2,
                g.gdc_level_3 = $gdc_level_3,
                g.category = $data_domain
            """, {
                "name": name,
                "definition": row.get('definition', ''),
                "data_domain": row.get('data_domain', ''),
                "data_privacy_indicator": row.get('data_privacy_indicator', ''),
                "gdc_level_2": row.get('gdc_level_2', ''),
                "gdc_level_3": row.get('gdc_level_3', ''),
            })
            count += 1
        logger.info(f"Ingested {count} GDC nodes")

    # -------------------------------------------------------------------------
    # Dynamic rule addition (wizard/sandbox) — unified method
    # -------------------------------------------------------------------------

    def add_rule(self, rule_def: dict) -> bool:
        """Add any rule type to the graph from AI-generated definition."""
        try:
            rule_type = rule_def.get('rule_type') or 'attribute'
            origin_match_type = "group" if rule_def.get('origin_group') else (
                "specific" if rule_def.get('origin_countries') else "any"
            )
            receiving_match_type = "group" if rule_def.get('receiving_group') else (
                "specific" if rule_def.get('receiving_countries') else "any"
            )
            priority = rule_def.get('priority', 'medium')
            outcome = rule_def.get('outcome', 'permission')
            valid_until = rule_def.get('valid_until')

            self.graph.query("""
            MERGE (r:Rule {rule_id: $rule_id})
            SET r.rule_type = $rule_type,
                r.name = $name,
                r.description = $description,
                r.priority = $priority,
                r.priority_order = $priority_order,
                r.origin_match_type = $origin_match_type,
                r.receiving_match_type = $receiving_match_type,
                r.matching_mode = $matching_mode,
                r.outcome = $outcome,
                r.odrl_type = $odrl_type,
                r.odrl_action = $odrl_action,
                r.odrl_target = $odrl_target,
                r.has_pii_required = $has_pii_required,
                r.requires_any_data = $requires_any_data,
                r.requires_personal_data = $requires_personal_data,
                r.required_actions = $required_actions,
                r.valid_until = $valid_until,
                r.case_matching_module = $case_matching_module,
                r.attribute_name = $attribute_name,
                r.attribute_keywords = $attribute_keywords,
                r.attribute_patterns = $attribute_patterns,
                r.logic_tree = $logic_tree,
                r.enabled = true
            """, {
                "rule_id": rule_def.get('rule_id'),
                "rule_type": rule_type,
                "name": rule_def.get('name', ''),
                "description": rule_def.get('description', ''),
                "priority": priority,
                "priority_order": _priority_order(priority),
                "origin_match_type": origin_match_type,
                "receiving_match_type": receiving_match_type,
                "matching_mode": rule_def.get('matching_mode', 'all_dimensions'),
                "outcome": outcome,
                "odrl_type": rule_def.get('odrl_type', 'Prohibition' if outcome == 'prohibition' else 'Permission'),
                "odrl_action": rule_def.get('odrl_action', 'transfer'),
                "odrl_target": rule_def.get('odrl_target', 'Data'),
                "has_pii_required": rule_def.get('requires_pii', False),
                "requires_any_data": rule_def.get('requires_any_data', False),
                "requires_personal_data": rule_def.get('requires_personal_data', False),
                "required_actions": ",".join(rule_def.get('required_actions') or []),
                "valid_until": valid_until,
                "case_matching_module": rule_def.get('case_matching_module') or None,
                "attribute_name": rule_def.get('attribute_name', ''),
                "attribute_keywords": json.dumps(rule_def.get('attribute_keywords') or []),
                "attribute_patterns": json.dumps(rule_def.get('attribute_patterns') or []),
                "logic_tree": json.dumps(rule_def.get('logic_tree')) if rule_def.get('logic_tree') else None,
            })

            # Permission/Prohibition — delete old relationships first to prevent
            # dual Permission+Prohibition when outcome changes on an existing rule
            rule_name = rule_def.get('name', rule_def.get('rule_id'))
            rule_id = rule_def.get('rule_id')
            self.graph.query("""
            MATCH (r:Rule {rule_id: $rule_id})-[rel:HAS_PERMISSION|HAS_PROHIBITION]->()
            DELETE rel
            """, {"rule_id": rule_id})

            if outcome == 'prohibition':
                self.graph.query("""
                MATCH (r:Rule {rule_id: $rule_id})
                MERGE (pb:Prohibition {name: $name})
                MERGE (r)-[:HAS_PROHIBITION]->(pb)
                """, {"rule_id": rule_id, "name": rule_name})
            else:
                perm_name = f"Transfer Permission ({rule_name})"
                self.graph.query("""
                MATCH (r:Rule {rule_id: $rule_id})
                MERGE (p:Permission {name: $name})
                MERGE (r)-[:HAS_PERMISSION]->(p)
                """, {"rule_id": rule_id, "name": perm_name})

                # Create assessment duties (PIA/TIA/HRPR) from required_assessments
                assessment_names = {'pia', 'tia', 'hrpr'}
                created_assessments = set()

                for assessment in (rule_def.get('required_assessments') or []):
                    assessment_upper = str(assessment).strip().upper()
                    assessment_lower = assessment_upper.lower()
                    if assessment_lower in assessment_names and assessment_lower not in created_assessments:
                        duty_name = f"Complete {assessment_upper} Module"
                        self._create_duty(duty_name, assessment_upper, "Completed")
                        self.graph.query("""
                        MATCH (p:Permission {name: $perm_name})
                        MATCH (d:Duty {name: $duty_name, module: $module, value: $value})
                        MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                        """, {"perm_name": perm_name, "duty_name": duty_name,
                              "module": assessment_upper, "value": "Completed"})
                        created_assessments.add(assessment_lower)

                # Also check required_actions for assessment names
                for action in (rule_def.get('required_actions') or []):
                    action_stripped = str(action).strip()
                    action_lower = action_stripped.lower()
                    if action_lower in assessment_names and action_lower not in created_assessments:
                        assessment_upper = action_stripped.upper()
                        duty_name = f"Complete {assessment_upper} Module"
                        self._create_duty(duty_name, assessment_upper, "Completed")
                        self.graph.query("""
                        MATCH (p:Permission {name: $perm_name})
                        MATCH (d:Duty {name: $duty_name, module: $module, value: $value})
                        MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                        """, {"perm_name": perm_name, "duty_name": duty_name,
                              "module": assessment_upper, "value": "Completed"})
                        created_assessments.add(action_lower)
                    elif action_lower not in assessment_names:
                        # Non-assessment action duties
                        self._create_duty(action_stripped, "action", "required")
                        self.graph.query("""
                        MATCH (p:Permission {name: $perm_name})
                        MATCH (d:Duty {name: $duty_name})
                        MERGE (p)-[:CAN_HAVE_DUTY]->(d)
                        """, {"perm_name": perm_name, "duty_name": action_stripped})

            # Helper to link geographic scopes correctly
            def link_scopes(scopes, is_origin=True):
                if not scopes:
                    return "any"
                
                match_type = "specific"
                has_groups = False
                for scope in scopes:
                    scope = scope.strip()
                    if not scope: continue
                    # Check if it's a group
                    res = self.graph.query("MATCH (g:CountryGroup {name: $name}) RETURN g LIMIT 1", {"name": scope})
                    is_group = len(res.result_set) > 0 if hasattr(res, 'result_set') else False
                    
                    if is_group:
                        has_groups = True
                        if is_origin:
                            self.graph.query("""
                            MATCH (r:Rule {rule_id: $rule_id})
                            MATCH (g:CountryGroup {name: $name})
                            MERGE (r)-[:TRIGGERED_BY_ORIGIN]->(g)
                            """, {"rule_id": rule_id, "name": scope})
                        else:
                            self.graph.query("""
                            MATCH (r:Rule {rule_id: $rule_id})
                            MATCH (g:CountryGroup {name: $name})
                            MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(g)
                            """, {"rule_id": rule_id, "name": scope})
                    else:
                        self._ensure_country(scope)
                        if is_origin:
                            self.graph.query("""
                            MATCH (r:Rule {rule_id: $rule_id})
                            MATCH (c:Country {name: $name})
                            MERGE (r)-[:ORIGINATES_FROM]->(c)
                            MERGE (r)-[:TRIGGERED_BY_ORIGIN]->(c)
                            """, {"rule_id": rule_id, "name": scope})
                        else:
                            self.graph.query("""
                            MATCH (r:Rule {rule_id: $rule_id})
                            MATCH (c:Country {name: $name})
                            MERGE (r)-[:RECEIVED_IN]->(c)
                            MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(c)
                            """, {"rule_id": rule_id, "name": scope})
                
                return "group" if has_groups else "specific"

            # Process origins and receivings
            computed_origin_type = link_scopes(
                (rule_def.get('origin_countries') or []) + [rule_def.get('origin_group')] if rule_def.get('origin_group') else rule_def.get('origin_countries'),
                is_origin=True
            )
            computed_receiving_type = link_scopes(
                (rule_def.get('receiving_countries') or []) + [rule_def.get('receiving_group')] if rule_def.get('receiving_group') else rule_def.get('receiving_countries'),
                is_origin=False
            )
            
            # Additional origin/receiving legal entities
            for entity in (rule_def.get('origin_legal_entities') or []):
                self.graph.query("""
                MATCH (r:Rule {rule_id: $rule_id})
                MATCH (le:LegalEntity {name: $entity})
                MERGE (r)-[:TRIGGERED_BY_ORIGIN]->(le)
                """, {"rule_id": rule_id, "entity": entity})

            for entity in (rule_def.get('receiving_legal_entities') or []):
                self.graph.query("""
                MATCH (r:Rule {rule_id: $rule_id})
                MATCH (le:LegalEntity {name: $entity})
                MERGE (r)-[:TRIGGERED_BY_RECEIVING]->(le)
                """, {"rule_id": rule_id, "entity": entity})

            # Action
            action_name = "Transfer PII" if rule_def.get('requires_pii') else "Transfer Data"
            self.graph.query("""
            MATCH (r:Rule {rule_id: $rule_id})
            MATCH (a:Action {name: $action_name})
            MERGE (r)-[:HAS_ACTION]->(a)
            """, {"rule_id": rule_id, "action_name": action_name})

            # Gather entities from both flat lists and the logic_tree
            v_data_categories = set(rule_def.get('data_categories') or [])
            v_purposes = set(rule_def.get('purposes_of_processing') or [])
            v_processes = set(rule_def.get('processes') or [])
            v_gdc = set(rule_def.get('gdc') or [])
            v_regulators = set(rule_def.get('regulators') or [])
            v_authorities = set(rule_def.get('authorities') or [])
            v_sdc = set(rule_def.get('sensitive_data_categories') or [])
            v_data_subjects = set(rule_def.get('data_subjects') or [])

            logic_tree = rule_def.get('logic_tree')
            if logic_tree:
                def walk_tree(node):
                    if not isinstance(node, dict): return
                    if node.get('type') == 'CONDITION':
                        dim = node.get('dimension')
                        val = node.get('value')
                        if not val: return
                        if dim == 'DataCategory': v_data_categories.add(val)
                        elif dim == 'Purpose': v_purposes.add(val)
                        elif dim == 'Process': v_processes.add(val)
                        elif dim == 'GDC': v_gdc.add(val)
                        elif dim == 'Regulator': v_regulators.add(val)
                        elif dim == 'Authority': v_authorities.add(val)
                        elif dim == 'SensitiveDataCategory': v_sdc.add(val)
                        elif dim == 'DataSubject': v_data_subjects.add(val)
                    elif node.get('type') in ['AND', 'OR', 'NOT']:
                        for child in node.get('children', []):
                            walk_tree(child)
                walk_tree(logic_tree)

            # Data Categories — MERGE nodes and link to rule
            for cat in v_data_categories:
                cat_name = str(cat).strip()
                if cat_name:
                    self.graph.query("MERGE (dc:DataCategory {name: $name})", {"name": cat_name})
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (dc:DataCategory {name: $name})
                    MERGE (r)-[:HAS_DATA_CATEGORY]->(dc)
                    """, {"rule_id": rule_id, "name": cat_name})

            # Purposes — MERGE nodes and link to rule (both PurposeOfProcessing and Purpose)
            for purpose in v_purposes:
                purpose_name = str(purpose).strip()
                if purpose_name:
                    self.graph.query("MERGE (p:PurposeOfProcessing {name: $name})", {"name": purpose_name})
                    self.graph.query("MERGE (p:Purpose {name: $name})", {"name": purpose_name})
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (p:PurposeOfProcessing {name: $name})
                    MERGE (r)-[:HAS_PURPOSE]->(p)
                    """, {"rule_id": rule_id, "name": purpose_name})
                    # Also link to Purpose node — ALL_RULES_QUERY matches :Purpose not :PurposeOfProcessing
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (p:Purpose {name: $name})
                    MERGE (r)-[:HAS_PURPOSE]->(p)
                    """, {"rule_id": rule_id, "name": purpose_name})

            # Processes — MERGE nodes and link to rule
            for proc in v_processes:
                proc_name = str(proc).strip()
                if proc_name:
                    self.graph.query("MERGE (p:Process {name: $name})", {"name": proc_name})
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (p:Process {name: $name})
                    MERGE (r)-[:HAS_PROCESS]->(p)
                    """, {"rule_id": rule_id, "name": proc_name})

            # GDC — MERGE nodes and link to rule
            for gdc in v_gdc:
                gdc_name = str(gdc).strip()
                if gdc_name:
                    self.graph.query("MERGE (g:GDC {name: $name})", {"name": gdc_name})
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (g:GDC {name: $name})
                    MERGE (r)-[:HAS_GDC]->(g)
                    """, {"rule_id": rule_id, "name": gdc_name})

            # LINKED_TO relationships for reference entity types.
            for reg in v_regulators:
                reg_name = str(reg).strip()
                if reg_name:
                    self.graph.query(
                        "MERGE (reg:Regulator {name: $name})",
                        {"name": reg_name},
                    )
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (reg:Regulator {name: $name})
                    MERGE (r)-[:LINKED_TO]->(reg)
                    """, {"rule_id": rule_id, "name": reg_name})

            for auth in v_authorities:
                auth_name = str(auth).strip()
                if auth_name:
                    self.graph.query(
                        "MERGE (auth:Authority {name: $name})",
                        {"name": auth_name},
                    )
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (auth:Authority {name: $name})
                    MERGE (r)-[:LINKED_TO]->(auth)
                    """, {"rule_id": rule_id, "name": auth_name})

            for sdc in v_sdc:
                sdc_name = str(sdc).strip()
                if sdc_name:
                    self.graph.query(
                        "MERGE (sdc:SensitiveDataCategory {name: $name})",
                        {"name": sdc_name},
                    )
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (sdc:SensitiveDataCategory {name: $name})
                    MERGE (r)-[:HAS_SENSITIVE_DATA_CATEGORY]->(sdc)
                    """, {"rule_id": rule_id, "name": sdc_name})

            for ds in v_data_subjects:
                ds_name = str(ds).strip()
                if ds_name:
                    self.graph.query(
                        "MERGE (ds:DataSubject {name: $name})",
                        {"name": ds_name},
                    )
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (ds:DataSubject {name: $name})
                    MERGE (r)-[:LINKED_TO]->(ds)
                    """, {"rule_id": rule_id, "name": ds_name})


            for ds in (rule_def.get('data_subjects') or []):
                ds_name = str(ds).strip()
                if ds_name:
                    self.graph.query(
                        "MERGE (ds:DataSubject {name: $name})",
                        {"name": ds_name},
                    )
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (ds:DataSubject {name: $name})
                    MERGE (r)-[:LINKED_TO]->(ds)
                    """, {"rule_id": rule_id, "name": ds_name})

            for gbgf in (rule_def.get('global_business_functions') or []):
                gbgf_name = str(gbgf).strip()
                if gbgf_name:
                    self.graph.query(
                        "MERGE (gbgf:GlobalBusinessFunction {name: $name})",
                        {"name": gbgf_name},
                    )
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (gbgf:GlobalBusinessFunction {name: $name})
                    MERGE (r)-[:LINKED_TO]->(gbgf)
                    """, {"rule_id": rule_id, "name": gbgf_name})

            # Attribute nodes from dictionary keywords — link to rule for graph-based discovery.
            # No cap: all keywords from the data dictionary are ingested.
            for keyword in (rule_def.get('attribute_keywords') or []):
                kw_name = str(keyword).strip().lower()
                if kw_name and len(kw_name) >= 3:
                    self.graph.query("MERGE (a:Attribute {name: $name})", {"name": kw_name})
                    self.graph.query("""
                    MATCH (r:Rule {rule_id: $rule_id})
                    MATCH (a:Attribute {name: $name})
                    MERGE (r)-[:HAS_ATTRIBUTE]->(a)
                    """, {"rule_id": rule_id, "name": kw_name})

            logger.info(f"Added rule: {rule_id} (type={rule_type})")
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to add rule: {e}")
            return False

    def _print_stats(self):
        stats = self.db.get_graph_stats(settings.database.rules_graph_name)
        logger.info(f"RulesGraph stats: {stats['node_count']} nodes, {stats['edge_count']} edges")


def build_rules_graph(clear_existing: bool = True):
    """Build the rules graph (convenience function)"""
    builder = RulesGraphBuilder()
    if clear_existing:
        builder.build(clear_existing=True)
    else:
        builder.build_incremental()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_rules_graph()
