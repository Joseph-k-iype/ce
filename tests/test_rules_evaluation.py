"""
Tests for Rules Evaluation
==========================
Tests for the compliance engine rules evaluation.
Updated for simplified architecture (case-matching rules only).
"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rules.dictionaries.country_groups import (
    EU_EEA_COUNTRIES,
    UK_CROWN_DEPENDENCIES,
    ADEQUACY_COUNTRIES,
    BCR_COUNTRIES,
    COUNTRY_GROUPS,
    get_country_group,
    is_country_in_group,
)
from rules.dictionaries.rules_definitions import (
    CASE_MATCHING_RULES,
    TRANSFER_RULES,
    ATTRIBUTE_RULES,
    get_enabled_case_matching_rules,
    get_enabled_transfer_rules,
    get_enabled_attribute_rules,
    RuleOutcome,
    PRIORITY_ORDER,
)
from rules.templates.cypher_templates import (
    CYPHER_TEMPLATES,
    build_origin_filter,
    build_receiving_filter,
    build_purpose_filter,
    build_assessment_filter,
)


class TestCountryGroups:
    """Tests for country groups"""

    def test_eu_eea_countries(self):
        """Test EU/EEA country group has expected countries"""
        assert "Germany" in EU_EEA_COUNTRIES
        assert "France" in EU_EEA_COUNTRIES
        assert "Spain" in EU_EEA_COUNTRIES
        assert len(EU_EEA_COUNTRIES) >= 27

    def test_uk_crown_dependencies(self):
        """Test UK and Crown Dependencies group"""
        assert "United Kingdom" in UK_CROWN_DEPENDENCIES
        assert "Jersey" in UK_CROWN_DEPENDENCIES
        assert "Guernsey" in UK_CROWN_DEPENDENCIES
        assert "Isle of Man" in UK_CROWN_DEPENDENCIES

    def test_adequacy_countries(self):
        """Test adequacy countries group"""
        assert "Japan" in ADEQUACY_COUNTRIES
        assert "Canada" in ADEQUACY_COUNTRIES
        assert "New Zealand" in ADEQUACY_COUNTRIES

    def test_bcr_countries(self):
        """Test BCR countries group"""
        assert "India" in BCR_COUNTRIES
        assert "Singapore" in BCR_COUNTRIES
        assert "United States of America" in BCR_COUNTRIES

    def test_removed_groups_not_present(self):
        """Test that removed groups (US_RESTRICTED, CHINA_TERRITORIES) are no longer in COUNTRY_GROUPS"""
        assert "US_RESTRICTED" not in COUNTRY_GROUPS
        assert "CHINA_TERRITORIES" not in COUNTRY_GROUPS

    def test_remaining_groups_count(self):
        """Test that we have the expected 10 remaining country groups"""
        expected_groups = {
            "EU_EEA", "UK_CROWN_DEPENDENCIES", "CROWN_DEPENDENCIES", "SWITZERLAND",
            "ADEQUACY_COUNTRIES", "SWITZERLAND_APPROVED", "BCR_COUNTRIES",
            "EU_EEA_UK_CROWN_CH", "EU_EEA_ADEQUACY_UK", "ADEQUACY_PLUS_EU",
        }
        assert set(COUNTRY_GROUPS.keys()) == expected_groups

    def test_get_country_group(self):
        """Test getting country group by name"""
        group = get_country_group("EU_EEA")
        assert "Germany" in group
        assert "France" in group

    def test_is_country_in_group(self):
        """Test checking if country is in group"""
        assert is_country_in_group("Germany", "EU_EEA")
        assert is_country_in_group("United Kingdom", "UK_CROWN_DEPENDENCIES")
        assert not is_country_in_group("United States", "EU_EEA")


class TestCaseMatchingRules:
    """Tests for case-matching rules (SET 1)"""

    def test_rules_exist(self):
        """Test that case-matching rules are defined"""
        assert len(CASE_MATCHING_RULES) == 8

    def test_rule_structure(self):
        """Test that rules have required fields"""
        for key, rule in CASE_MATCHING_RULES.items():
            assert rule.rule_id is not None
            assert rule.name is not None
            assert rule.description is not None
            assert rule.priority is not None
            assert rule.priority in ("high", "medium", "low")
            assert rule.required_assessments is not None

    def test_eu_internal_rule(self):
        """Test EU internal transfer rule"""
        rule = CASE_MATCHING_RULES.get("RULE_1_EU_INTERNAL")
        assert rule is not None
        assert rule.origin_group == "EU_EEA_UK_CROWN_CH"
        assert rule.receiving_group == "EU_EEA_UK_CROWN_CH"
        assert rule.required_assessments.pia_required

    def test_eu_adequacy_rule(self):
        """Test EU to adequacy countries rule"""
        rule = CASE_MATCHING_RULES.get("RULE_2_EU_ADEQUACY")
        assert rule is not None
        assert rule.origin_group == "EU_EEA"
        assert rule.receiving_group == "ADEQUACY_COUNTRIES"
        assert rule.required_assessments.pia_required

    def test_rest_of_world_rule_requires_tia(self):
        """Test rest-of-world rule requires both PIA and TIA"""
        rule = CASE_MATCHING_RULES.get("RULE_6_REST_OF_WORLD")
        assert rule is not None
        assert rule.required_assessments.pia_required
        assert rule.required_assessments.tia_required
        assert not rule.required_assessments.hrpr_required

    def test_bcr_rule(self):
        """Test BCR countries rule"""
        rule = CASE_MATCHING_RULES.get("RULE_7_BCR")
        assert rule is not None
        assert rule.origin_group == "BCR_COUNTRIES"
        assert rule.required_assessments.pia_required
        assert rule.required_assessments.hrpr_required

    def test_personal_data_rule(self):
        """Test personal data transfer rule"""
        rule = CASE_MATCHING_RULES.get("RULE_8_PERSONAL_DATA")
        assert rule is not None
        assert rule.requires_personal_data
        assert rule.origin_countries is None  # any
        assert rule.receiving_countries is None  # any
        assert rule.required_assessments.pia_required

    def test_get_enabled_rules(self):
        """Test getting enabled rules"""
        enabled = get_enabled_case_matching_rules()
        assert len(enabled) == 8
        for key, rule in enabled.items():
            assert rule.enabled

    def test_required_assessments_to_list(self):
        """Test converting required assessments to list"""
        rule = CASE_MATCHING_RULES["RULE_7_BCR"]
        assessments = rule.required_assessments.to_list()
        assert "PIA" in assessments
        assert "HRPR" in assessments
        assert "TIA" not in assessments

        rule6 = CASE_MATCHING_RULES["RULE_6_REST_OF_WORLD"]
        assessments6 = rule6.required_assessments.to_list()
        assert "PIA" in assessments6
        assert "TIA" in assessments6


class TestTransferRulesRemoved:
    """Tests confirming transfer rules (SET 2A) have been emptied"""

    def test_transfer_rules_empty(self):
        """Transfer rules should be empty after simplification"""
        assert len(TRANSFER_RULES) == 0

    def test_get_enabled_transfer_rules_empty(self):
        """No enabled transfer rules should exist"""
        assert len(get_enabled_transfer_rules()) == 0


class TestAttributeRulesRemoved:
    """Tests confirming attribute rules (SET 2B) have been emptied"""

    def test_attribute_rules_empty(self):
        """Attribute rules should be empty after simplification"""
        assert len(ATTRIBUTE_RULES) == 0

    def test_get_enabled_attribute_rules_empty(self):
        """No enabled attribute rules should exist"""
        assert len(get_enabled_attribute_rules()) == 0


class TestCypherTemplates:
    """Tests for Cypher query templates"""

    def test_templates_exist(self):
        """Test that templates are defined"""
        assert len(CYPHER_TEMPLATES) > 0

    def test_template_structure(self):
        """Test that templates have required fields"""
        for key, template in CYPHER_TEMPLATES.items():
            assert template.template_id is not None
            assert template.name is not None
            assert template.query_template is not None

    def test_build_origin_filter(self):
        """Test building origin country filter"""
        filter_str = build_origin_filter("United Kingdom")
        assert "Country" in filter_str
        assert "United Kingdom" not in filter_str  # Uses $origin_country param
        assert "$origin_country" in filter_str

    def test_build_origin_filter_none(self):
        """Test building origin filter with None"""
        filter_str = build_origin_filter(None)
        assert filter_str == ""

    def test_build_receiving_filter(self):
        """Test building receiving country filter"""
        filter_str = build_receiving_filter("India")
        assert "Jurisdiction" in filter_str

    def test_build_purpose_filter(self):
        """Test building purpose filter"""
        filter_str = build_purpose_filter(["Marketing", "Analytics"])
        assert "Purpose" in filter_str

    def test_build_assessment_filter(self):
        """Test building assessment filter"""
        filter_str = build_assessment_filter(pia_required=True, tia_required=True)
        assert "pia_status" in filter_str
        assert "tia_status" in filter_str


class TestRulePriorities:
    """Tests for rule priority ordering"""

    def test_priority_order_mapping(self):
        """Test that priority order maps correctly"""
        assert PRIORITY_ORDER["high"] == 1
        assert PRIORITY_ORDER["medium"] == 2
        assert PRIORITY_ORDER["low"] == 3

    def test_case_matching_rules_have_valid_priority(self):
        """Test that case-matching rules have valid string priorities"""
        valid_priorities = {"high", "medium", "low"}
        for key, rule in CASE_MATCHING_RULES.items():
            assert rule.priority in valid_priorities, f"Rule {key} has invalid priority: {rule.priority}"


class TestRuleConsistency:
    """Tests for rule consistency and validity"""

    def test_unique_rule_ids(self):
        """Test that all rule IDs are unique"""
        all_ids = set()

        for rule in CASE_MATCHING_RULES.values():
            assert rule.rule_id not in all_ids, f"Duplicate rule ID: {rule.rule_id}"
            all_ids.add(rule.rule_id)

        # Transfer and attribute dicts are empty, but still verify they don't conflict
        for rule in TRANSFER_RULES.values():
            assert rule.rule_id not in all_ids, f"Duplicate rule ID: {rule.rule_id}"
            all_ids.add(rule.rule_id)

        for rule in ATTRIBUTE_RULES.values():
            assert rule.rule_id not in all_ids, f"Duplicate rule ID: {rule.rule_id}"
            all_ids.add(rule.rule_id)

    def test_odrl_properties(self):
        """Test ODRL properties are valid"""
        valid_types = ["Permission", "Prohibition"]
        valid_actions = ["transfer", "store", "process"]

        for rule in CASE_MATCHING_RULES.values():
            assert rule.odrl_type in valid_types
            assert rule.odrl_action in valid_actions

    def test_all_origin_groups_exist(self):
        """Test that origin groups referenced in rules exist in COUNTRY_GROUPS"""
        for key, rule in CASE_MATCHING_RULES.items():
            if rule.origin_group:
                assert rule.origin_group in COUNTRY_GROUPS, (
                    f"Rule {key} references non-existent origin group: {rule.origin_group}"
                )

    def test_all_receiving_groups_exist(self):
        """Test that receiving groups referenced in rules exist in COUNTRY_GROUPS"""
        for key, rule in CASE_MATCHING_RULES.items():
            if rule.receiving_group:
                assert rule.receiving_group in COUNTRY_GROUPS, (
                    f"Rule {key} references non-existent receiving group: {rule.receiving_group}"
                )

    def test_receiving_not_in_groups_exist(self):
        """Test that receiving_not_in groups exist"""
        for key, rule in CASE_MATCHING_RULES.items():
            if rule.receiving_not_in:
                for group in rule.receiving_not_in:
                    assert group in COUNTRY_GROUPS, (
                        f"Rule {key} excludes non-existent group: {group}"
                    )


class TestDataDictionaries:
    """Tests for the new data dictionary JSON files"""

    @pytest.fixture
    def dict_dir(self):
        return Path(__file__).parent.parent / "rules" / "data_dictionaries"

    def test_dictionaries_directory_exists(self, dict_dir):
        assert dict_dir.exists(), "data_dictionaries directory should exist"

    def test_all_dictionary_files_exist(self, dict_dir):
        for name in ["processes.json", "purposes.json", "data_subjects.json", "gdc.json"]:
            assert (dict_dir / name).exists(), f"{name} should exist"

    def test_processes_has_50_plus_entries(self, dict_dir):
        import json
        with open(dict_dir / "processes.json") as f:
            data = json.load(f)
        total = sum(len(cat["entries"]) for cat in data["categories"].values())
        assert total >= 50, f"processes.json should have 50+ entries, has {total}"

    def test_purposes_has_50_plus_entries(self, dict_dir):
        import json
        with open(dict_dir / "purposes.json") as f:
            data = json.load(f)
        total = sum(len(cat["entries"]) for cat in data["categories"].values())
        assert total >= 50, f"purposes.json should have 50+ entries, has {total}"

    def test_data_subjects_has_50_plus_entries(self, dict_dir):
        import json
        with open(dict_dir / "data_subjects.json") as f:
            data = json.load(f)
        total = sum(len(cat["entries"]) for cat in data["categories"].values())
        assert total >= 50, f"data_subjects.json should have 50+ entries, has {total}"

    def test_gdc_has_50_plus_entries(self, dict_dir):
        import json
        with open(dict_dir / "gdc.json") as f:
            data = json.load(f)
        total = sum(len(cat["entries"]) for cat in data["categories"].values())
        assert total >= 50, f"gdc.json should have 50+ entries, has {total}"

    def test_dictionary_structure(self, dict_dir):
        """All dictionaries should have name, categories with entries"""
        import json
        for name in ["processes.json", "purposes.json", "data_subjects.json", "gdc.json"]:
            with open(dict_dir / name) as f:
                data = json.load(f)
            assert "name" in data, f"{name} missing 'name'"
            assert "categories" in data, f"{name} missing 'categories'"
            for cat_name, cat_data in data["categories"].items():
                assert "entries" in cat_data, f"{name} category '{cat_name}' missing 'entries'"
                assert len(cat_data["entries"]) > 0, f"{name} category '{cat_name}' has no entries"

    def test_no_duplicate_entries_within_dictionary(self, dict_dir):
        """No duplicate entry names within a single dictionary"""
        import json
        for name in ["processes.json", "purposes.json", "data_subjects.json", "gdc.json"]:
            with open(dict_dir / name) as f:
                data = json.load(f)
            all_entries = []
            for cat_data in data["categories"].values():
                all_entries.extend(cat_data["entries"])
            assert len(all_entries) == len(set(all_entries)), f"{name} has duplicate entries"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
