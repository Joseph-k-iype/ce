"""
Rules Evaluation Service
========================
Core engine for evaluating rules via FalkorDB graph queries.
The RulesGraph is the single source of truth.

Evaluates case-matching rules (precedent-based) against the graph.
Supports legal entity matching, case-insensitive country matching,
prohibition logic (any prohibition → overall PROHIBITION), and rule expiration.
"""

import json
import logging
import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import date

from services.database import get_db_service
from services.cache import get_cache_service
from services.attribute_detector import get_attribute_detector
from rules.dictionaries.rules_definitions import (
    get_enabled_attribute_rules,
    RuleOutcome,
)
from models.schemas import (
    TransferStatus,
    RuleOutcomeType,
    TriggeredRule,
    PermissionInfo,
    ProhibitionInfo,
    DutyInfo,
    CaseMatch,
    FieldMatch,
    PrecedentValidation,
    EvidenceSummary,
    AssessmentCompliance,
    DetectedAttribute,
    RulesEvaluationResponse,
    EvaluationNode,
    EvaluationEdge,
    EvaluationGraph,
)
from utils.schema_manager import get_rf_type_for_label, get_lane_for_label
from services.cypher_template_engine import get_cypher_templates

logger = logging.getLogger(__name__)


# ── Country name normalization ──────────────────────────────────────────────
# Maps common abbreviations and variants to canonical names used in the graph.
COUNTRY_ALIASES = {
    "uk": "United Kingdom",
    "gb": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "us": "United States",
    "usa": "United States",
    "united states of america": "United States",
    "uae": "United Arab Emirates",
    "south korea": "Republic of Korea",
    "korea": "Republic of Korea",
    "czech republic": "Czechia",
    "türkiye": "Turkiye",
    "turkey": "Turkiye",
    "hk": "Hong Kong",
    "sg": "Singapore",
    "de": "Germany",
    "fr": "France",
    "jp": "Japan",
    "cn": "China",
    "in": "India",
    "au": "Australia",
    "nz": "New Zealand",
    "ca": "Canada",
    "br": "Brazil",
    "mx": "Mexico",
    "za": "South Africa",
    "ch": "Switzerland",
    "ie": "Ireland",
    "nl": "Netherlands",
    "se": "Sweden",
    "no": "Norway",
    "dk": "Denmark",
    "fi": "Finland",
    "at": "Austria",
    "be": "Belgium",
    "it": "Italy",
    "es": "Spain",
    "pt": "Portugal",
    "pl": "Poland",
    "ro": "Romania",
    "bg": "Bulgaria",
    "hr": "Croatia",
    "cy": "Cyprus",
    "cz": "Czechia",
    "ee": "Estonia",
    "gr": "Greece",
    "hu": "Hungary",
    "lv": "Latvia",
    "lt": "Lithuania",
    "lu": "Luxembourg",
    "mt": "Malta",
    "sk": "Slovakia",
    "si": "Slovenia",
    "is": "Iceland",
    "li": "Liechtenstein",
}


def _normalize_country(name: str) -> str:
    """Normalize country name to match graph data."""
    if not name:
        return name
    stripped = name.strip()
    lower = stripped.lower()
    return COUNTRY_ALIASES.get(lower, stripped)


def _normalize_text(text: str) -> str:
    """Normalize for attribute matching: lowercase, strip all non-alphanumeric.

    Result: "opt-out" → "optout", "opt_out" → "optout", "Opt Out" → "optout"
    """
    if not text:
        return text
    return re.sub(r'[^a-z0-9]', '', text.lower().strip())


# ── Cypher query templates loaded from services/cypher_templates/ ────────────
# ALL_RULES_QUERY is loaded at class init from all_rules.cypher
# See services/cypher_templates/ for the actual query definitions.


@dataclass
class EvaluationContext:
    """Context for rule evaluation"""
    origin_country: str
    receiving_country: str
    pii: bool = False
    purposes: List[str] = field(default_factory=list)
    process_l1: List[str] = field(default_factory=list)
    process_l2: List[str] = field(default_factory=list)
    process_l3: List[str] = field(default_factory=list)
    personal_data_names: List[str] = field(default_factory=list)
    data_categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_attributes: List[DetectedAttribute] = field(default_factory=list)
    origin_legal_entity: Optional[str] = None
    receiving_legal_entity: Optional[str] = None
    data_subjects: List[str] = field(default_factory=list)
    regulators: List[str] = field(default_factory=list)
    authorities: List[str] = field(default_factory=list)
    # rule_id -> {label -> [node_names]}
    triggered_node_mappings: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)


class RulesEvaluator:
    """
    Graph-based rules evaluation engine.
    All rule matching is done via Cypher queries against the RulesGraph.
    Supports multi-graph precedent search across configured graphs.
    """

    def __init__(self, rules_graph=None, additional_precedent_graphs: Optional[List[str]] = None):
        self.db = get_db_service()
        self.cache = get_cache_service()
        self.attribute_detector = get_attribute_detector()
        self._rules_graph = rules_graph or self.db.get_rules_graph()
        self._templates = get_cypher_templates()
        # Additional graphs to query for precedent cases (beyond DataTransferGraph)
        self.additional_precedent_graphs = additional_precedent_graphs or []

    def _graph_query(self, query: str, params: dict = None) -> list:
        """Execute a Cypher query against the rules graph."""
        try:
            result = self._rules_graph.query(query, params)
            if not hasattr(result, 'result_set') or not result.result_set:
                logger.debug(f"Graph query returned empty result set (params: {params})")
                return []
            headers = result.header
            rows = []
            for row in result.result_set:
                row_dict = {}
                for i, header in enumerate(headers):
                    col_name = header[1] if isinstance(header, (list, tuple)) else header
                    row_dict[col_name] = row[i]
                rows.append(row_dict)
            logger.debug(f"Graph query returned {len(rows)} row(s)")
            return rows
        except Exception as e:
            logger.error(f"Graph query failed: {e}", exc_info=True)
            logger.error(f"Query params were: {params}")
            return []

    # ─── Main evaluation entry ──────────────────────────────────────────

    def evaluate(
        self,
        origin_country: str,
        receiving_country: str,
        pii: bool = False,
        purposes: Optional[List[str]] = None,
        process_l1: Optional[List[str]] = None,
        process_l2: Optional[List[str]] = None,
        process_l3: Optional[List[str]] = None,
        personal_data_names: Optional[List[str]] = None,
        data_categories: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        origin_legal_entity: Optional[str] = None,
        receiving_legal_entity: Optional[str] = None,
        data_subjects: Optional[List[str]] = None,
        regulators: Optional[List[str]] = None,
        authorities: Optional[List[str]] = None,
    ) -> RulesEvaluationResponse:
        """Evaluate all applicable rules for a data transfer via graph queries."""
        start_time = time.time()

        # Normalize country names to match graph data
        norm_origin = _normalize_country(origin_country)
        norm_receiving = _normalize_country(receiving_country)
        logger.info(
            f"Evaluating transfer: {origin_country} (normalized: {norm_origin}) "
            f"→ {receiving_country} (normalized: {norm_receiving}), PII={pii}"
        )

        context = EvaluationContext(
            origin_country=norm_origin,
            receiving_country=norm_receiving,
            pii=pii,
            purposes=purposes or [],
            process_l1=process_l1 or [],
            process_l2=process_l2 or [],
            process_l3=process_l3 or [],
            personal_data_names=personal_data_names or [],
            data_categories=data_categories or [],
            metadata=metadata or {},
            origin_legal_entity=origin_legal_entity,
            receiving_legal_entity=receiving_legal_entity,
            data_subjects=data_subjects or [],
            regulators=regulators or [],
            authorities=authorities or [],
        )

        # Detect attributes for informational enrichment
        context.detected_attributes = self._detect_attributes(context)

        # Build scenario summary for response reflection
        scenario_summary = self._build_context_info(context)

        triggered_rules: List[TriggeredRule] = []
        consolidated_duties: List[str] = []
        has_prohibition = False
        prohibition_reasons: List[str] = []
        evaluated_rule_ids: set = set()

        # ── PHASE 0: Hardcoded attribute rules only (from rules_definitions.py) ──
        # These are global rules (no country matching needed).
        # Graph-stored attribute rules are handled in Phase 1 WITH country matching.
        # NOTE: No short-circuit — collect all Phase 0 results and continue to Phase 1.
        hardcoded_triggered = self._evaluate_hardcoded_attribute_rules(context)
        for attr_rule in hardcoded_triggered:
            triggered_rules.append(attr_rule)
            evaluated_rule_ids.add(attr_rule.rule_id)
            if attr_rule.outcome == RuleOutcomeType.PROHIBITION:
                has_prohibition = True
                prohibition_reasons.append(
                    f"Attribute rule '{attr_rule.rule_name}': {attr_rule.description}"
                )
            # Collect duties from Phase 0 permissions
            for perm in (attr_rule.permissions or []):
                for duty in (perm.duties or []):
                    if duty.name:
                        consolidated_duties.append(duty.name)

        # ── PHASE 1: All graph rules (unified country-based matching) ──
        # Queries ALL enabled rules (case_matching, transfer, attribute) with
        # country matching. Attribute rules with keywords get additional
        # keyword post-filtering against personal_data_names and metadata.
        all_graph_rules = self._query_all_applicable_rules(context)
        logger.info(f"Graph query returned {len(all_graph_rules)} applicable rule(s)")

        # ── Metadata entity enrichment ───────────────────────────────────
        # If the user provides metadata JSON with entity-like keys
        # (e.g. {"data_category": "Financial Crime Data", "regulator": "FinCEN"}),
        # extract those values and merge them into context dimensions so they
        # participate in Tier 1 entity matching — not just keyword matching.
        if context.metadata:
            self._enrich_context_from_metadata(context)

        # Contextual intelligence: determine whether the caller provided any entity data.
        # If no entity data is provided (only countries), ONLY case_matching rules
        # (TIA/PIA/HRPR) should fire. Attribute rules require at least one entity
        # dimension so results are specific and meaningful, not just country-based.
        ctx_has_any_content_data = bool(
            context.data_categories
            or context.purposes
            or context.process_l1
            or context.process_l2
            or context.process_l3
            or context.data_subjects
            or context.regulators
            or context.authorities
            or context.personal_data_names
            or context.metadata
        )
        logger.info(
            f"Entity context: data_categories={context.data_categories}, "
            f"purposes={context.purposes}, regulators={context.regulators}, "
            f"data_subjects={context.data_subjects}, authorities={context.authorities}, "
            f"processes_l1={context.process_l1}, ctx_has_any_content_data={ctx_has_any_content_data}"
        )

        # Post-filter and build triggered rules
        country_matched_rules = []
        for rule_row in all_graph_rules:
            rule_id = rule_row.get('rule_id', '')
            rule_type = rule_row.get('rule_type', 'case_matching')

            # Skip rules already evaluated in Phase 0
            if rule_id in evaluated_rule_ids:
                continue

            # Skip expired rules
            valid_until_str = rule_row.get('valid_until')
            if valid_until_str:
                try:
                    # simple string comparison works for ISO dates (YYYY-MM-DD)
                    # Graph returns '2025-12-31'
                    from datetime import datetime
                    if valid_until_str < datetime.now().isoformat()[:10]:
                        logger.info(f"Rule {rule_id} skipped: expired on {valid_until_str}")
                        continue
                except Exception as e:
                    logger.warning(f"Error checking valid_until for {rule_id}: {e}")

            # For rules with attribute_keywords (any type), check keyword matching
            keywords_json = rule_row.get('attribute_keywords') or ''
            patterns_json = rule_row.get('attribute_patterns') or ''
            has_keywords = keywords_json and keywords_json != '[]'
            has_patterns = patterns_json and patterns_json != '[]'

            # Check if rule has graph-linked attributes/categories/purposes/processes/gdcs OR a logic tree
            has_linked = bool(
                rule_row.get('logic_tree')
                or rule_row.get('linked_attributes')
                or rule_row.get('linked_data_categories')
                or rule_row.get('linked_purposes')
                or rule_row.get('linked_processes')
                or rule_row.get('linked_gdcs')
                or rule_row.get('linked_data_subjects')
                or rule_row.get('linked_regulators')
                or rule_row.get('linked_authorities')
            )

            logger.info(
                f"Rule {rule_id} ({rule_type}): has_linked={has_linked}, "
                f"has_keywords={has_keywords}, linked_cats={rule_row.get('linked_data_categories')}, "
                f"linked_regs={rule_row.get('linked_regulators')}, "
                f"linked_purps={rule_row.get('linked_purposes')}"
            )

            # Determine if this rule requires content matching
            needs_content_match = (
                rule_type == 'attribute'
                or has_keywords
                or has_patterns
                or has_linked
            )

            # If this rule needs content/entity matching but the evaluation context
            # has NO entity data at all, skip it. With only origin+receiving country,
            # only case_matching rules (TIA/PIA/HRPR) should apply.
            if needs_content_match and not ctx_has_any_content_data:
                logger.debug(
                    f"Rule {rule_id} ({rule_type}) skipped: "
                    f"needs entity context but none provided — TIA/PIA/HRPR rules only"
                )
                continue

            if needs_content_match:
                matched = False

                # ─── Entity dimension gating (MUST pass if rule has linked entities) ───
                entity_dims_ok = True
                if has_linked:
                    entity_dims_ok = self._match_graph_linked_attributes(context, rule_row)

                # ─── Keyword / pattern matching (free-text) ──────────────────────────
                keyword_matched = False
                if has_keywords or has_patterns:
                    try:
                        keywords = json.loads(keywords_json) if isinstance(keywords_json, str) else (keywords_json or [])
                    except (json.JSONDecodeError, TypeError):
                        keywords = []
                    try:
                        patterns = json.loads(patterns_json) if isinstance(patterns_json, str) else (patterns_json or [])
                    except (json.JSONDecodeError, TypeError):
                        patterns = []

                    if keywords or patterns:
                        keyword_matched = self._match_attribute_keywords(context, keywords, patterns)

                # ─── Final decision ──────────────────────────────────────────────────
                # Based on user request, if ANY condition matched (entities OR keywords),
                # the rule should trigger. This means keyword matches in metadata can 
                # trigger the rule even if the entity selection from dropdowns was wrong.
                if entity_dims_ok and has_linked:
                    matched = True
                    logger.debug(f"Rule {rule_id} ({rule_type}) matched via entity dimensions")
                elif keyword_matched:
                    matched = True
                    logger.debug(f"Rule {rule_id} ({rule_type}) matched via keywords/patterns")
                
                # If neither matched, the rule fails
                if not matched:
                    logger.debug(
                        f"Rule {rule_id} ({rule_type}) skipped: no keyword or graph match"
                    )
                    continue
                else:
                    logger.info(
                        f"Rule {rule_id} ({rule_type}) matched via content/keyword/graph"
                    )

            country_matched_rules.append(rule_row)
            evaluated_rule_ids.add(rule_id)

        if not country_matched_rules and not triggered_rules:
            context_info = self._build_context_info(context)
            return RulesEvaluationResponse(
                transfer_status=TransferStatus.REQUIRES_REVIEW,
                origin_country=norm_origin,
                receiving_country=norm_receiving,
                pii=pii,
                scenario_summary=scenario_summary,
                triggered_rules=triggered_rules,
                evaluation_graph=EvaluationGraph(nodes=[], edges=[]),
                detected_attributes=self._format_detected(context),
                message=f"REQUIRES REVIEW [{context_info}]: No applicable rules found. Please raise a governance ticket.",
                evaluation_time_ms=(time.time() - start_time) * 1000,
            )

        # ── Check for prohibition rules ──────────────────────────────
        for rule_row in country_matched_rules:
            outcome = rule_row.get('outcome', 'permission')
            prohibition_names = rule_row.get('prohibition_names', [])
            if outcome == 'prohibition' or (prohibition_names and any(p for p in prohibition_names)):
                has_prohibition = True
                prohibition_reasons.append(
                    f"Rule '{rule_row.get('name', '')}' is a prohibition: {rule_row.get('description', '')}"
                )

        # ── Collect required assessments from ALL rules ────────────
        required_assessments = self._get_required_assessments_from_graph(country_matched_rules)
        logger.info(f"Required assessments: {required_assessments}")

        # ── Build triggered rules ─────────────────────────────────
        for rule_row in country_matched_rules:
            rule_type = rule_row.get('rule_type', 'case_matching')
            triggered_rules.append(self._build_triggered_rule_from_row(rule_row, rule_type, context))
            for module in (rule_row.get('required_assessments') or []):
                if module:
                    consolidated_duties.append(module)
            # Also collect duty names for display
            for duty_name in (rule_row.get('duty_names') or []):
                if duty_name:
                    consolidated_duties.append(duty_name)

        logger.info(
            f"Triggered {len(triggered_rules)} rule(s), "
            f"prohibition={has_prohibition}, duties={list(set(consolidated_duties))}"
        )

        # ── PHASE 2: Search for precedent cases ───────────────────────
        precedent_result = self._search_precedent_cases(context, required_assessments)

        # ── Build visual evaluation graph ──────────────────────────────
        evaluation_graph = self._build_evaluation_graph(context, triggered_rules, required_assessments, list(set(consolidated_duties)))

        # ── PHASE 3: Determine final status ───────────────────────────
        # If ANY triggered rule is a prohibition → overall PROHIBITION
        if has_prohibition:
            context_info = self._build_context_info(context)
            return RulesEvaluationResponse(
                transfer_status=TransferStatus.PROHIBITED,
                origin_country=norm_origin,
                receiving_country=norm_receiving,
                pii=pii,
                scenario_summary=scenario_summary,
                triggered_rules=triggered_rules,
                evaluation_graph=evaluation_graph,
                precedent_validation=precedent_result,
                detected_attributes=self._format_detected(context),
                consolidated_duties=list(set(consolidated_duties)),
                prohibition_reasons=prohibition_reasons,
                evidence_summary=precedent_result.evidence_summary if precedent_result else None,
                message=f"Transfer PROHIBITED [{context_info}]: One or more rules prohibit this transfer.",
                evaluation_time_ms=(time.time() - start_time) * 1000,
            )

        assessment_compliance = AssessmentCompliance(
            pia_required=required_assessments.get('pia', False),
            tia_required=required_assessments.get('tia', False),
            hrpr_required=required_assessments.get('hrpr', False),
        )

        if precedent_result.has_valid_precedent:
            assessment_compliance.pia_compliant = True
            assessment_compliance.tia_compliant = True
            assessment_compliance.hrpr_compliant = True
            assessment_compliance.all_compliant = True
            context_info = self._build_context_info(context)
            return RulesEvaluationResponse(
                transfer_status=TransferStatus.ALLOWED,
                origin_country=norm_origin,
                receiving_country=norm_receiving,
                pii=pii,
                scenario_summary=scenario_summary,
                triggered_rules=triggered_rules,
                evaluation_graph=evaluation_graph,
                precedent_validation=precedent_result,
                assessment_compliance=assessment_compliance,
                detected_attributes=self._format_detected(context),
                consolidated_duties=list(set(consolidated_duties)),
                evidence_summary=precedent_result.evidence_summary,
                message=f"Transfer ALLOWED [{context_info}]: Precedent found with completed assessments.",
                evaluation_time_ms=(time.time() - start_time) * 1000,
            )

        # No valid precedent
        missing = []
        if required_assessments.get('pia') and not precedent_result.compliant_matches:
            missing.append('PIA'); assessment_compliance.pia_compliant = False
        if required_assessments.get('tia') and not precedent_result.compliant_matches:
            missing.append('TIA'); assessment_compliance.tia_compliant = False
        if required_assessments.get('hrpr') and not precedent_result.compliant_matches:
            missing.append('HRPR'); assessment_compliance.hrpr_compliant = False
        assessment_compliance.missing_assessments = missing

        context_info = self._build_context_info(context)
        status_msg = (
            f"Transfer PROHIBITED [{context_info}]: No precedent cases found. Please raise a governance ticket."
            if precedent_result.total_matches == 0
            else f"Transfer PROHIBITED [{context_info}]: Precedent cases found but missing required assessments: {', '.join(missing)}"
        )
        return RulesEvaluationResponse(
            transfer_status=TransferStatus.PROHIBITED,
            origin_country=norm_origin,
            receiving_country=norm_receiving,
            pii=pii,
            scenario_summary=scenario_summary,
            triggered_rules=triggered_rules,
            evaluation_graph=evaluation_graph,
            precedent_validation=precedent_result,
            assessment_compliance=assessment_compliance,
            detected_attributes=self._format_detected(context),
            consolidated_duties=list(set(consolidated_duties)),
            prohibition_reasons=(
                ["No precedent cases found matching criteria"]
                if precedent_result.total_matches == 0
                else [f"No precedent cases with completed {', '.join(missing)} assessments"]
            ),
            evidence_summary=precedent_result.evidence_summary,
            message=status_msg,
            evaluation_time_ms=(time.time() - start_time) * 1000,
        )

    # ─── Graph-based rule evaluation ────────────────────────────────────

    def _query_all_applicable_rules(self, context: EvaluationContext) -> list:
        """Query the RulesGraph for ALL applicable rules (case_matching, transfer, attribute).

        Uses the unified ALL_RULES_QUERY which:
        - Matches all enabled rule types via graph-driven country matching
        - Handles 'not_in' receiving rules correctly
        - Uses exact case-insensitive matching for country names
        - Returns rule metadata including attribute keywords for post-filtering
        """
        today_str = date.today().isoformat()
        params = {
            "origin": context.origin_country,
            "receiving": context.receiving_country,
            "pii": context.pii,
            "has_personal_data": bool(context.personal_data_names),
            "today": today_str,
        }
        logger.debug(f"Querying rules with params: {params}")
        results = self._graph_query(self._templates.get('all_rules'), params)
        if results:
            rule_ids = [r.get('rule_id', '?') for r in results]
            logger.info(f"Rules matched by graph query: {rule_ids}")
        else:
            logger.warning(
                f"No rules matched for {context.origin_country} → {context.receiving_country}. "
                f"Check that country names exist in the graph."
            )
        return results

    # ─── Attribute rule evaluation ─────────────────────────────────────

    def _evaluate_hardcoded_attribute_rules(self, context: EvaluationContext) -> List[TriggeredRule]:
        """Evaluate hardcoded attribute rules from rules_definitions.py only.

        Graph-stored attribute rules are evaluated in Phase 1 via ALL_RULES_QUERY
        which includes proper country matching. This method only handles the
        backward-compatible hardcoded rules that apply globally.
        """
        triggered = []

        attribute_rules = get_enabled_attribute_rules()
        for rule_key, rule in attribute_rules.items():
            matched = self._match_attribute_keywords(
                context, rule.attribute_keywords, rule.attribute_patterns
            )
            # Also check detected attributes from AttributeDetector
            if not matched:
                for detected in context.detected_attributes:
                    if detected.attribute_name == rule.attribute_name:
                        matched = True
                        break
            if not matched:
                continue
            if rule.requires_pii and not context.pii:
                continue

            outcome = RuleOutcomeType.PROHIBITION if rule.outcome == RuleOutcome.PROHIBITION else RuleOutcomeType.PERMISSION
            permissions = []
            prohibitions = []

            if rule.outcome == RuleOutcome.PROHIBITION:
                prohibitions.append(ProhibitionInfo(
                    prohibition_id=f"PROHIB_{rule.rule_id}",
                    name=rule.name,
                    description=rule.description,
                ))
            else:
                permissions.append(PermissionInfo(
                    permission_id=f"PERM_{rule.rule_id}",
                    name=rule.name,
                    description=rule.description,
                    duties=[],
                ))

            triggered.append(TriggeredRule(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                rule_type="attribute",
                priority=rule.priority,
                origin_match_type="any",
                receiving_match_type="any",
                odrl_type=rule.odrl_type,
                has_pii_required=rule.requires_pii,
                description=rule.description,
                outcome=outcome,
                permissions=permissions,
                prohibitions=prohibitions,
                required_actions=[],
                required_assessments=[],
            ))

        return triggered

    # Minimum characters for a keyword to participate in substring matching.
    # Shorter keywords only match via exact (whole-word) comparison.
    MIN_KEYWORD_SUBSTRING_LEN = 4

    def _match_attribute_keywords(self, context: EvaluationContext, keywords: list, patterns: list) -> bool:
        """Check FREE-TEXT input fields only against keywords/patterns.

        Structured fields (purposes, data_categories, process_l1/l2/l3) are
        handled by Tier 1 exact matching in _match_graph_linked_attributes().
        Keywords only match against: personal_data_names + metadata values.

        Matching logic:
        - Keywords >= 4 chars: substring match (keyword found inside input value)
        - Keywords < 4 chars: exact whole-word match only
        - Metadata: only VALUES are checked, not dict keys
        - Each value is checked individually (no cross-contamination)
        """
        # Filter to meaningful keywords
        valid_keywords = [str(k).lower().strip() for k in keywords if str(k).strip()]
        if not valid_keywords and not patterns:
            return False

        # Collect only free-text input fields (NOT structured dropdown fields)
        input_texts = list(context.personal_data_names)

        # Add metadata VALUES only (not keys)
        if context.metadata:
            input_texts.extend(self._extract_metadata_values(context.metadata))

        # Check each input value against keywords individually
        for text in input_texts:
            text_lower = str(text).lower().strip()
            if not text_lower:
                continue
            for kw in valid_keywords:
                if self._keyword_matches(kw, text_lower):
                    logger.debug(f"Keyword match: '{kw}' in input '{text}'")
                    return True

        # Check regex patterns against free-text inputs
        for text in input_texts:
            text_str = str(text)
            for pattern in patterns:
                try:
                    if re.search(pattern, text_str, re.IGNORECASE):
                        logger.debug(f"Pattern match: '{pattern}' in input '{text}'")
                        return True
                except re.error:
                    pass

        return False

    def _keyword_matches(self, keyword: str, text: str) -> bool:
        """Check if a keyword matches a text value using word-boundary matching.

        Uses regex word boundaries so "bank" matches "bank", "banking",
        "bank account" but NOT "embankment".

        Multi-word keywords require ALL words present at word boundaries.
        """
        kw = keyword.strip().lower()
        txt = text.strip().lower()
        if not kw or not txt:
            return False
        words = kw.split()
        if len(words) > 1:
            # Multi-word: require ALL words present at word boundaries
            return all(
                re.search(r'\b' + re.escape(w) + r'\b', txt)
                for w in words if w
            )
        # Single word: word-boundary match
        return bool(re.search(r'\b' + re.escape(kw) + r'\b', txt))

    # Values that are not semantically meaningful for keyword matching
    _SKIP_VALUES = frozenset({
        'true', 'false', 'yes', 'no', 'none', 'null', 'n/a', 'na', 'undefined',
    })
    _UUID_RE = re.compile(r'^[0-9a-f\-]{32,}$', re.IGNORECASE)
    _ISO_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')

    def _extract_metadata_values(self, obj) -> list:
        """Extract only semantically meaningful text (keys AND values) from metadata.
        Skips non-string primitives, short strings, booleans, numbers,
        UUIDs, and ISO dates to prevent false-positive keyword matches.
        """
        values = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                values.extend(self._extract_metadata_values(k))
                values.extend(self._extract_metadata_values(v))
        elif isinstance(obj, list):
            for item in obj:
                values.extend(self._extract_metadata_values(item))
        elif isinstance(obj, str):
            s = obj.strip()
            # Skip short strings (< 3 chars)
            if len(s) < 3:
                return values
            # Skip boolean-like / null-like values
            if s.lower() in self._SKIP_VALUES:
                return values
            # Skip pure numeric strings
            if s.replace('.', '', 1).replace('-', '', 1).isdigit():
                return values
            # Skip UUID-like strings
            if self._UUID_RE.match(s):
                return values
            # Skip ISO date strings
            if self._ISO_DATE_RE.match(s):
                return values
            values.append(s)
        # Skip non-string primitives (int, float, bool) entirely
        return values

    # Minimum keyword hits for fuzzy matching in Tier 2 (or 1 keyword >= this length)
    MIN_FUZZY_KEYWORD_LEN = 6
    MIN_FUZZY_HIT_COUNT = 3

    def _evaluate_logic_node(self, node: dict, context: EvaluationContext, current_matches: Dict[str, List[str]]) -> bool:
        """Recursively evaluate a logic tree node against the evaluation context."""
        node_type = node.get('type')
        if node_type == 'AND':
            children = node.get('children', [])
            if not children:
                return True
            return all(self._evaluate_logic_node(child, context, current_matches) for child in children)
        elif node_type == 'OR':
            children = node.get('children', [])
            if not children:
                return False
            return any(self._evaluate_logic_node(child, context, current_matches) for child in children)
        elif node_type == 'CONDITION':
            dim = node.get('dimension')
            val = node.get('value')
            if not dim or not val:
                return False
            
            # Support comma-separated multi-select values
            val_items = [v.strip() for v in str(val).split(',') if v.strip()]
            val_norms = {_normalize_text(v) for v in val_items}
            if not val_norms:
                return False
            
            # Map dimension to context fields
            ctx_vals = set()
            if dim == 'DataCategory':
                ctx_vals = {_normalize_text(str(c)) for c in context.data_categories if c}
            elif dim == 'Purpose':
                ctx_vals = {_normalize_text(str(p)) for p in context.purposes if p}
            elif dim == 'Process':
                ctx_vals = {_normalize_text(str(p)) for p in (context.process_l1 + context.process_l2 + context.process_l3) if p}
            elif dim == 'GDC':
                ctx_vals = {_normalize_text(str(c)) for c in context.data_categories if c}
            elif dim == 'DataSubject':
                ctx_vals = {_normalize_text(str(d)) for d in context.data_subjects if d}
            elif dim == 'Regulator':
                ctx_vals = {_normalize_text(str(r)) for r in context.regulators if r}
            elif dim == 'Authority':
                ctx_vals = {_normalize_text(str(a)) for a in context.authorities if a}
            elif dim == 'OriginCountry':
                ctx_vals = {_normalize_text(str(context.origin_country))} if context.origin_country else set()
            elif dim == 'ReceivingCountry':
                ctx_vals = {_normalize_text(str(context.receiving_country))} if context.receiving_country else set()
            elif dim == 'LegalEntity':
                ctx_vals = {_normalize_text(str(le)) for le in context.legal_entities if le}
                
                
            intersection = val_norms.intersection(ctx_vals)
            if intersection:
                if dim not in current_matches:
                    current_matches[dim] = []
                for original_v in val_items:
                    if _normalize_text(original_v) in intersection:
                        current_matches[dim].append(original_v)
                return True
            return False
            
        return False

    def _match_graph_linked_attributes(
        self, context: EvaluationContext, rule_row: dict
    ) -> bool:
        """Two-tiered matching of input data against rule's graph-linked nodes.

        Tier 1 — Exact match for structured/dropdown fields:
          - linked_data_categories vs context.data_categories
          - linked_purposes vs context.purposes
          - linked_processes vs context.process_l1/l2/l3
          - linked_gdcs vs context.data_categories (GDC = Group Data Category)
          Case-insensitive set intersection. Any overlap → match.
          - OR, if logic_tree exists, evaluates the tree recursively to determine match.

        Tier 2 — Fuzzy/keyword match for free-text fields only:
          - linked_attributes vs personal_data_names + metadata values
          - Requires threshold: 2+ keyword hits OR 1 keyword >= 6 chars
          - Does NOT match linked_attributes against structured fields.
        """
        rule_id = rule_row.get('rule_id', 'unknown')
        current_matches: Dict[str, List[str]] = {}

        # ── Optional: Complex Logic Tree evaluation ─────────────────────
        logic_tree_json = rule_row.get('logic_tree')
        if logic_tree_json:
            try:
                tree_data = json.loads(logic_tree_json) if isinstance(logic_tree_json, str) else logic_tree_json
                if tree_data:
                    matched = self._evaluate_logic_node(tree_data, context, current_matches)
                    if matched:
                        logger.debug(f"Rule {rule_id} matched via logic_tree")
                        rule_row['matched_entities'] = current_matches
                        return True
                    else:
                        logger.debug(f"Rule {rule_id} logic_tree evaluated to False")
                        return False
            except Exception as e:
                logger.error(f"Failed to parse logic_tree for rule {rule_id}: {e}")
                return False

        linked_attrs = rule_row.get('linked_attributes') or []
        linked_cats = rule_row.get('linked_data_categories') or []
        linked_purposes = rule_row.get('linked_purposes') or []
        linked_processes = rule_row.get('linked_processes') or []
        linked_gdcs = rule_row.get('linked_gdcs') or []
        linked_data_subjects = rule_row.get('linked_data_subjects') or []
        linked_regulators = rule_row.get('linked_regulators') or []
        linked_authorities = rule_row.get('linked_authorities') or []

        if (not linked_attrs and not linked_cats and not linked_purposes
                and not linked_processes and not linked_gdcs
                and not linked_data_subjects and not linked_regulators
                and not linked_authorities):
            return False

        rule_id = rule_row.get('rule_id', 'unknown')
        current_matches: Dict[str, List[str]] = {}

        # ── Tier 1: Check dimensions the USER actually provided values for ──
        # For each dimension the rule specifies AND the user provided values:
        #   - If the values match → dimension passes (True)
        #   - If the values DON'T match → dimension fails (False, wrong entity)
        # If the user provided NO values for a dimension → SKIP it entirely.
        # This way: selecting just one correct entity type fires the rule,
        # but selecting a WRONG entity fails it.
        dimension_results = []

        # Data categories (normalized) — also check GDCs
        if linked_cats or linked_gdcs:
            ctx_cats_norm = {_normalize_text(str(c)) for c in context.data_categories if c} - {''}
            if ctx_cats_norm:
                # User provided data categories → check for overlap
                rule_cats_norm = {_normalize_text(str(c)) for c in linked_cats if c}
                rule_gdcs_norm = {_normalize_text(str(g)) for g in linked_gdcs if g}
                
                # Expand GDCs into their constituent DataCategories using graph queries
                if rule_gdcs_norm:
                    try:
                        query = """
                        MATCH (gdc:GDC)-[:HAS_DATA_CATEGORY]->(cat:DataCategory)
                        WHERE toLower(gdc.name) IN $gdc_names
                        RETURN DISTINCT cat.name AS cat_name
                        """
                        params = {"gdc_names": [g.lower() for g in rule_gdcs_norm]}
                        
                        # Check RulesGraph first
                        gdc_result = self._graph_query(query, params)
                        for row in gdc_result:
                            c = row.get('cat_name')
                            if c:
                                rule_gdcs_norm.add(_normalize_text(str(c)))
                                
                        # Check additional selected graphs for GDC definitions
                        if self.additional_precedent_graphs:
                            from services.multi_graph_query import MultiGraphQuery
                            from services.graph_registry import get_graph_registry
                            multi_query = MultiGraphQuery()
                            registry = get_graph_registry()
                            
                            additional_queries = {}
                            for g_name in self.additional_precedent_graphs:
                                g_meta = registry.get_graph(g_name)
                                if g_meta and g_meta.enabled:
                                    additional_queries[g_name] = (query, params)
                            
                            if additional_queries:
                                additional_results = multi_query.multi_query(additional_queries)
                                for g_name, rows in additional_results.items():
                                    for row in rows:
                                        c = row.get('cat_name')
                                        if c:
                                            rule_gdcs_norm.add(_normalize_text(str(c)))
                    except Exception as e:
                        logger.warning(f"Error expanding GDCs: {e}")
                        pass

                combined_rule_cats = (rule_cats_norm | rule_gdcs_norm) - {''}

                matched_norm = combined_rule_cats & ctx_cats_norm
                if matched_norm:
                    dimension_results.append(True)
                    matched_originals = []
                    for c in linked_cats:
                        if c and _normalize_text(str(c)) in matched_norm:
                            matched_originals.append(str(c))
                    # For GDCs, if the user's data category matched a GDC's child,
                    # we should include the GDC name or the child name as the match
                    for g in linked_gdcs:
                        g_norm = _normalize_text(str(g))
                        if g and g_norm in matched_norm:
                            matched_originals.append(str(g))
                        # Note: we don't easily have the parent->child association here
                        # without slowing down to map them. It's enough to trigger the match
                        # and let the UI know DataCategory dimension matched.
                    current_matches["DataCategory"] = list(set(matched_originals))
                    logger.debug(f"Tier 1: data_categories/GDC matched: {matched_originals}")
                else:
                    dimension_results.append(False)
                    logger.debug(f"Tier 1: data_categories/GDC NOT matched (user values don't overlap)")
            else:
                logger.debug(f"Tier 1: data_categories/GDC — user provided none, skipping")

        # Purposes (normalized)
        if linked_purposes:
            ctx_purp_norm = {_normalize_text(str(p)) for p in context.purposes if p} - {''}
            if ctx_purp_norm:
                rule_purp_norm = {_normalize_text(str(p)) for p in linked_purposes if p} - {''}
                matched_norm = rule_purp_norm & ctx_purp_norm
                if matched_norm:
                    dimension_results.append(True)
                    matched_originals = [p for p in linked_purposes if p and _normalize_text(str(p)) in matched_norm]
                    current_matches["Purpose"] = matched_originals
                    logger.debug(f"Tier 1: purposes matched: {matched_originals}")
                else:
                    dimension_results.append(False)
                    logger.debug(f"Tier 1: purposes NOT matched (user values don't overlap)")
            else:
                logger.debug(f"Tier 1: purposes — user provided none, skipping")

        # Processes (hierarchical, normalized)
        if linked_processes:
            ctx_processes = set()
            ctx_processes_raw = set()
            for p in context.process_l1:
                if p:
                    ctx_processes.add(_normalize_text(str(p)))
                    ctx_processes_raw.add(str(p).lower().strip())
            for p in context.process_l2:
                if p:
                    ctx_processes.add(_normalize_text(str(p)))
                    ctx_processes_raw.add(str(p).lower().strip())
            for p in context.process_l3:
                if p:
                    ctx_processes.add(_normalize_text(str(p)))
                    ctx_processes_raw.add(str(p).lower().strip())
            ctx_processes -= {''}

            if ctx_processes:
                rule_proc_norm = {_normalize_text(str(p)) for p in linked_processes if p} - {''}

                # Build ancestor set for hierarchical matching
                ancestor_set = set(ctx_processes)
                for proc_name in list(ctx_processes_raw):
                    try:
                        query = """
                        MATCH (ancestor:Process)-[:HAS_SUBPROCESS*1..3]->(child:Process)
                        WHERE toLower(child.name) = toLower($name)
                        RETURN DISTINCT ancestor.name AS ancestor_name
                        """
                        params = {"name": proc_name}

                        # Check RulesGraph first
                        ancestor_result = self._graph_query(query, params)
                        for row in ancestor_result:
                            a = row.get('ancestor_name')
                            if a:
                                ancestor_set.add(_normalize_text(str(a)))

                        # Check additional selected graphs for hierarchy definitions
                        if self.additional_precedent_graphs:
                            from services.multi_graph_query import MultiGraphQuery
                            from services.graph_registry import get_graph_registry
                            multi_query = MultiGraphQuery()
                            registry = get_graph_registry()
                            
                            additional_queries = {}
                            for g_name in self.additional_precedent_graphs:
                                g_meta = registry.get_graph(g_name)
                                if g_meta and g_meta.enabled:
                                    additional_queries[g_name] = (query, params)
                            
                            if additional_queries:
                                additional_results = multi_query.multi_query(additional_queries)
                                for g_name, rows in additional_results.items():
                                    for row in rows:
                                        a = row.get('ancestor_name')
                                        if a:
                                            ancestor_set.add(_normalize_text(str(a)))
                    except Exception as e:
                        logger.warning(f"Error checking Process hierarchy for {proc_name}: {e}")
                        pass
                ancestor_set -= {''}

                matched_norm = rule_proc_norm & ancestor_set
                if matched_norm:
                    dimension_results.append(True)
                    matched_originals = [p for p in linked_processes if p and _normalize_text(str(p)) in matched_norm]
                    current_matches["Process"] = matched_originals
                    logger.debug(f"Tier 1: processes matched: {matched_originals}")
                else:
                    dimension_results.append(False)
                    logger.debug(f"Tier 1: processes NOT matched")
            else:
                logger.debug(f"Tier 1: processes — user provided none, skipping")

        # Data subjects (normalized)
        if linked_data_subjects:
            ctx_ds_norm = {_normalize_text(str(d)) for d in context.data_subjects if d} - {''}
            if ctx_ds_norm:
                rule_ds_norm = {_normalize_text(str(d)) for d in linked_data_subjects if d} - {''}
                matched_norm = rule_ds_norm & ctx_ds_norm
                if matched_norm:
                    dimension_results.append(True)
                    matched_originals = [d for d in linked_data_subjects if d and _normalize_text(str(d)) in matched_norm]
                    current_matches["DataSubject"] = matched_originals
                    logger.debug(f"Tier 1: data_subjects matched: {matched_originals}")
                else:
                    dimension_results.append(False)
                    logger.debug(f"Tier 1: data_subjects NOT matched")
            else:
                logger.debug(f"Tier 1: data_subjects — user provided none, skipping")

        # Regulators (normalized)
        if linked_regulators:
            ctx_reg_norm = {_normalize_text(str(r)) for r in context.regulators if r} - {''}
            if ctx_reg_norm:
                rule_reg_norm = {_normalize_text(str(r)) for r in linked_regulators if r} - {''}
                matched_norm = rule_reg_norm & ctx_reg_norm
                if matched_norm:
                    dimension_results.append(True)
                    matched_originals = [r for r in linked_regulators if r and _normalize_text(str(r)) in matched_norm]
                    current_matches["Regulator"] = matched_originals
                    logger.debug(f"Tier 1: regulators matched: {matched_originals}")
                else:
                    dimension_results.append(False)
                    logger.debug(f"Tier 1: regulators NOT matched")
            else:
                logger.debug(f"Tier 1: regulators — user provided none, skipping")

        # Authorities (normalized)
        if linked_authorities:
            ctx_auth_norm = {_normalize_text(str(a)) for a in context.authorities if a} - {''}
            if ctx_auth_norm:
                rule_auth_norm = {_normalize_text(str(a)) for a in linked_authorities if a} - {''}
                matched_norm = rule_auth_norm & ctx_auth_norm
                if matched_norm:
                    dimension_results.append(True)
                    matched_originals = [a for a in linked_authorities if a and _normalize_text(str(a)) in matched_norm]
                    current_matches["Authority"] = matched_originals
                    logger.debug(f"Tier 1: authorities matched: {matched_originals}")
                else:
                    dimension_results.append(False)
                    logger.debug(f"Tier 1: authorities NOT matched")
            else:
                logger.debug(f"Tier 1: authorities — user provided none, skipping")

        # ── Tier 1 decision ──
        # dimension_results only contains entries for dimensions the user
        # actually provided values for. If empty → user provided no matching
        # dimension data, fall through to Tier 2 fuzzy matching.
        if dimension_results:
            matching_mode = rule_row.get('matching_mode', 'all_dimensions')
            
            # OR-logic: trigger if ANY dimension matched
            if matching_mode == 'any_dimension':
                if any(dimension_results):
                    logger.debug(f"Tier 1: ANY_DIMENSION mode — at least one matched — rule triggers")
                    context.triggered_node_mappings[rule_id] = current_matches
                    return True
                else:
                    logger.debug(f"Tier 1: ANY_DIMENSION mode — NO dimensions matched — rule SKIPPED")
                    return False
            
            # AND-logic: trigger only if ALL checked dimensions matched
            else:
                if all(dimension_results):
                    logger.debug(f"Tier 1: ALL_DIMENSIONS mode — all {len(dimension_results)} checked matched — rule triggers")
                    context.triggered_node_mappings[rule_id] = current_matches
                    return True
                else:
                    # User provided values for some dimensions but they didn't match.
                    # This is an actual mismatch (wrong entities) — rule does NOT fire.
                    logger.debug(f"Tier 1: dimension mismatch ({dimension_results}) — rule SKIPPED")
                    return False

        # ── Tier 2: Fuzzy match on free-text fields only ──
        if not linked_attrs:
            return False

        # Only match against free-text inputs: personal_data_names + metadata values
        free_text_inputs = list(context.personal_data_names)
        if context.metadata:
            free_text_inputs.extend(self._extract_metadata_values(context.metadata))

        free_text_lower = [str(t).lower().strip() for t in free_text_inputs if str(t).strip()]
        if not free_text_lower:
            return False

        # Count keyword hits with threshold enforcement
        hit_count = 0
        has_long_hit = False
        matched_attrs = []
        for attr in linked_attrs:
            attr_lower = str(attr).lower().strip()
            if not attr_lower:
                continue
            for text in free_text_lower:
                if self._keyword_matches(attr_lower, text):
                    hit_count += 1
                    matched_attrs.append(str(attr))
                    if len(attr_lower) >= self.MIN_FUZZY_KEYWORD_LEN:
                        has_long_hit = True
                    logger.debug(f"Tier 2 fuzzy hit: '{attr}' in free-text '{text}'")
                    break  # Count each attribute only once

        if has_long_hit or hit_count >= self.MIN_FUZZY_HIT_COUNT:
            logger.debug(f"Tier 2 matched: {hit_count} hit(s), has_long_hit={has_long_hit}")
            if rule_id not in context.triggered_node_mappings:
                context.triggered_node_mappings[rule_id] = {}
            context.triggered_node_mappings[rule_id]["Attribute"] = matched_attrs
            return True

        return False

    # ─── Helpers ────────────────────────────────────────────────────────

    # Mapping of common metadata key patterns to context dimension fields
    _METADATA_ENTITY_KEYS = {
        # data_categories
        'data_category': 'data_categories',
        'data_categories': 'data_categories',
        'category': 'data_categories',
        'categories': 'data_categories',
        # purposes
        'purpose': 'purposes',
        'purposes': 'purposes',
        'purpose_of_processing': 'purposes',
        'purposes_of_processing': 'purposes',
        'processing_purpose': 'purposes',
        # regulators
        'regulator': 'regulators',
        'regulators': 'regulators',
        'regulatory_body': 'regulators',
        # authorities
        'authority': 'authorities',
        'authorities': 'authorities',
        'supervisory_authority': 'authorities',
        # data subjects
        'data_subject': 'data_subjects',
        'data_subjects': 'data_subjects',
        'subject': 'data_subjects',
        # processes
        'process': 'process_l1',
        'process_l1': 'process_l1',
        'process_l2': 'process_l2',
        'process_l3': 'process_l3',
    }

    def _enrich_context_from_metadata(self, context: EvaluationContext) -> None:
        """Extract entity-like values from metadata JSON and merge into context.

        When the user provides metadata like:
            {"data_category": "Financial Crime Data", "regulator": "FinCEN"}
        these values are added to context.data_categories and context.regulators
        so that Tier 1 entity dimension matching can use them.
        """
        if not context.metadata or not isinstance(context.metadata, dict):
            return

        enriched: Dict[str, List[str]] = {}

        for key, value in context.metadata.items():
            key_lower = key.lower().strip().replace(' ', '_')
            target_field = self._METADATA_ENTITY_KEYS.get(key_lower)
            if not target_field:
                continue

            # Handle both single string and list values
            if isinstance(value, str):
                values = [value.strip()] if value.strip() else []
            elif isinstance(value, list):
                values = [str(v).strip() for v in value if v and str(v).strip()]
            else:
                continue

            if not values:
                continue

            if target_field not in enriched:
                enriched[target_field] = []
            enriched[target_field].extend(values)

        if not enriched:
            return

        # Merge into context dimensions (dedup case-insensitive)
        for field_name, new_values in enriched.items():
            existing = getattr(context, field_name, []) or []
            existing_lower = {str(v).lower().strip() for v in existing}
            for val in new_values:
                if val.lower().strip() not in existing_lower:
                    existing.append(val)
                    existing_lower.add(val.lower().strip())
            setattr(context, field_name, existing)

        logger.info(f"Metadata enrichment: merged {enriched} into context dimensions")


    def _detect_attributes(self, context: EvaluationContext) -> list:
        combined_metadata = {
            **context.metadata,
            'personal_data_names': context.personal_data_names,
            'purposes': context.purposes,
            'data_categories': context.data_categories,
            'process_l1': context.process_l1,
            'process_l2': context.process_l2,
            'process_l3': context.process_l3,
        }
        if not combined_metadata:
            return []
        results = self.attribute_detector.detect(combined_metadata)
        return [r for r in results if r.detected]

    def _format_detected(self, context: EvaluationContext) -> List[DetectedAttribute]:
        return [
            DetectedAttribute(
                attribute_name=d.attribute_name,
                detection_method=d.detection_method,
                matched_terms=d.matched_terms,
                confidence=d.confidence,
            )
            for d in context.detected_attributes
        ]

    def _build_context_info(self, context: EvaluationContext) -> str:
        parts = [f"{context.origin_country} → {context.receiving_country}"]
        if context.pii:
            parts.append("PII=Yes")
        if context.origin_legal_entity:
            parts.append(f"Origin LE: {context.origin_legal_entity}")
        if context.receiving_legal_entity:
            parts.append(f"Receiving LE: {context.receiving_legal_entity}")
        if context.purposes:
            parts.append(f"Purposes: {', '.join(context.purposes)}")
        if context.data_categories:
            parts.append(f"Categories: {', '.join(context.data_categories)}")
        if context.process_l1:
            parts.append(f"L1: {', '.join(context.process_l1)}")
        if context.process_l2:
            parts.append(f"L2: {', '.join(context.process_l2)}")
        if context.process_l3:
            parts.append(f"L3: {', '.join(context.process_l3)}")
        if context.detected_attributes:
            attrs = [d.attribute_name for d in context.detected_attributes]
            parts.append(f"Detected: {', '.join(attrs)}")
        return " | ".join(parts)

    def _get_required_assessments_from_graph(self, rules: list) -> Dict[str, bool]:
        """Extract required assessments from graph query results.

        Checks both d.module (predefined rules) and d.name/required_actions
        (AI-generated rules) for PIA/TIA/HRPR requirements.
        """
        required = {'pia': False, 'tia': False, 'hrpr': False}
        assessment_aliases = {
            'pia': 'pia', 'tia': 'tia', 'hrpr': 'hrpr',
            'complete pia module': 'pia', 'complete tia module': 'tia',
            'complete hrpr module': 'hrpr',
            'privacy impact assessment': 'pia',
            'transfer impact assessment': 'tia',
            'high risk processing review': 'hrpr',
        }
        for row in rules:
            # Check d.module values (predefined rules)
            for module in (row.get('required_assessments') or []):
                if module:
                    key = str(module).lower().strip()
                    mapped = assessment_aliases.get(key, key)
                    if mapped in required:
                        required[mapped] = True
            # Check d.name values (AI-generated rules via add_rule)
            for duty_name in (row.get('duty_names') or []):
                if duty_name:
                    key = str(duty_name).lower().strip()
                    mapped = assessment_aliases.get(key, key)
                    if mapped in required:
                        required[mapped] = True
            # Check required_actions stored on rule node (comma-separated string)
            req_actions = row.get('required_actions') or ''
            if isinstance(req_actions, str) and req_actions:
                for action in req_actions.split(','):
                    action_lower = action.strip().lower()
                    mapped = assessment_aliases.get(action_lower, action_lower)
                    if mapped in required:
                        required[mapped] = True
        return required

    def _build_triggered_rule_from_row(self, row: dict, rule_type: str, context: 'EvaluationContext' = None) -> TriggeredRule:
        """Build a TriggeredRule from a graph query result row."""
        outcome_str = row.get('outcome', 'permission')
        outcome = RuleOutcomeType.PROHIBITION if outcome_str == 'prohibition' else RuleOutcomeType.PERMISSION

        prohibitions = []
        permissions = []
        duties = []

        # Parse required_actions (comma-separated string from rule node)
        req_actions_raw = row.get('required_actions') or ''
        if isinstance(req_actions_raw, str):
            req_actions = [a.strip() for a in req_actions_raw.split(',') if a.strip()] if req_actions_raw else []
        elif isinstance(req_actions_raw, list):
            req_actions = req_actions_raw
        else:
            req_actions = []

        # Collect assessment modules from graph duties
        assessment_modules = set()
        assessment_aliases = {
            'pia', 'tia', 'hrpr',
        }
        duty_name_to_module = {
            'complete pia module': 'PIA',
            'complete tia module': 'TIA',
            'complete hrpr module': 'HRPR',
        }

        for module in (row.get('required_assessments') or []):
            if module:
                module_str = str(module).strip()
                if module_str.lower() in assessment_aliases:
                    assessment_modules.add(module_str.upper())

        for duty_name in (row.get('duty_names') or []):
            if duty_name:
                mapped = duty_name_to_module.get(str(duty_name).lower().strip())
                if mapped:
                    assessment_modules.add(mapped)

        # Also check required_actions for assessment names
        for action in req_actions:
            action_lower = action.lower().strip()
            if action_lower in assessment_aliases:
                assessment_modules.add(action.upper())
            mapped = duty_name_to_module.get(action_lower)
            if mapped:
                assessment_modules.add(mapped)

        # Build duty info for assessments
        for module in sorted(assessment_modules):
            duties.append(DutyInfo(
                duty_id=f"DUTY_{module}",
                name=f"Complete {module} Module",
                module=str(module),
                value="Completed",
                description=f"Complete the {module} assessment before transfer",
            ))

        # Build duty info for non-assessment actions
        for action in req_actions:
            if action.lower().strip() not in assessment_aliases and action.lower().strip() not in duty_name_to_module:
                duties.append(DutyInfo(
                    duty_id=f"DUTY_{str(action).replace(' ', '_')}",
                    name=str(action),
                    module="action",
                    value="required",
                ))

        if outcome_str == 'prohibition':
            prohibitions.append(ProhibitionInfo(
                prohibition_id=f"PROHIB_{row.get('rule_id')}",
                name=row.get('name', ''),
                description=row.get('description', ''),
            ))
        else:
            permissions.append(PermissionInfo(
                permission_id=f"PERM_{row.get('rule_id')}",
                name=row.get('name', ''),
                description=row.get('description', ''),
                duties=duties,
            ))

        # Populate matched_entities from context.triggered_node_mappings
        rule_id_str = str(row.get('rule_id', ''))
        matched_entities = {}
        if context and hasattr(context, 'triggered_node_mappings'):
            matched_entities = context.triggered_node_mappings.get(rule_id_str, {})

        return TriggeredRule(
            rule_id=rule_id_str,
            rule_name=str(row.get('name', '')),
            rule_type=rule_type,
            priority=str(row.get('priority', 'medium')),
            origin_match_type=str(row.get('origin_match_type', 'any')),
            receiving_match_type=str(row.get('receiving_match_type', 'any')),
            odrl_type=str(row.get('odrl_type', 'Permission')),
            has_pii_required=bool(row.get('requires_pii', False)),
            description=str(row.get('description', '')),
            outcome=outcome,
            permissions=permissions,
            prohibitions=prohibitions,
            required_actions=req_actions,
            required_assessments=sorted(assessment_modules),
            matched_entities=matched_entities,
        )

    # ─── Precedent case search (multi-graph search across DataTransferGraph + external graphs) ───

    def _search_precedent_cases(
        self,
        context: EvaluationContext,
        required_assessments: Dict[str, bool],
    ) -> PrecedentValidation:
        match_parts = ["MATCH (c:Case)"]
        where_conditions = ["c.case_status IN ['Completed', 'Complete', 'Active', 'Published']"]
        params = {}
        applied_filters = []

        if context.origin_country:
            match_parts.append("MATCH (c)-[:ORIGINATES_FROM]->(origin:Country {name: $origin_country})")
            params["origin_country"] = context.origin_country
            applied_filters.append(f"origin={context.origin_country}")

        if context.receiving_country:
            match_parts.append("MATCH (c)-[:TRANSFERS_TO]->(receiving:Jurisdiction {name: $receiving_country})")
            params["receiving_country"] = context.receiving_country
            applied_filters.append(f"receiving={context.receiving_country}")

        if context.purposes:
            match_parts.append("MATCH (c)-[:HAS_PURPOSE]->(p:Purpose)")
            where_conditions.append("p.name IN $purposes")
            params["purposes"] = context.purposes
            applied_filters.append(f"purposes={context.purposes}")

        if context.process_l1:
            match_parts.append("MATCH (c)-[:HAS_PROCESS_L1]->(pl1:ProcessL1)")
            where_conditions.append("pl1.name IN $process_l1")
            params["process_l1"] = context.process_l1

        if context.process_l2:
            match_parts.append("MATCH (c)-[:HAS_PROCESS_L2]->(pl2:ProcessL2)")
            where_conditions.append("pl2.name IN $process_l2")
            params["process_l2"] = context.process_l2

        if context.process_l3:
            match_parts.append("MATCH (c)-[:HAS_PROCESS_L3]->(pl3:ProcessL3)")
            where_conditions.append("pl3.name IN $process_l3")
            params["process_l3"] = context.process_l3

        base_query = "\n".join(match_parts)
        if where_conditions:
            base_query += "\nWHERE " + " AND ".join(where_conditions)

        # Count total matches
        count_query = base_query + "\nRETURN count(c) as total"
        try:
            total_result = self.db.execute_data_query(count_query, params=params or None)
            total_matches = total_result[0].get('total', 0) if total_result else 0
        except Exception as e:
            logger.warning(f"Error counting precedent cases: {e}")
            total_matches = 0

        # Build compliant query with assessment filters
        assessment_conditions = []
        if required_assessments.get('pia'):
            assessment_conditions.append("c.pia_status = 'Completed'")
        if required_assessments.get('tia'):
            assessment_conditions.append("c.tia_status = 'Completed'")
        if required_assessments.get('hrpr'):
            assessment_conditions.append("c.hrpr_status = 'Completed'")

        if assessment_conditions:
            all_conditions = where_conditions + assessment_conditions
            compliant_query = "\n".join(match_parts)
            compliant_query += "\nWHERE " + " AND ".join(all_conditions)
        else:
            compliant_query = base_query

        compliant_query += """
OPTIONAL MATCH (c)-[:HAS_PURPOSE]->(purpose:Purpose)
OPTIONAL MATCH (c)-[:HAS_PROCESS_L1]->(proc_l1:ProcessL1)
OPTIONAL MATCH (c)-[:HAS_PROCESS_L2]->(proc_l2:ProcessL2)
OPTIONAL MATCH (c)-[:HAS_PROCESS_L3]->(proc_l3:ProcessL3)
OPTIONAL MATCH (c)-[:HAS_PERSONAL_DATA]->(pdn:PersonalData)
OPTIONAL MATCH (c)-[:HAS_PERSONAL_DATA_CATEGORY]->(dc:PersonalDataCategory)
WITH c,
     collect(DISTINCT purpose.name) as purposes,
     collect(DISTINCT proc_l1.name) as process_l1,
     collect(DISTINCT proc_l2.name) as process_l2,
     collect(DISTINCT proc_l3.name) as process_l3,
     collect(DISTINCT pdn.name) as personal_data_names,
     collect(DISTINCT dc.name) as data_categories
RETURN c, purposes, process_l1, process_l2, process_l3, personal_data_names, data_categories
LIMIT 10"""

        try:
            compliant_result = self.db.execute_data_query(compliant_query, params=params or None)
        except Exception as e:
            logger.warning(f"Error searching compliant cases: {e}")
            compliant_result = []

        # Query additional precedent graphs (if configured)
        if self.additional_precedent_graphs:
            try:
                from services.multi_graph_query import MultiGraphQuery
                multi_query = MultiGraphQuery()

                # Build queries for each additional graph
                additional_queries = {}
                for graph_name in self.additional_precedent_graphs:
                    try:
                        # Check if graph exists and is enabled
                        from services.graph_registry import get_graph_registry
                        registry = get_graph_registry()
                        graph_meta = registry.get_graph(graph_name)
                        if graph_meta and graph_meta.enabled:
                            additional_queries[graph_name] = (compliant_query, params or {})
                    except Exception:
                        pass

                if additional_queries:
                    logger.info(f"Querying {len(additional_queries)} additional precedent graphs: {list(additional_queries.keys())}")
                    additional_results = multi_query.multi_query(additional_queries)

                    # Merge results from additional graphs
                    for graph_name, rows in additional_results.items():
                        if rows:
                            logger.info(f"Found {len(rows)} precedent cases in {graph_name}")
                            compliant_result.extend(rows)
            except Exception as e:
                logger.warning(f"Error querying additional precedent graphs: {e}")

        # Build case matches
        matching_cases = []
        for row in compliant_result:
            case_data = row.get('c', {})
            if not case_data:
                continue
            case_purposes = [p for p in (row.get('purposes', []) or []) if p]
            case_l1 = [p for p in (row.get('process_l1', []) or []) if p]
            case_l2 = [p for p in (row.get('process_l2', []) or []) if p]
            case_l3 = [p for p in (row.get('process_l3', []) or []) if p]
            personal_data = [p for p in (row.get('personal_data_names', []) or []) if p]
            data_cats = [p for p in (row.get('data_categories', []) or []) if p]

            field_matches = self._compute_field_matches(
                context, case_purposes, case_l1, case_l2, case_l3, personal_data,
            )
            match_score = self._compute_match_score(field_matches)
            relevance = self._build_relevance_explanation(
                context, case_data, case_purposes, case_l1, match_score,
            )

            matching_cases.append(CaseMatch(
                case_id=str(case_data.get('case_id', '')),
                case_ref_id=str(case_data.get('case_ref_id', '')),
                case_status=str(case_data.get('case_status', '')),
                origin_country=context.origin_country,
                receiving_country=context.receiving_country,
                pia_status=case_data.get('pia_status'),
                tia_status=case_data.get('tia_status'),
                hrpr_status=case_data.get('hrpr_status'),
                is_compliant=True,
                purposes=case_purposes,
                process_l1=case_l1,
                process_l2=case_l2,
                process_l3=case_l3,
                personal_data_names=personal_data,
                data_categories=data_cats,
                created_date=case_data.get('created_date'),
                last_updated=case_data.get('last_updated'),
                match_score=match_score,
                field_matches=field_matches,
                relevance_explanation=relevance,
            ))

        matching_cases.sort(key=lambda c: c.match_score, reverse=True)
        compliant_count = len(matching_cases)
        evidence_summary = self._build_evidence_summary(
            context, matching_cases, total_matches, required_assessments,
        )
        filters_info = f" (filters: {', '.join(applied_filters)})" if applied_filters else ""
        msg = (
            f"Found {compliant_count} compliant case(s) out of {total_matches} total matches{filters_info}"
            if total_matches > 0
            else f"No matching cases found{filters_info}"
        )

        return PrecedentValidation(
            total_matches=total_matches,
            compliant_matches=compliant_count,
            has_valid_precedent=compliant_count > 0,
            matching_cases=matching_cases,
            evidence_summary=evidence_summary,
            message=msg,
        )

    # ─── Field matching helpers ─────────────────────────────────────────

    def _compute_field_matches(
        self, context, case_purposes, case_l1, case_l2, case_l3, case_pd,
    ) -> List[FieldMatch]:
        field_matches = [
            FieldMatch(field_name="origin_country", query_values=[context.origin_country],
                       case_values=[context.origin_country], match_type="exact", match_percentage=100.0),
            FieldMatch(field_name="receiving_country", query_values=[context.receiving_country],
                       case_values=[context.receiving_country], match_type="exact", match_percentage=100.0),
        ]
        for field_name, query_vals, case_vals in [
            ("purposes", context.purposes, case_purposes),
            ("process_l1", context.process_l1, case_l1),
            ("process_l2", context.process_l2, case_l2),
            ("process_l3", context.process_l3, case_l3),
            ("personal_data_names", context.personal_data_names, case_pd),
        ]:
            if query_vals:
                overlap = set(query_vals) & set(case_vals)
                pct = (len(overlap) / len(query_vals) * 100) if query_vals else 0
                mt = "exact" if pct == 100 else ("partial" if pct > 0 else "none")
                field_matches.append(FieldMatch(
                    field_name=field_name, query_values=query_vals,
                    case_values=case_vals, match_type=mt, match_percentage=round(pct, 1),
                ))
        return field_matches

    def _compute_match_score(self, field_matches: List[FieldMatch]) -> float:
        if not field_matches:
            return 1.0
        weights = {
            "origin_country": 0.25, "receiving_country": 0.25,
            "purposes": 0.15, "process_l1": 0.10,
            "process_l2": 0.08, "process_l3": 0.07,
            "personal_data_names": 0.10,
        }
        total_w = sum(weights.get(fm.field_name, 0.05) for fm in field_matches)
        weighted = sum(weights.get(fm.field_name, 0.05) * (fm.match_percentage / 100.0) for fm in field_matches)
        return round(weighted / total_w, 3) if total_w > 0 else 1.0

    def _build_relevance_explanation(self, context, case_data, case_purposes, case_l1, score) -> str:
        case_ref = case_data.get('case_ref_id', case_data.get('case_id', 'Unknown'))
        parts = [f"Case {case_ref} is a precedent for {context.origin_country} to {context.receiving_country} transfers"]
        assessments = [a for a in ['PIA', 'TIA', 'HRPR'] if case_data.get(f'{a.lower()}_status') == 'Completed']
        if assessments:
            parts.append(f"with completed {', '.join(assessments)} assessments")
        if context.purposes and case_purposes:
            overlap = set(context.purposes) & set(case_purposes)
            if overlap:
                parts.append(f"covering purposes: {', '.join(overlap)}")
        if score >= 0.9:
            parts.append("(strong match)")
        elif score >= 0.7:
            parts.append("(good match)")
        elif score >= 0.5:
            parts.append("(partial match)")
        return ". ".join(parts) + "."

    def _build_evidence_summary(self, context, matching_cases, total_matches, required_assessments) -> EvidenceSummary:
        if not matching_cases:
            return EvidenceSummary(
                total_cases_searched=total_matches, compliant_cases_found=0,
                confidence_level="low",
                evidence_narrative=f"No compliant precedent cases found for {context.origin_country} to {context.receiving_country} transfers.",
            )
        all_purposes = set()
        all_cats = set()
        best_score = 0.0
        best_id = None
        for c in matching_cases:
            all_purposes.update(c.purposes)
            all_cats.update(c.data_categories)
            if c.match_score > best_score:
                best_score = c.match_score
                best_id = c.case_ref_id or c.case_id
        assessment_coverage = {}
        for key in ['pia', 'tia', 'hrpr']:
            if required_assessments.get(key):
                n = sum(1 for c in matching_cases if getattr(c, f'{key}_status', None) == 'Completed')
                assessment_coverage[key.upper()] = f"{n}/{len(matching_cases)} cases completed"
        confidence = "high" if best_score >= 0.9 and len(matching_cases) >= 2 else ("medium" if best_score >= 0.7 else "low")
        parts = [f"Found {len(matching_cases)} compliant precedent case(s) out of {total_matches} total for {context.origin_country} to {context.receiving_country}."]
        if best_id:
            parts.append(f"Strongest precedent: case {best_id} with {best_score:.0%} match.")
        if all_purposes:
            parts.append(f"Covered purposes: {', '.join(sorted(all_purposes)[:5])}.")
        if assessment_coverage:
            parts.append("Assessment: " + "; ".join(f"{k}: {v}" for k, v in assessment_coverage.items()) + ".")
        return EvidenceSummary(
            total_cases_searched=total_matches, compliant_cases_found=len(matching_cases),
            strongest_match_score=best_score, strongest_match_case_id=best_id,
            common_purposes=sorted(all_purposes)[:10], common_data_categories=sorted(all_cats)[:10],
            assessment_coverage=assessment_coverage, confidence_level=confidence,
            evidence_narrative=" ".join(parts),
        )

    def _build_evaluation_graph(
        self,
        context: EvaluationContext,
        triggered_rules: List[TriggeredRule],
        required_assessments: Dict[str, bool],
        consolidated_duties: List[str]
    ) -> EvaluationGraph:
        """Dynamically build an EvaluationGraph for the React Flow frontend visualization."""
        nodes: List[EvaluationNode] = []
        edges: List[EvaluationEdge] = []
        node_ids = set()
        
        def add_node(n_id: str, label: str, node_type: str, n_data: dict):
            if n_id not in node_ids:
                from utils.schema_manager import get_rf_type_for_label, get_lane_for_label
                nodes.append(EvaluationNode(
                    id=n_id,
                    type=get_rf_type_for_label(node_type),
                    data={"label": label, "nodeType": node_type, "lane": get_lane_for_label(node_type), **n_data}
                ))
                node_ids.add(n_id)
                
        def add_edge(source: str, target: str, rel: str):
            edge_id = f"e_{source}_{target}"
            edges.append(EvaluationEdge(
                id=edge_id,
                source=source,
                target=target,
                type="laneEdge",
                data={"relationship": rel}
            ))

        # 1. Base Countries
        norm_orig = context.origin_country
        norm_recv = context.receiving_country
        
        if norm_orig:
            add_node(f"country_{norm_orig}", norm_orig, "Country", {"countryCount": 1})
        if norm_recv:
            add_node(f"country_{norm_recv}", norm_recv, "Country", {"countryCount": 1})
            
        # 2. Add properties from Context
        for dc in context.data_categories:
            add_node(f"dc_{dc}", dc, "DataCategory", {})
            if norm_orig:
                add_edge(f"country_{norm_orig}", f"dc_{dc}", "HAS_DATA_CATEGORY")
                
        for purp in context.purposes:
            add_node(f"purp_{purp}", purp, "Purpose", {})
            if norm_orig:
                add_edge(f"country_{norm_orig}", f"purp_{purp}", "HAS_PURPOSE")

        # 3. Add Triggered Rules & Link
        for rule in triggered_rules:
            r_id = f"rule_{rule.rule_id}"
            add_node(r_id, rule.rule_name, "Rule", {
                "ruleId": rule.rule_id,
                "odrlType": rule.outcome.value.title(),
                "description": rule.description
            })
            
            if norm_orig:
                add_edge(f"country_{norm_orig}", r_id, "TRIGGERED_BY_ORIGIN")
            if norm_recv:
                add_edge(r_id, f"country_{norm_recv}", "TRIGGERED_BY_RECEIVING")

            # Link Rule to component duty parameters
            if rule.permissions:
                for perm in rule.permissions:
                    for duty in (perm.duties or []):
                        if duty.name:
                            duty_id = f"duty_{duty.name}"
                            add_node(duty_id, duty.name, "Duty", {"subType": "Action"})
                            add_edge(r_id, duty_id, "HAS_DUTY")
                            
        # 4. Global Assessments attached to the transfer as duties
        for module in ["pia", "tia", "hrpr"]:
            if required_assessments.get(module):
                mod_id = f"mod_{module.upper()}"
                add_node(mod_id, module.upper(), "Duty", {"subType": "Assessment"})
                # Link to all rules that required it
                for rule in triggered_rules:
                    r_id = f"rule_{rule.rule_id}"
                    add_edge(r_id, mod_id, "CAN_HAVE_DUTY")
                    
        return EvaluationGraph(nodes=nodes, edges=edges)

# Singleton
_evaluator: Optional[RulesEvaluator] = None


def get_rules_evaluator() -> RulesEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = RulesEvaluator()
    return _evaluator
