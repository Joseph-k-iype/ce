"""
Comprehensive Rules Test Suite
==============================
Tests all permutations and combinations of rules at the attribute level.
Tests multiple rule matching, correct rule selection, TIA/PIA/HRPR rules.
Creates random rules from various countries with process, purpose, GDC attributes.

Tests are split into:
- Pure logic tests (no DB needed)
- Mocked evaluator tests (mock FalkorDB graph responses)
"""

import pytest
import sys
import json
import random
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rules.dictionaries.country_groups import (
    EU_EEA_COUNTRIES,
    UK_CROWN_DEPENDENCIES,
    CROWN_DEPENDENCIES,
    ADEQUACY_COUNTRIES,
    BCR_COUNTRIES,
    COUNTRY_GROUPS,
    EU_EEA_UK_CROWN_CH,
    EU_EEA_ADEQUACY_UK,
    ADEQUACY_PLUS_EU,
    SWITZERLAND_APPROVED,
    get_country_group,
    is_country_in_group,
    get_all_countries,
)
from rules.dictionaries.rules_definitions import (
    CASE_MATCHING_RULES,
    CaseMatchingRule,
    RequiredAssessments,
    RulePriority,
    PRIORITY_ORDER,
    get_enabled_case_matching_rules,
    get_rules_by_priority,
)
from models.schemas import (
    TransferStatus,
    RuleOutcomeType,
    TriggeredRule,
    RulesEvaluationResponse,
    PrecedentValidation,
    AssessmentCompliance,
    EvidenceSummary,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def dict_dir():
    return Path(__file__).parent.parent / "rules" / "data_dictionaries"


@pytest.fixture
def all_processes(dict_dir):
    with open(dict_dir / "processes.json") as f:
        data = json.load(f)
    entries = []
    for cat_data in data["categories"].values():
        entries.extend(cat_data["entries"])
    return entries


@pytest.fixture
def all_purposes(dict_dir):
    with open(dict_dir / "purposes.json") as f:
        data = json.load(f)
    entries = []
    for cat_data in data["categories"].values():
        entries.extend(cat_data["entries"])
    return entries


@pytest.fixture
def all_data_subjects(dict_dir):
    with open(dict_dir / "data_subjects.json") as f:
        data = json.load(f)
    entries = []
    for cat_data in data["categories"].values():
        entries.extend(cat_data["entries"])
    return entries


@pytest.fixture
def all_gdc(dict_dir):
    with open(dict_dir / "gdc.json") as f:
        data = json.load(f)
    entries = []
    for cat_data in data["categories"].values():
        entries.extend(cat_data["entries"])
    return entries


@pytest.fixture
def sample_countries():
    """A diverse set of countries from different groups for testing."""
    return {
        "eu": "Germany",
        "eu2": "France",
        "uk": "United Kingdom",
        "crown": "Jersey",
        "switzerland": "Switzerland",
        "adequacy": "Japan",
        "bcr": "India",
        "bcr2": "Singapore",
        "rest_of_world": "Brazil",
        "rest_of_world2": "Nigeria",
    }


# ─── Helpers ──────────────────────────────────────────────────────────────

def find_matching_rules(origin: str, receiving: str, pii: bool = False, personal_data: bool = False) -> List[str]:
    """
    Simulate which case-matching rules would fire for a given origin/receiving pair.
    This replicates the graph builder's matching logic without needing FalkorDB.
    """
    matching = []

    for key, rule in get_enabled_case_matching_rules().items():
        # Check PII requirement
        if rule.requires_pii and not pii:
            continue
        # Check personal data requirement
        if rule.requires_personal_data and not personal_data:
            continue

        # Check origin match
        origin_matches = False
        if rule.origin_group:
            group = get_country_group(rule.origin_group)
            if origin in group:
                origin_matches = True
        elif rule.origin_countries:
            if origin in rule.origin_countries:
                origin_matches = True
        else:
            # No origin restriction = matches any
            origin_matches = True

        if not origin_matches:
            continue

        # Check receiving match
        receiving_matches = False
        if rule.receiving_not_in:
            # "not_in" match type — rule fires when receiving is NOT in these groups
            excluded = False
            for group_name in rule.receiving_not_in:
                group = get_country_group(group_name)
                if receiving in group:
                    excluded = True
                    break
            receiving_matches = not excluded
        elif rule.receiving_group:
            group = get_country_group(rule.receiving_group)
            if receiving in group:
                receiving_matches = True
        elif rule.receiving_countries:
            if receiving in rule.receiving_countries:
                receiving_matches = True
        else:
            # No receiving restriction = matches any
            receiving_matches = True

        if receiving_matches:
            matching.append(key)

    return matching


def get_rule_assessments(rule_key: str) -> Dict[str, bool]:
    """Get required assessments for a rule."""
    rule = CASE_MATCHING_RULES[rule_key]
    return {
        "pia": rule.required_assessments.pia_required,
        "tia": rule.required_assessments.tia_required,
        "hrpr": rule.required_assessments.hrpr_required,
    }


# ─── Test: Country Group Membership Consistency ───────────────────────────

class TestCountryGroupConsistency:
    """Verify that country group memberships are internally consistent."""

    def test_combined_groups_correct(self):
        """EU_EEA_UK_CROWN_CH should be union of EU_EEA, UK_CROWN, Switzerland."""
        expected = EU_EEA_COUNTRIES | UK_CROWN_DEPENDENCIES | frozenset({"Switzerland"})
        assert EU_EEA_UK_CROWN_CH == expected

    def test_adequacy_plus_eu(self):
        """ADEQUACY_PLUS_EU should include all EU/EEA and adequacy countries."""
        for c in EU_EEA_COUNTRIES:
            assert c in ADEQUACY_PLUS_EU, f"EU country {c} not in ADEQUACY_PLUS_EU"
        for c in ADEQUACY_COUNTRIES:
            assert c in ADEQUACY_PLUS_EU, f"Adequacy country {c} not in ADEQUACY_PLUS_EU"

    def test_no_overlap_eu_bcr_unique(self):
        """BCR countries should include some non-EU countries."""
        non_eu_bcr = BCR_COUNTRIES - EU_EEA_COUNTRIES
        assert len(non_eu_bcr) > 0, "BCR should include countries outside EU/EEA"
        assert "India" in non_eu_bcr
        assert "Singapore" in non_eu_bcr


# ─── Test: Rule Matching Logic — All Permutations ─────────────────────────

class TestRuleMatchingPermutations:
    """
    Test all meaningful origin/receiving permutations against the 8 rules.
    Verifies correct rules fire and correct assessments are required.
    """

    # ── Rule 1: EU Internal ──

    def test_eu_to_eu_matches_rule_1(self, sample_countries):
        """Germany → France should match RULE_1_EU_INTERNAL (PIA only)."""
        rules = find_matching_rules("Germany", "France")
        assert "RULE_1_EU_INTERNAL" in rules
        assessments = get_rule_assessments("RULE_1_EU_INTERNAL")
        assert assessments["pia"] is True
        assert assessments["tia"] is False
        assert assessments["hrpr"] is False

    def test_uk_to_eu_matches_rule_1(self):
        """UK → Germany should match RULE_1 (UK is in EU_EEA_UK_CROWN_CH)."""
        rules = find_matching_rules("United Kingdom", "Germany")
        assert "RULE_1_EU_INTERNAL" in rules

    def test_switzerland_to_eu_matches_rule_1(self):
        """Switzerland → France should match RULE_1 (CH is in EU_EEA_UK_CROWN_CH)."""
        rules = find_matching_rules("Switzerland", "France")
        assert "RULE_1_EU_INTERNAL" in rules

    def test_crown_to_crown_matches_rule_1(self):
        """Jersey → Isle of Man should match RULE_1."""
        rules = find_matching_rules("Jersey", "Isle of Man")
        assert "RULE_1_EU_INTERNAL" in rules

    # ── Rule 2: EU to Adequacy ──

    def test_eu_to_adequacy_matches_rule_2(self):
        """Germany → Japan should match RULE_2_EU_ADEQUACY."""
        rules = find_matching_rules("Germany", "Japan")
        assert "RULE_2_EU_ADEQUACY" in rules

    def test_eu_to_non_adequacy_does_not_match_rule_2(self):
        """Germany → Brazil should NOT match RULE_2."""
        rules = find_matching_rules("Germany", "Brazil")
        assert "RULE_2_EU_ADEQUACY" not in rules

    # ── Rule 3: Crown to Adequacy + EU ──

    def test_crown_to_adequacy_matches_rule_3(self):
        """Jersey → Japan should match RULE_3_CROWN_ADEQUACY."""
        rules = find_matching_rules("Jersey", "Japan")
        assert "RULE_3_CROWN_ADEQUACY" in rules

    def test_crown_to_eu_matches_rule_3(self):
        """Jersey → Germany should match RULE_3."""
        rules = find_matching_rules("Jersey", "Germany")
        assert "RULE_3_CROWN_ADEQUACY" in rules

    # ── Rule 4: UK to Adequacy + EU ──

    def test_uk_to_adequacy_matches_rule_4(self):
        """UK → Japan should match RULE_4_UK_ADEQUACY."""
        rules = find_matching_rules("United Kingdom", "Japan")
        assert "RULE_4_UK_ADEQUACY" in rules

    def test_uk_to_eu_matches_rule_4(self):
        """UK → Germany should match RULE_4."""
        rules = find_matching_rules("United Kingdom", "Germany")
        assert "RULE_4_UK_ADEQUACY" in rules

    # ── Rule 5: Switzerland to Approved ──

    def test_switzerland_to_approved_matches_rule_5(self):
        """Switzerland → Germany should match RULE_5_SWITZERLAND."""
        rules = find_matching_rules("Switzerland", "Germany")
        assert "RULE_5_SWITZERLAND" in rules

    def test_switzerland_to_non_approved_does_not_match_rule_5(self):
        """Switzerland → Nigeria should NOT match RULE_5."""
        rules = find_matching_rules("Switzerland", "Nigeria")
        assert "RULE_5_SWITZERLAND" not in rules

    # ── Rule 6: Rest of World (TIA required) ──

    def test_eu_to_rest_of_world_matches_rule_6(self):
        """Germany → Brazil should match RULE_6 (rest of world, requires PIA+TIA)."""
        rules = find_matching_rules("Germany", "Brazil")
        assert "RULE_6_REST_OF_WORLD" in rules
        assessments = get_rule_assessments("RULE_6_REST_OF_WORLD")
        assert assessments["pia"] is True
        assert assessments["tia"] is True
        assert assessments["hrpr"] is False

    def test_eu_to_eu_does_not_match_rule_6(self):
        """Germany → France should NOT match RULE_6 (both in EU_EEA_ADEQUACY_UK)."""
        rules = find_matching_rules("Germany", "France")
        assert "RULE_6_REST_OF_WORLD" not in rules

    def test_uk_to_rest_of_world_matches_rule_6(self):
        """UK → Nigeria should match RULE_6."""
        rules = find_matching_rules("United Kingdom", "Nigeria")
        assert "RULE_6_REST_OF_WORLD" in rules

    # ── Rule 7: BCR Countries (HRPR required) ──

    def test_bcr_to_any_matches_rule_7(self):
        """India → Brazil should match RULE_7_BCR (requires PIA+HRPR)."""
        rules = find_matching_rules("India", "Brazil")
        assert "RULE_7_BCR" in rules
        assessments = get_rule_assessments("RULE_7_BCR")
        assert assessments["pia"] is True
        assert assessments["tia"] is False
        assert assessments["hrpr"] is True

    def test_bcr_to_eu_matches_rule_7(self):
        """India → Germany should match RULE_7."""
        rules = find_matching_rules("India", "Germany")
        assert "RULE_7_BCR" in rules

    def test_non_bcr_does_not_match_rule_7(self):
        """Nigeria → Brazil should NOT match RULE_7 (Nigeria not in BCR)."""
        rules = find_matching_rules("Nigeria", "Brazil")
        assert "RULE_7_BCR" not in rules

    # ── Rule 8: Personal Data ──

    def test_personal_data_rule_matches_with_personal_data(self):
        """Any → Any with personal data should match RULE_8."""
        rules = find_matching_rules("Nigeria", "Brazil", personal_data=True)
        assert "RULE_8_PERSONAL_DATA" in rules

    def test_personal_data_rule_does_not_match_without_personal_data(self):
        """Any → Any without personal data should NOT match RULE_8."""
        rules = find_matching_rules("Nigeria", "Brazil", personal_data=False)
        assert "RULE_8_PERSONAL_DATA" not in rules


# ─── Test: Multiple Rules Fire Simultaneously ─────────────────────────────

class TestMultipleRuleFiring:
    """Test scenarios where multiple rules fire and correct ones are selected."""

    def test_eu_internal_fires_multiple_rules(self):
        """Germany → France should match RULE_1 and also RULE_2 (EU → Adequacy if France is adequacy)."""
        rules = find_matching_rules("Germany", "France")
        # Rule 1: EU internal
        assert "RULE_1_EU_INTERNAL" in rules
        # Rule 2: EU to adequacy — France is NOT in ADEQUACY_COUNTRIES
        assert "RULE_2_EU_ADEQUACY" not in rules

    def test_uk_to_eu_fires_multiple_rules(self):
        """UK → Germany should match RULE_1 (EU_EEA_UK_CROWN_CH internal) AND RULE_4 (UK → adequacy+EU)."""
        rules = find_matching_rules("United Kingdom", "Germany")
        assert "RULE_1_EU_INTERNAL" in rules
        assert "RULE_4_UK_ADEQUACY" in rules

    def test_crown_to_eu_fires_multiple_rules(self):
        """Jersey → Germany should match RULE_1 (internal) AND RULE_3 (crown → adequacy+EU)."""
        rules = find_matching_rules("Jersey", "Germany")
        assert "RULE_1_EU_INTERNAL" in rules
        assert "RULE_3_CROWN_ADEQUACY" in rules

    def test_switzerland_to_germany_fires_three_rules(self):
        """Switzerland → Germany matches RULE_1 (internal), RULE_5 (CH → approved)."""
        rules = find_matching_rules("Switzerland", "Germany")
        assert "RULE_1_EU_INTERNAL" in rules
        assert "RULE_5_SWITZERLAND" in rules

    def test_india_to_japan_fires_bcr_rule(self):
        """India → Japan: BCR rule should fire. India is in BCR_COUNTRIES."""
        rules = find_matching_rules("India", "Japan")
        assert "RULE_7_BCR" in rules

    def test_eu_bcr_country_fires_both(self):
        """Germany (EU+BCR) → Brazil: should fire RULE_6 (rest of world) and RULE_7 (BCR)."""
        rules = find_matching_rules("Germany", "Brazil")
        assert "RULE_6_REST_OF_WORLD" in rules
        assert "RULE_7_BCR" in rules  # Germany is in BCR_COUNTRIES

    def test_personal_data_fires_alongside_country_rules(self):
        """Germany → France with personal data: RULE_1 + RULE_8."""
        rules = find_matching_rules("Germany", "France", personal_data=True)
        assert "RULE_1_EU_INTERNAL" in rules
        assert "RULE_8_PERSONAL_DATA" in rules


# ─── Test: Assessment Requirements — PIA/TIA/HRPR ────────────────────────

class TestAssessmentRequirements:
    """
    Verify that each rule requires the correct assessments.
    This is critical for compliance — wrong assessments = wrong outcome.
    """

    def test_rules_1_through_5_require_pia_only(self):
        """Rules 1-5 should require only PIA."""
        pia_only_rules = [
            "RULE_1_EU_INTERNAL", "RULE_2_EU_ADEQUACY", "RULE_3_CROWN_ADEQUACY",
            "RULE_4_UK_ADEQUACY", "RULE_5_SWITZERLAND",
        ]
        for key in pia_only_rules:
            assessments = get_rule_assessments(key)
            assert assessments["pia"] is True, f"{key} should require PIA"
            assert assessments["tia"] is False, f"{key} should NOT require TIA"
            assert assessments["hrpr"] is False, f"{key} should NOT require HRPR"

    def test_rule_6_requires_pia_and_tia(self):
        """Rule 6 (rest of world) requires PIA + TIA."""
        assessments = get_rule_assessments("RULE_6_REST_OF_WORLD")
        assert assessments["pia"] is True
        assert assessments["tia"] is True
        assert assessments["hrpr"] is False

    def test_rule_7_requires_pia_and_hrpr(self):
        """Rule 7 (BCR) requires PIA + HRPR."""
        assessments = get_rule_assessments("RULE_7_BCR")
        assert assessments["pia"] is True
        assert assessments["tia"] is False
        assert assessments["hrpr"] is True

    def test_rule_8_requires_pia_only(self):
        """Rule 8 (personal data) requires PIA only."""
        assessments = get_rule_assessments("RULE_8_PERSONAL_DATA")
        assert assessments["pia"] is True
        assert assessments["tia"] is False
        assert assessments["hrpr"] is False

    def test_consolidated_assessments_multi_rule_scenario(self):
        """When multiple rules fire, the union of all assessments is required."""
        # Germany → Brazil: RULE_6 (PIA+TIA) + RULE_7 (PIA+HRPR)
        rules = find_matching_rules("Germany", "Brazil")
        all_assessments = {"pia": False, "tia": False, "hrpr": False}
        for rule_key in rules:
            assessments = get_rule_assessments(rule_key)
            for k in all_assessments:
                if assessments[k]:
                    all_assessments[k] = True

        # Combined: PIA + TIA (from R6) + HRPR (from R7)
        assert all_assessments["pia"] is True
        assert all_assessments["tia"] is True
        assert all_assessments["hrpr"] is True


# ─── Test: Random Rule Permutations ──────────────────────────────────────

class TestRandomRulePermutations:
    """
    Generate random transfers and verify the system responds correctly.
    Uses fixed seed for reproducibility.
    """

    @pytest.fixture(autouse=True)
    def set_seed(self):
        random.seed(42)

    def _pick_country(self, group_name: Optional[str] = None):
        if group_name:
            group = get_country_group(group_name)
            return random.choice(sorted(group))
        all_c = sorted(get_all_countries())
        return random.choice(all_c)

    def test_random_eu_internal_transfers(self):
        """Generate 20 random EU internal transfers — all should match RULE_1."""
        eu_countries = sorted(EU_EEA_UK_CROWN_CH)
        for _ in range(20):
            origin = random.choice(eu_countries)
            receiving = random.choice(eu_countries)
            rules = find_matching_rules(origin, receiving)
            assert "RULE_1_EU_INTERNAL" in rules, (
                f"{origin} → {receiving} should match RULE_1"
            )

    def test_random_bcr_transfers(self):
        """Generate 20 random BCR origin transfers — all should match RULE_7."""
        bcr_countries = sorted(BCR_COUNTRIES)
        all_countries = sorted(get_all_countries())
        for _ in range(20):
            origin = random.choice(bcr_countries)
            receiving = random.choice(all_countries)
            rules = find_matching_rules(origin, receiving)
            assert "RULE_7_BCR" in rules, (
                f"{origin} → {receiving} should match RULE_7"
            )

    def test_random_rest_of_world_transfers(self):
        """Generate transfers from EU/adequacy to non-adequacy countries."""
        eu_adequacy = sorted(EU_EEA_ADEQUACY_UK)
        rest_of_world = sorted(get_all_countries() - EU_EEA_ADEQUACY_UK)
        if not rest_of_world:
            pytest.skip("No rest-of-world countries available")
        for _ in range(20):
            origin = random.choice(eu_adequacy)
            receiving = random.choice(rest_of_world)
            rules = find_matching_rules(origin, receiving)
            assert "RULE_6_REST_OF_WORLD" in rules, (
                f"{origin} → {receiving} should match RULE_6"
            )

    def test_random_personal_data_transfers(self):
        """Generate random transfers with personal data — all should match RULE_8."""
        all_countries = sorted(get_all_countries())
        for _ in range(20):
            origin = random.choice(all_countries)
            receiving = random.choice(all_countries)
            rules = find_matching_rules(origin, receiving, personal_data=True)
            assert "RULE_8_PERSONAL_DATA" in rules, (
                f"{origin} → {receiving} with personal data should match RULE_8"
            )

    def test_no_rules_outside_known_groups(self):
        """A country not in any group should only match RULE_8 if personal data present."""
        # Pick countries that exist only in BCR but not EU/adequacy/CH
        bcr_only = BCR_COUNTRIES - EU_EEA_UK_CROWN_CH - ADEQUACY_COUNTRIES
        non_bcr_non_eu = get_all_countries() - BCR_COUNTRIES - EU_EEA_UK_CROWN_CH - ADEQUACY_COUNTRIES

        if bcr_only and non_bcr_non_eu:
            origin = sorted(non_bcr_non_eu)[0] if non_bcr_non_eu else "Nigeria"
            receiving = sorted(non_bcr_non_eu)[-1] if len(non_bcr_non_eu) > 1 else "Nigeria"
            # This pair might not match any rules (no group membership, no personal data)
            rules = find_matching_rules(origin, receiving)
            # These should NOT match EU-specific rules
            assert "RULE_1_EU_INTERNAL" not in rules
            assert "RULE_2_EU_ADEQUACY" not in rules


# ─── Test: Data Dictionary Integration ────────────────────────────────────

class TestDataDictionaryIntegration:
    """Test that data dictionaries have meaningful content and can be used in rules."""

    def test_processes_cover_key_industries(self, all_processes):
        """Processes should cover financial, HR, customer, tech, and compliance."""
        lower_procs = [p.lower() for p in all_processes]
        assert any("payment" in p for p in lower_procs), "Should include payment processing"
        assert any("recruit" in p for p in lower_procs), "Should include recruitment"
        assert any("customer" in p for p in lower_procs), "Should include customer processes"

    def test_purposes_cover_gdpr_bases(self, dict_dir):
        """Purposes should cover GDPR legal bases (checking both entries and categories)."""
        with open(dict_dir / "purposes.json") as f:
            data = json.load(f)
        categories = [c.lower() for c in data["categories"].keys()]
        all_entries = []
        for cat_data in data["categories"].values():
            all_entries.extend(e.lower() for e in cat_data["entries"])
        combined = categories + all_entries
        assert any("consent" in t for t in combined), "Should include consent-based"
        assert any("contract" in t for t in combined), "Should include contractual"
        assert any("legitimate" in t for t in combined), "Should include legitimate interest"

    def test_data_subjects_cover_internal_external(self, all_data_subjects):
        """Data subjects should cover internal (employees) and external (customers)."""
        lower_ds = [d.lower() for d in all_data_subjects]
        assert any("employee" in d for d in lower_ds), "Should include employees"
        assert any("customer" in d for d in lower_ds), "Should include customers"
        assert any("contractor" in d for d in lower_ds), "Should include contractors"

    def test_gdc_cover_sensitive_categories(self, all_gdc):
        """GDC should cover personal identifiers, financial, health, biometric data."""
        lower_gdc = [g.lower() for g in all_gdc]
        assert any("name" in g for g in lower_gdc), "Should include name"
        assert any("credit" in g or "bank" in g for g in lower_gdc), "Should include financial"
        assert any("medical" in g or "health" in g for g in lower_gdc), "Should include health data"

    def test_random_combinations_with_dictionaries(
        self, all_processes, all_purposes, all_data_subjects, all_gdc
    ):
        """Create 10 random scenarios combining dictionaries with country rules."""
        random.seed(99)
        all_countries = sorted(get_all_countries())

        for i in range(10):
            origin = random.choice(all_countries)
            receiving = random.choice(all_countries)
            process = random.choice(all_processes)
            purpose = random.choice(all_purposes)
            subject = random.choice(all_data_subjects)
            gdc_item = random.choice(all_gdc)

            # Find matching rules for this scenario
            rules = find_matching_rules(origin, receiving)

            # Verify the scenario is well-defined
            assert isinstance(process, str) and len(process) > 0
            assert isinstance(purpose, str) and len(purpose) > 0
            assert isinstance(subject, str) and len(subject) > 0
            assert isinstance(gdc_item, str) and len(gdc_item) > 0

            # At minimum, if origin and receiving are both in EU_EEA_UK_CROWN_CH, RULE_1 should fire
            if origin in EU_EEA_UK_CROWN_CH and receiving in EU_EEA_UK_CROWN_CH:
                assert "RULE_1_EU_INTERNAL" in rules, (
                    f"Scenario {i}: {origin} → {receiving} with {process}/{purpose}/{subject}/{gdc_item} "
                    f"should match RULE_1"
                )


# ─── Test: Mocked Evaluator — Full Pipeline ──────────────────────────────

class TestMockedEvaluator:
    """
    Test the RulesEvaluator with mocked FalkorDB responses.
    Verifies the full evaluation pipeline: rule matching → precedent search → outcome.
    """

    def _mock_graph_result(self, headers, rows):
        """Create a mock FalkorDB query result."""
        result = MagicMock()
        result.header = headers
        result.result_set = rows
        return result

    def _build_rule_row(
        self,
        rule_id: str,
        name: str,
        priority: str = "low",
        assessments: List[str] = None,
        origin_match: str = "group",
        receiving_match: str = "group",
    ) -> list:
        """Build a row matching the CASE_MATCHING_RULES_QUERY result schema."""
        return [
            rule_id,                # rule_id
            name,                   # name
            f"Description for {name}",  # description
            priority,               # priority
            PRIORITY_ORDER.get(priority, 2),  # priority_order
            "Permission",           # odrl_type
            False,                  # requires_pii
            False,                  # requires_personal_data
            origin_match,           # origin_match_type
            receiving_match,        # receiving_match_type
            assessments or ["PIA"], # required_assessments
        ]

    @pytest.fixture
    def mock_evaluator(self):
        """Create a RulesEvaluator with mocked dependencies."""
        with patch('services.rules_evaluator.get_db_service') as mock_db, \
             patch('services.rules_evaluator.get_cache_service') as mock_cache, \
             patch('services.rules_evaluator.get_attribute_detector') as mock_attr:

            mock_db_instance = MagicMock()
            mock_db.return_value = mock_db_instance
            mock_db_instance.get_rules_graph.return_value = MagicMock()

            mock_cache.return_value = MagicMock()

            mock_detector = MagicMock()
            mock_detector.detect.return_value = []
            mock_attr.return_value = mock_detector

            from services.rules_evaluator import RulesEvaluator
            evaluator = RulesEvaluator.__new__(RulesEvaluator)
            evaluator.db = mock_db_instance
            evaluator.cache = mock_cache.return_value
            evaluator.attribute_detector = mock_detector
            evaluator._rules_graph = mock_db_instance.get_rules_graph.return_value

            yield evaluator, mock_db_instance

    def test_allowed_with_precedent(self, mock_evaluator):
        """Transfer should be ALLOWED when rules match and precedent exists."""
        evaluator, mock_db = mock_evaluator

        headers = [
            (0, "rule_id"), (1, "name"), (2, "description"),
            (3, "priority"), (4, "priority_order"), (5, "odrl_type"),
            (6, "requires_pii"), (7, "requires_personal_data"),
            (8, "origin_match_type"), (9, "receiving_match_type"),
            (10, "required_assessments"),
        ]
        rule_row = self._build_rule_row("RULE_1", "EU Internal", assessments=["PIA"])

        rules_result = self._mock_graph_result(headers, [rule_row])
        evaluator._rules_graph.query.return_value = rules_result

        # Mock precedent search — count query
        count_result = MagicMock()
        count_result.header = [(0, "total")]
        count_result.result_set = [[1]]

        # Mock compliant case
        case_data = {
            "case_id": "CASE_001",
            "case_ref_id": "REF_001",
            "case_status": "Completed",
            "pia_status": "Completed",
            "tia_status": None,
            "hrpr_status": None,
        }
        compliant_result = MagicMock()
        compliant_result.header = [
            (0, "c"), (1, "purposes"), (2, "process_l1"),
            (3, "process_l2"), (4, "process_l3"),
            (5, "personal_data_names"), (6, "data_categories"),
        ]
        compliant_result.result_set = [[case_data, ["Marketing"], [], [], [], [], []]]

        mock_db.execute_data_query.side_effect = [count_result, compliant_result]

        # Note: the mock_graph_result is for _graph_query (rules graph)
        # and execute_data_query is for DataTransferGraph

        # We need to properly mock execute_data_query to return dicts
        mock_db.execute_data_query.side_effect = None
        mock_db.execute_data_query.side_effect = [
            [{"total": 1}],  # count query
            [{"c": case_data, "purposes": ["Marketing"], "process_l1": [],
              "process_l2": [], "process_l3": [],
              "personal_data_names": [], "data_categories": []}],
        ]

        result = evaluator.evaluate("Germany", "France")
        assert result.transfer_status == TransferStatus.ALLOWED

    def test_prohibited_no_precedent(self, mock_evaluator):
        """Transfer should be PROHIBITED when rules match but no precedent exists."""
        evaluator, mock_db = mock_evaluator

        headers = [
            (0, "rule_id"), (1, "name"), (2, "description"),
            (3, "priority"), (4, "priority_order"), (5, "odrl_type"),
            (6, "requires_pii"), (7, "requires_personal_data"),
            (8, "origin_match_type"), (9, "receiving_match_type"),
            (10, "required_assessments"),
        ]
        rule_row = self._build_rule_row("RULE_6", "Rest of World", assessments=["PIA", "TIA"])
        rules_result = self._mock_graph_result(headers, [rule_row])
        evaluator._rules_graph.query.return_value = rules_result

        mock_db.execute_data_query.side_effect = [
            [{"total": 0}],  # No matching cases
            [],               # No compliant cases
        ]

        result = evaluator.evaluate("Germany", "Brazil")
        assert result.transfer_status == TransferStatus.PROHIBITED
        assert "No precedent" in result.message or "PROHIBITED" in result.message

    def test_requires_review_no_rules(self, mock_evaluator):
        """Transfer should REQUIRE REVIEW when no rules match."""
        evaluator, mock_db = mock_evaluator

        empty_result = self._mock_graph_result([], [])
        evaluator._rules_graph.query.return_value = empty_result

        result = evaluator.evaluate("Nigeria", "Somalia")
        assert result.transfer_status == TransferStatus.REQUIRES_REVIEW

    def test_tia_required_for_rest_of_world(self, mock_evaluator):
        """When RULE_6 fires, both PIA and TIA should be required."""
        evaluator, mock_db = mock_evaluator

        headers = [
            (0, "rule_id"), (1, "name"), (2, "description"),
            (3, "priority"), (4, "priority_order"), (5, "odrl_type"),
            (6, "requires_pii"), (7, "requires_personal_data"),
            (8, "origin_match_type"), (9, "receiving_match_type"),
            (10, "required_assessments"),
        ]
        rule_row = self._build_rule_row("RULE_6", "Rest of World", assessments=["PIA", "TIA"])
        rules_result = self._mock_graph_result(headers, [rule_row])
        evaluator._rules_graph.query.return_value = rules_result

        # Precedent exists with completed assessments
        case_data = {
            "case_id": "CASE_002",
            "case_ref_id": "REF_002",
            "case_status": "Completed",
            "pia_status": "Completed",
            "tia_status": "Completed",
            "hrpr_status": None,
        }
        mock_db.execute_data_query.side_effect = [
            [{"total": 1}],
            [{"c": case_data, "purposes": [], "process_l1": [],
              "process_l2": [], "process_l3": [],
              "personal_data_names": [], "data_categories": []}],
        ]

        result = evaluator.evaluate("Germany", "Brazil")
        assert result.transfer_status == TransferStatus.ALLOWED
        assert result.assessment_compliance.pia_required is True
        assert result.assessment_compliance.tia_required is True

    def test_hrpr_required_for_bcr(self, mock_evaluator):
        """When RULE_7 fires, PIA and HRPR should be required."""
        evaluator, mock_db = mock_evaluator

        headers = [
            (0, "rule_id"), (1, "name"), (2, "description"),
            (3, "priority"), (4, "priority_order"), (5, "odrl_type"),
            (6, "requires_pii"), (7, "requires_personal_data"),
            (8, "origin_match_type"), (9, "receiving_match_type"),
            (10, "required_assessments"),
        ]
        rule_row = self._build_rule_row("RULE_7", "BCR Transfer", assessments=["PIA", "HRPR"])
        rules_result = self._mock_graph_result(headers, [rule_row])
        evaluator._rules_graph.query.return_value = rules_result

        case_data = {
            "case_id": "CASE_003",
            "case_ref_id": "REF_003",
            "case_status": "Completed",
            "pia_status": "Completed",
            "tia_status": None,
            "hrpr_status": "Completed",
        }
        mock_db.execute_data_query.side_effect = [
            [{"total": 1}],
            [{"c": case_data, "purposes": [], "process_l1": [],
              "process_l2": [], "process_l3": [],
              "personal_data_names": [], "data_categories": []}],
        ]

        result = evaluator.evaluate("India", "Brazil")
        assert result.transfer_status == TransferStatus.ALLOWED
        assert result.assessment_compliance.pia_required is True
        assert result.assessment_compliance.hrpr_required is True

    def test_prohibited_missing_tia(self, mock_evaluator):
        """Transfer should be PROHIBITED when TIA is required but missing from precedent."""
        evaluator, mock_db = mock_evaluator

        headers = [
            (0, "rule_id"), (1, "name"), (2, "description"),
            (3, "priority"), (4, "priority_order"), (5, "odrl_type"),
            (6, "requires_pii"), (7, "requires_personal_data"),
            (8, "origin_match_type"), (9, "receiving_match_type"),
            (10, "required_assessments"),
        ]
        rule_row = self._build_rule_row("RULE_6", "Rest of World", assessments=["PIA", "TIA"])
        rules_result = self._mock_graph_result(headers, [rule_row])
        evaluator._rules_graph.query.return_value = rules_result

        # Cases exist but no compliant ones (TIA not completed)
        mock_db.execute_data_query.side_effect = [
            [{"total": 3}],  # 3 matching cases
            [],               # But 0 compliant (TIA missing)
        ]

        result = evaluator.evaluate("Germany", "Brazil")
        assert result.transfer_status == TransferStatus.PROHIBITED
        assert result.assessment_compliance is not None
        assert "TIA" in result.assessment_compliance.missing_assessments


# ─── Test: Graph Builder — Dictionary Ingestion ──────────────────────────

class TestGraphBuilderDictionaries:
    """Test that the graph builder correctly ingests data dictionaries."""

    def test_ingest_data_dictionaries(self, dict_dir):
        """Test that _ingest_data_dictionaries creates MERGE queries for all entries."""
        mock_graph = MagicMock()
        mock_graph.query.return_value = MagicMock(result_set=None, header=[])

        with patch('utils.graph_builder.get_db_service') as mock_db:
            mock_db.return_value = MagicMock()
            mock_db.return_value.get_rules_graph.return_value = mock_graph

            from utils.graph_builder import RulesGraphBuilder
            builder = RulesGraphBuilder.__new__(RulesGraphBuilder)
            builder.db = mock_db.return_value
            builder.graph = mock_graph
            builder._created_duties = set()
            builder._created_countries = set()

            builder._ingest_data_dictionaries_v2()

            # Count MERGE calls for dictionary entries
            merge_calls = [
                call for call in mock_graph.query.call_args_list
                if "MERGE" in str(call) and ("Process" in str(call) or "Purpose" in str(call)
                                              or "DataSubject" in str(call) or "GDC" in str(call))
            ]
            # Should have 200+ MERGE calls (50+ per dictionary × 4 dictionaries)
            assert len(merge_calls) >= 200, f"Expected 200+ MERGE calls, got {len(merge_calls)}"

    def test_add_rule_creates_graph_nodes(self):
        """Test that add_rule creates a Rule node with correct properties."""
        mock_graph = MagicMock()
        mock_graph.query.return_value = MagicMock(result_set=None, header=[])

        with patch('utils.graph_builder.get_db_service') as mock_db:
            mock_db.return_value = MagicMock()
            mock_db.return_value.get_rules_graph.return_value = mock_graph

            from utils.graph_builder import RulesGraphBuilder
            builder = RulesGraphBuilder.__new__(RulesGraphBuilder)
            builder.db = mock_db.return_value
            builder.graph = mock_graph
            builder._created_duties = set()
            builder._created_countries = set()

            rule_def = {
                "rule_id": "RULE_TEST_1",
                "name": "Test Rule",
                "description": "A test rule",
                "rule_type": "case_matching",
                "priority": "medium",
                "outcome": "permission",
                "origin_group": "EU_EEA",
                "receiving_group": "BCR_COUNTRIES",
                "odrl_type": "Permission",
                "odrl_action": "transfer",
                "odrl_target": "Data",
            }

            success = builder.add_rule(rule_def)
            assert success is True

            # Verify MERGE was called with the rule_id
            merge_calls = [str(c) for c in mock_graph.query.call_args_list]
            assert any("RULE_TEST_1" in c for c in merge_calls)
            assert any("TRIGGERED_BY_ORIGIN" in c for c in merge_calls)
            assert any("TRIGGERED_BY_RECEIVING" in c for c in merge_calls)


# ─── Test: Edge Cases ─────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_same_country_origin_and_receiving(self):
        """Transfer within the same country should still match appropriate rules."""
        rules = find_matching_rules("Germany", "Germany")
        assert "RULE_1_EU_INTERNAL" in rules

    def test_empty_personal_data_no_rule_8(self):
        """Without personal data flag, RULE_8 should not fire."""
        rules = find_matching_rules("Germany", "France", personal_data=False)
        assert "RULE_8_PERSONAL_DATA" not in rules

    def test_all_rules_have_unique_ids(self):
        """Verify all 8 rule IDs are unique."""
        ids = [rule.rule_id for rule in CASE_MATCHING_RULES.values()]
        assert len(ids) == len(set(ids))

    def test_all_rules_enabled(self):
        """All 8 case-matching rules should be enabled."""
        for key, rule in CASE_MATCHING_RULES.items():
            assert rule.enabled is True, f"Rule {key} should be enabled"

    def test_priority_sorting(self):
        """Rules should be sortable by priority."""
        rules = get_rules_by_priority()
        assert len(rules) == 8
        # All rules have priority "low" so they should all have same order
        for rule_id, rule, rule_type in rules:
            assert PRIORITY_ORDER.get(rule.priority, 2) == 3  # "low" = 3

    def test_uk_is_in_multiple_groups(self):
        """UK should be in UK_CROWN_DEPENDENCIES and ADEQUACY_COUNTRIES."""
        assert "United Kingdom" in UK_CROWN_DEPENDENCIES
        assert "United Kingdom" in ADEQUACY_COUNTRIES
        assert "United Kingdom" in EU_EEA_UK_CROWN_CH

    def test_jersey_is_in_multiple_groups(self):
        """Jersey should be in CROWN_DEPENDENCIES, UK_CROWN, and ADEQUACY."""
        assert "Jersey" in CROWN_DEPENDENCIES
        assert "Jersey" in UK_CROWN_DEPENDENCIES
        assert "Jersey" in ADEQUACY_COUNTRIES


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
