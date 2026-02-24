"""
Rule Specification Model
========================
Declarative rule specifications validated at ingestion time.
Rules are validated BEFORE they enter the graph, ensuring that
malformed rules are rejected early rather than causing evaluation errors.

This is the single source of truth for what constitutes a valid rule.
"""

from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


class RuleMatchingMode(str, Enum):
    """How multiple entity dimensions are combined during evaluation."""
    ALL_DIMENSIONS = "all_dimensions"  # AND — all dimensions must match
    ANY_DIMENSION = "any_dimension"    # OR — any dimension match triggers


class RuleOutcome(str, Enum):
    """What happens when a rule fires."""
    PERMISSION = "permission"
    PROHIBITION = "prohibition"


class RuleType(str, Enum):
    """Classification of rule behavior."""
    CASE_MATCHING = "case_matching"    # Country-pair only (TIA/PIA/HRPR)
    TRANSFER = "transfer"              # Transfer-specific rules
    ATTRIBUTE = "attribute"            # Entity/content-aware rules


class RuleSpec(BaseModel):
    """Declarative rule specification — validated at ingestion time.

    This model defines what a valid rule looks like. It is used to:
    1. Validate AI-generated rules before insertion into the graph
    2. Validate user-edited rules from the wizard
    3. Provide a single schema for rule structure documentation

    Entity dimensions (required_data_categories, required_regulators, etc.)
    use AND-across-dimensions matching by default: a rule linked to both
    DataCategory:HealthData AND Regulator:ICO only fires when BOTH are
    present in the evaluation context.
    """

    # ── Core identity ──────────────────────────────────────────────────
    rule_id: str = Field(description="Unique identifier for this rule")
    name: str = Field(min_length=1, description="Human-readable rule name")
    description: str = Field(default="", description="Explanation of the rule")
    rule_type: RuleType = Field(default=RuleType.CASE_MATCHING)
    outcome: RuleOutcome = Field(default=RuleOutcome.PERMISSION)
    priority: str = Field(default="medium")

    # ── Country matching ───────────────────────────────────────────────
    origin_match_type: Literal["any", "specific"] = "any"
    receiving_match_type: Literal["any", "specific", "not_in"] = "any"
    origin_countries: List[str] = Field(default_factory=list)
    receiving_countries: List[str] = Field(default_factory=list)

    # ── Entity dimension requirements ──────────────────────────────────
    # These define WHAT the rule applies to. Empty = not required.
    # Matching mode determines how dimensions are combined (default: AND).
    matching_mode: RuleMatchingMode = Field(
        default=RuleMatchingMode.ALL_DIMENSIONS,
        description="How multiple entity dimensions are combined"
    )
    required_data_categories: List[str] = Field(default_factory=list)
    required_purposes: List[str] = Field(default_factory=list)
    required_processes: List[str] = Field(default_factory=list)
    required_gdcs: List[str] = Field(default_factory=list)
    required_regulators: List[str] = Field(default_factory=list)
    required_authorities: List[str] = Field(default_factory=list)
    required_data_subjects: List[str] = Field(default_factory=list)
    required_sensitive_data_categories: List[str] = Field(default_factory=list)

    # ── Free-text matching (optional) ──────────────────────────────────
    keywords: List[str] = Field(
        default_factory=list,
        description="Keywords for free-text matching against personal_data_names/metadata"
    )
    patterns: List[str] = Field(
        default_factory=list,
        description="Regex patterns for free-text matching"
    )

    # ── PII / personal data requirements ───────────────────────────────
    requires_pii: bool = Field(default=False)
    requires_personal_data: bool = Field(default=False)

    # ── Duties and assessments ─────────────────────────────────────────
    required_assessments: List[str] = Field(
        default_factory=list,
        description="Required assessment modules: PIA, TIA, HRPR"
    )
    required_actions: List[str] = Field(default_factory=list)

    # ── Validity ───────────────────────────────────────────────────────
    valid_until: Optional[str] = Field(
        default=None,
        description="ISO date string. Rule disabled after this date."
    )

    @model_validator(mode='after')
    def validate_rule_consistency(self):
        """Validate rule spec consistency."""
        # Attribute rules should have at least one entity dimension or keyword
        if self.rule_type == RuleType.ATTRIBUTE:
            has_entities = any([
                self.required_data_categories,
                self.required_purposes,
                self.required_processes,
                self.required_gdcs,
                self.required_regulators,
                self.required_authorities,
                self.required_data_subjects,
                self.required_sensitive_data_categories,
            ])
            has_keywords = bool(self.keywords or self.patterns)
            if not has_entities and not has_keywords:
                raise ValueError(
                    "Attribute rules must specify at least one entity dimension "
                    "or keyword/pattern for matching"
                )

        # Country-specific matching needs country lists
        if self.origin_match_type == "specific" and not self.origin_countries:
            raise ValueError(
                "origin_match_type='specific' requires at least one origin country"
            )
        if self.receiving_match_type in ("specific", "not_in") and not self.receiving_countries:
            raise ValueError(
                f"receiving_match_type='{self.receiving_match_type}' requires "
                "at least one receiving country"
            )

        return self

    @property
    def has_entity_dimensions(self) -> bool:
        """Whether this rule specifies any entity dimension requirements."""
        return any([
            self.required_data_categories,
            self.required_purposes,
            self.required_processes,
            self.required_gdcs,
            self.required_regulators,
            self.required_authorities,
            self.required_data_subjects,
            self.required_sensitive_data_categories,
        ])

    @property
    def entity_dimension_count(self) -> int:
        """Number of entity dimensions specified."""
        return sum(1 for lst in [
            self.required_data_categories,
            self.required_purposes,
            self.required_processes,
            self.required_gdcs,
            self.required_regulators,
            self.required_authorities,
            self.required_data_subjects,
            self.required_sensitive_data_categories,
        ] if lst)
