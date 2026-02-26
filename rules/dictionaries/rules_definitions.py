"""
Rules Definitions Dictionary
=============================
This file contains two sets of rules:

SET 1: Case-Matching Rules
--------------------------
These rules require finding at least one historical case that matches the given
parameters. If a perfect match is found with completed assessments, transfer is ALLOWED.

SET 2: Generic Country-Specific Rules
-------------------------------------
Category A: Transfer Rules - Country to country transfer permissions/prohibitions
Category B: Attribute Rules - Attribute-level restrictions (e.g., health data)

Developers can add/modify rules here without changing core logic.
"""

from typing import Dict, List, Optional, Set, Tuple, Any, FrozenSet
from dataclasses import dataclass, field
from enum import Enum
from rules.dictionaries.country_groups import (
    EU_EEA_UK_CROWN_CH,
    EU_EEA_COUNTRIES,
    ADEQUACY_COUNTRIES,
    ADEQUACY_PLUS_EU,
    CROWN_DEPENDENCIES,
    SWITZERLAND_APPROVED,
    EU_EEA_ADEQUACY_UK,
    BCR_COUNTRIES
)


class RuleType(Enum):
    """Type of rule"""
    CASE_MATCHING = "case_matching"  # SET 1: Requires case matching
    TRANSFER = "transfer"            # SET 2A: Transfer rules
    ATTRIBUTE = "attribute"          # SET 2B: Attribute-level rules


class RuleOutcome(Enum):
    """Outcome if rule conditions are met"""
    PERMISSION = "permission"
    PROHIBITION = "prohibition"


class RulePriority(str, Enum):
    """Three-tier priority system. HIGH = evaluated first, LOW = evaluated last."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Sort order for priority: lower value = evaluated first
PRIORITY_ORDER = {
    RulePriority.HIGH: 1,
    RulePriority.MEDIUM: 2,
    RulePriority.LOW: 3,
    "high": 1,
    "medium": 2,
    "low": 3,
}


class AssessmentType(Enum):
    """Types of assessments that can be required"""
    PIA = "pia"       # Privacy Impact Assessment
    TIA = "tia"       # Transfer Impact Assessment
    HRPR = "hrpr"     # High Risk Processing Review


@dataclass
class RequiredAssessments:
    """Assessment requirements for a rule"""
    pia_required: bool = False
    tia_required: bool = False
    hrpr_required: bool = False

    def to_list(self) -> List[str]:
        """Return list of required assessment names"""
        assessments = []
        if self.pia_required:
            assessments.append("PIA")
        if self.tia_required:
            assessments.append("TIA")
        if self.hrpr_required:
            assessments.append("HRPR")
        return assessments


@dataclass
class CaseMatchingRule:
    """
    SET 1: Case-Matching Rule Definition

    These rules search for historical cases that match the parameters.
    If at least one case matches with completed assessments, transfer is ALLOWED.
    """
    rule_id: str
    name: str
    description: str
    priority: str  # "high", "medium", "low"

    # Country matching
    origin_countries: Optional[FrozenSet[str]] = None  # None = any country
    origin_group: Optional[str] = None  # Reference to COUNTRY_GROUPS key
    receiving_countries: Optional[FrozenSet[str]] = None  # None = any country
    receiving_group: Optional[str] = None
    receiving_not_in: Optional[FrozenSet[str]] = None  # Exclude these countries

    # Assessment requirements
    required_assessments: RequiredAssessments = field(default_factory=RequiredAssessments)

    # PII condition
    requires_pii: bool = False
    requires_personal_data: bool = False  # PersonalDataNames is not None

    # Rule status
    enabled: bool = True

    # ODRL properties
    odrl_type: str = "Permission"
    odrl_action: str = "transfer"
    odrl_target: str = "Data"


@dataclass
class TransferRule:
    """
    SET 2A: Transfer Rule Definition

    Country-to-country transfer permissions/prohibitions.
    These rules define whether data transfer between specific countries is allowed.
    """
    rule_id: str
    name: str
    description: str
    priority: str  # "high", "medium", "low"

    # Transfer specification (can use tuples or groups)
    # Format: List of (origin, receiving) tuples
    transfer_pairs: List[Tuple[str, str]] = field(default_factory=list)

    # Or use country groups
    origin_group: Optional[str] = None
    receiving_group: Optional[str] = None
    receiving_countries: Optional[FrozenSet[str]] = None  # Specific receiving countries
    bidirectional: bool = False  # If True, applies both ways

    # Outcome
    outcome: RuleOutcome = RuleOutcome.PERMISSION

    # Conditions
    requires_pii: bool = False
    requires_any_data: bool = False  # True = applies to all data

    # Actions/Duties (if permission, these are duties to fulfill)
    required_actions: List[str] = field(default_factory=list)

    # Rule status
    enabled: bool = True

    # ODRL properties
    odrl_type: str = "Permission"
    odrl_action: str = "transfer"
    odrl_target: str = "Data"


@dataclass
class AttributeRule:
    """
    SET 2B: Attribute-Level Rule Definition

    Rules that apply based on specific data attributes (e.g., health data).
    These rules check for specific metadata/attribute matches.
    """
    rule_id: str
    name: str
    description: str
    priority: str  # "high", "medium", "low"

    # Attribute specification
    attribute_name: str  # e.g., "health_data", "financial_data"
    attribute_keywords: List[str] = field(default_factory=list)
    attribute_patterns: List[str] = field(default_factory=list)  # Regex patterns

    # Link to attribute config file (for complex detection)
    attribute_config_file: Optional[str] = None

    # Country restrictions
    origin_countries: Optional[FrozenSet[str]] = None
    origin_group: Optional[str] = None
    receiving_countries: Optional[FrozenSet[str]] = None
    receiving_group: Optional[str] = None

    # Outcome
    outcome: RuleOutcome = RuleOutcome.PROHIBITION

    # Additional conditions
    requires_pii: bool = False

    # Rule status
    enabled: bool = True

    # ODRL properties
    odrl_type: str = "Prohibition"
    odrl_action: str = "transfer"
    odrl_target: str = "Data"


# =============================================================================
# SET 1: CASE-MATCHING RULES
# =============================================================================
# These rules require finding historical cases that match parameters.

CASE_MATCHING_RULES: Dict[str, CaseMatchingRule] = {
    # Rule 1: EU/EEA/UK/Crown/Switzerland Internal Transfers
    "RULE_1_EU_INTERNAL": CaseMatchingRule(
        rule_id="RULE_1",
        name="EU/EEA/UK/Crown/Switzerland Internal Transfers",
        description="Transfers within EU/EEA, UK, Crown Dependencies, and Switzerland require PIA completion",
        priority="low",
        origin_countries=EU_EEA_UK_CROWN_CH,
        receiving_countries=EU_EEA_UK_CROWN_CH,
        required_assessments=RequiredAssessments(pia_required=True),
    ),

    # Rule 2: EU/EEA to Adequacy Countries
    "RULE_2_EU_ADEQUACY": CaseMatchingRule(
        rule_id="RULE_2",
        name="EU/EEA to Adequacy Countries",
        description="Transfers from EU/EEA to adequacy countries require PIA completion",
        priority="low",
        origin_countries=EU_EEA_COUNTRIES,
        receiving_countries=ADEQUACY_COUNTRIES,
        required_assessments=RequiredAssessments(pia_required=True),
    ),

    # Rule 3: Crown Dependencies to Adequacy + EU/EEA
    "RULE_3_CROWN_ADEQUACY": CaseMatchingRule(
        rule_id="RULE_3",
        name="Crown Dependencies to Adequacy + EU/EEA",
        description="Transfers from Crown Dependencies to adequacy countries or EU/EEA require PIA",
        priority="low",
        origin_countries=CROWN_DEPENDENCIES,
        receiving_countries=ADEQUACY_PLUS_EU,
        required_assessments=RequiredAssessments(pia_required=True),
    ),

    # Rule 4: UK to Adequacy + EU/EEA
    "RULE_4_UK_ADEQUACY": CaseMatchingRule(
        rule_id="RULE_4",
        name="UK to Adequacy + EU/EEA",
        description="Transfers from UK to adequacy countries or EU/EEA require PIA",
        priority="low",
        origin_countries=frozenset({"United Kingdom"}),
        receiving_countries=ADEQUACY_PLUS_EU,
        required_assessments=RequiredAssessments(pia_required=True),
    ),

    # Rule 5: Switzerland to Approved Countries
    "RULE_5_SWITZERLAND": CaseMatchingRule(
        rule_id="RULE_5",
        name="Switzerland to Approved Countries",
        description="Transfers from Switzerland to approved jurisdictions require PIA",
        priority="low",
        origin_countries=frozenset({"Switzerland"}),
        receiving_countries=SWITZERLAND_APPROVED,
        required_assessments=RequiredAssessments(pia_required=True),
    ),

    # Rule 6: EU/EEA/Adequacy/UK to Rest of World
    "RULE_6_REST_OF_WORLD": CaseMatchingRule(
        rule_id="RULE_6",
        name="EU/EEA/Adequacy/UK to Rest of World",
        description="Transfers to non-adequacy countries require PIA and TIA",
        priority="low",
        origin_countries=EU_EEA_ADEQUACY_UK,
        receiving_not_in=EU_EEA_ADEQUACY_UK,  # explicit frozenset marker
        required_assessments=RequiredAssessments(pia_required=True, tia_required=True),
    ),

    # Rule 7: BCR Countries to Any
    "RULE_7_BCR": CaseMatchingRule(
        rule_id="RULE_7",
        name="BCR Countries Transfer",
        description="Transfers from BCR countries require PIA and HRPR",
        priority="low",
        origin_countries=BCR_COUNTRIES,
        receiving_countries=None,  # Any country
        required_assessments=RequiredAssessments(pia_required=True, hrpr_required=True),
    ),

    # Rule 8: Any transfer with Personal Data
    "RULE_8_PERSONAL_DATA": CaseMatchingRule(
        rule_id="RULE_8",
        name="Personal Data Transfer",
        description="Any transfer with personal data requires PIA",
        priority="low",
        origin_countries=None,  # Any
        receiving_countries=None,  # Any
        requires_personal_data=True,
        required_assessments=RequiredAssessments(pia_required=True),
    ),
}


# =============================================================================
# SET 2A: TRANSFER RULES
# =============================================================================
# Country-to-country transfer permissions/prohibitions

TRANSFER_RULES: Dict[str, TransferRule] = {}


# =============================================================================
# SET 2B: ATTRIBUTE RULES
# =============================================================================
# Attribute-level rules based on data characteristics

ATTRIBUTE_RULES: Dict[str, AttributeRule] = {}


# =============================================================================
# STANDARD ACTIONS AND DUTIES LISTS
# =============================================================================

# Actions (system-level tasks performed automatically or by the system)
STANDARD_ACTIONS = [
    "Anonymisation",
    "Enhanced Technical and Organisational Security Measures",
    "Public Availability",
    "Services Agreement",
    "Storage Limitation",
    "Outsourcing Agreement",
]

# Duties (user-level obligations requiring human action)
STANDARD_DUTIES = [
    "Consent",
    "Consult/Approve Legal",
    "Consult/Approve Risk and Compliance",
    "Notification to Regulator",
    "Local Authority/Regulatory Approval",
    "Explicit Consent",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_all_rules() -> Dict[str, Any]:
    """Get all rules organized by type"""
    return {
        "case_matching": CASE_MATCHING_RULES,
        "transfer": TRANSFER_RULES,
        "attribute": ATTRIBUTE_RULES,
    }


def get_enabled_case_matching_rules() -> Dict[str, CaseMatchingRule]:
    """Get only enabled case-matching rules"""
    return {k: v for k, v in CASE_MATCHING_RULES.items() if v.enabled}


def get_enabled_transfer_rules() -> Dict[str, TransferRule]:
    """Get only enabled transfer rules"""
    return {k: v for k, v in TRANSFER_RULES.items() if v.enabled}


def get_enabled_attribute_rules() -> Dict[str, AttributeRule]:
    """Get only enabled attribute rules"""
    return {k: v for k, v in ATTRIBUTE_RULES.items() if v.enabled}


def get_rules_by_priority() -> List[Tuple[str, Any]]:
    """Get all enabled rules sorted by priority (ascending)"""
    all_rules = []

    for rule_id, rule in get_enabled_case_matching_rules().items():
        all_rules.append((rule_id, rule, RuleType.CASE_MATCHING))

    for rule_id, rule in get_enabled_transfer_rules().items():
        all_rules.append((rule_id, rule, RuleType.TRANSFER))

    for rule_id, rule in get_enabled_attribute_rules().items():
        all_rules.append((rule_id, rule, RuleType.ATTRIBUTE))

    # Sort by priority (high first, then medium, then low)
    return sorted(all_rules, key=lambda x: PRIORITY_ORDER.get(x[1].priority, 2))
