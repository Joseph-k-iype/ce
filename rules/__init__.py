"""Rules module - dictionaries and templates"""
from .dictionaries.country_groups import (
    COUNTRY_GROUPS,
    get_country_group,
    is_country_in_group,
    get_all_countries,
)
from .dictionaries.rules_definitions import (
    RuleType,
    RuleOutcome,
    AssessmentType,
    CaseMatchingRule,
    TransferRule,
    AttributeRule,
    CASE_MATCHING_RULES,
    TRANSFER_RULES,
    ATTRIBUTE_RULES,
    get_all_rules,
    get_enabled_case_matching_rules,
    get_enabled_transfer_rules,
    get_enabled_attribute_rules,
    get_rules_by_priority,
)
from .templates.cypher_templates import (
    CYPHER_TEMPLATES,
    build_query_from_template,
    get_template,
    list_templates,
    build_origin_filter,
    build_receiving_filter,
    build_purpose_filter,
    build_process_filter,
    build_pii_filter,
    build_assessment_filter,
)

__all__ = [
    # Country groups
    "COUNTRY_GROUPS",
    "get_country_group",
    "is_country_in_group",
    "get_all_countries",
    # Rule definitions
    "RuleType",
    "RuleOutcome",
    "AssessmentType",
    "CaseMatchingRule",
    "TransferRule",
    "AttributeRule",
    "CASE_MATCHING_RULES",
    "TRANSFER_RULES",
    "ATTRIBUTE_RULES",
    "get_all_rules",
    "get_enabled_case_matching_rules",
    "get_enabled_transfer_rules",
    "get_enabled_attribute_rules",
    "get_rules_by_priority",
    # Templates
    "CYPHER_TEMPLATES",
    "build_query_from_template",
    "get_template",
    "list_templates",
    "build_origin_filter",
    "build_receiving_filter",
    "build_purpose_filter",
    "build_process_filter",
    "build_pii_filter",
    "build_assessment_filter",
]
