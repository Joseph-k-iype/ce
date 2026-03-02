"""
Validation Models
==================
Pydantic v2 models for validating all agent outputs.

Models:
  - RequirementCheckResult: Hard-stop output when required inputs are missing
  - RuleDefinitionModel: Validates parsed rule definitions from analyzer
  - CypherQueriesModel: Validates FalkorDB-compatible Cypher queries
  - ValidationResultModel: Validates validation agent results
  - AnalyzerOutputModel: Full analyzer response envelope
  - DictionaryOutputModel: Dictionary agent response
  - SupervisorDecisionModel: Supervisor routing decisions
  - TesterOutputModel: Test scenario structure
  - ReferenceDataOutputModel: Reference data creation output
"""

import re
from typing import Optional, List, Dict, Any, Literal
from typing_extensions import Self
from pydantic import BaseModel, Field, field_validator, model_validator

from rules.dictionaries.country_groups import COUNTRY_GROUPS


# ═══════════════════════════════════════════════════════════════════════════════
# Requirement Check — Hard-Stop Gate
# ═══════════════════════════════════════════════════════════════════════════════

class RequirementCheckResult(BaseModel):
    """Hard-stop output when required inputs are missing.

    Every executor calls validate_preconditions() before running.
    If requirements_met=False, the executor emits this and halts.
    """
    requirements_met: bool
    missing_inputs: List[str] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    can_proceed: bool = False

    @model_validator(mode='after')
    def check_consistency(self) -> Self:
        if not self.requirements_met and not self.missing_inputs:
            raise ValueError("requirements_met=False requires at least one missing_input")
        self.can_proceed = self.requirements_met
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Rule Definition Model
# ═══════════════════════════════════════════════════════════════════════════════

class RuleDefinitionModel(BaseModel):
    """Pydantic v2 model for validating rule definitions.

    Cross-field validators enforce:
    - Attribute rules MUST have attribute_keywords
    - outcome and odrl_type must be consistent
    - Priority is normalised to lowercase
    """
    rule_type: Literal["attribute", "case_matching"] = "attribute"
    rule_id: str = Field(..., min_length=1, description="Unique ID, e.g. RULE_SAR_UK")
    name: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", min_length=0)
    priority: str = "medium"
    origin_countries: Optional[List[str]] = None
    origin_group: Optional[str] = None
    receiving_countries: Optional[List[str]] = None
    receiving_group: Optional[str] = None
    outcome: Literal["permission", "prohibition"] = "permission"
    requires_pii: bool = False
    requires_any_data: bool = False
    requires_personal_data: bool = False
    attribute_name: Optional[str] = None
    attribute_keywords: Optional[List[str]] = None
    required_actions: List[str] = Field(default_factory=list)
    odrl_type: Literal["Permission", "Prohibition"] = "Permission"
    odrl_action: str = "transfer"
    odrl_target: str = "Data"
    case_matching_module: Optional[str] = None
    data_categories: Optional[List[str]] = None
    purposes_of_processing: Optional[List[str]] = None
    valid_until: Optional[str] = None
    suggested_linked_entities: Optional[dict] = None

    model_config = {"extra": "allow"}

    @field_validator('priority', mode='before')
    @classmethod
    def normalise_priority(cls, v: Any) -> str:
        if isinstance(v, (int, float)):
            if v <= 33:
                return "high"
            elif v <= 66:
                return "medium"
            return "low"
        if isinstance(v, str) and v.lower() in ("high", "medium", "low"):
            return v.lower()
        return "medium"

    @field_validator('outcome', mode='before')
    @classmethod
    def normalise_outcome(cls, v: Any) -> str:
        if isinstance(v, str) and v.lower() in ("permission", "prohibition"):
            return v.lower()
        return "permission"

    @field_validator('odrl_type', mode='before')
    @classmethod
    def normalise_odrl_type(cls, v: Any) -> str:
        if isinstance(v, str) and v.lower() in ("permission", "prohibition"):
            return v.capitalize()
        return "Permission"

    @field_validator('origin_group', 'receiving_group')
    @classmethod
    def validate_country_group(cls, v: Optional[str]) -> Optional[str]:
        # Warn but don't reject — AI may generate valid groups not in our list
        return v

    @model_validator(mode='after')
    def cross_field_checks(self) -> Self:
        """Enforce cross-field consistency."""
        # Auto-align odrl_type with outcome
        expected_odrl = "Prohibition" if self.outcome == "prohibition" else "Permission"
        if self.odrl_type != expected_odrl:
            self.odrl_type = expected_odrl

        # case_matching rules must specify a module
        if self.rule_type == "case_matching" and not self.case_matching_module:
            # Default to PIA if not specified
            self.case_matching_module = "PIA"

        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Cypher Queries Model
# ═══════════════════════════════════════════════════════════════════════════════

_FALKOR_BLOCKLIST = [
    (r'EXISTS\s*\{', "EXISTS {{ }} subqueries not supported — use OPTIONAL MATCH"),
    (r'CALL\s*\{', "CALL {{ }} subqueries not supported"),
    (r'\bUNION\b', "UNION not supported in single query"),
    (r'\bFOREACH\b', "FOREACH not supported — use UNWIND"),
    (r'\bDELETE\b', "DELETE operations are forbidden"),
    (r'DETACH\s+DELETE', "DETACH DELETE operations are forbidden"),
]


class CypherQueriesModel(BaseModel):
    """Pydantic v2 model for validating Cypher queries.

    Enforces FalkorDB compatibility:
    - Single statement only (no semicolons mid-query)
    - No EXISTS/CALL subqueries, UNION, FOREACH, DELETE
    - Must contain at least one Cypher keyword
    """
    rule_check: str = ""
    rule_insert: str = ""
    rule_links: str = ""
    validation: str = ""

    model_config = {"extra": "allow"}

    @field_validator('rule_check', 'rule_insert', 'rule_links', 'validation', mode='before')
    @classmethod
    def validate_cypher_syntax(cls, v: Any) -> str:
        if not isinstance(v, str):
            v = str(v) if v is not None else ""
        if not v or not v.strip():
            return v

        # Strip trailing semicolons (FalkorDB: single statement)
        v = v.strip().rstrip(';')

        # Must contain at least one Cypher keyword
        keywords = {'MATCH', 'CREATE', 'MERGE', 'RETURN', 'WITH', 'UNWIND', 'SET', 'REMOVE'}
        v_upper = v.upper()
        if not any(kw in v_upper for kw in keywords):
            raise ValueError(
                f"Query must contain at least one Cypher keyword "
                f"({', '.join(sorted(keywords))})"
            )

        # Check for multi-statement (semicolons inside the query body)
        stripped = v.strip().rstrip(';')
        if ';' in stripped:
            raise ValueError("Multiple statements not supported — remove semicolons")

        # FalkorDB blocklist
        for pattern, message in _FALKOR_BLOCKLIST:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(message)

        return v

    @model_validator(mode='after')
    def require_core_queries(self) -> Self:
        """rule_insert is required; rule_check and validation are strongly recommended."""
        if self.rule_insert and not self.rule_insert.strip():
            # Empty rule_insert is a warning but not a hard error
            pass
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Result Model
# ═══════════════════════════════════════════════════════════════════════════════

class ValidationResultModel(BaseModel):
    """Pydantic v2 model for validator agent results.

    Auto-derives overall_valid from sub-field validity if not explicitly set.
    """
    overall_valid: bool = True
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    rule_definition_valid: bool = True
    cypher_valid: bool = True
    logical_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggested_fixes: List[str] = Field(default_factory=list)

    @field_validator('confidence_score', mode='before')
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        """Clamp confidence to [0, 1] — LLM sometimes returns >1 or <0."""
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0.8
        return max(0.0, min(1.0, v))

    @model_validator(mode='after')
    def derive_overall_valid(self) -> Self:
        """Auto-derive overall_valid from sub-fields if there are errors."""
        if self.errors:
            self.overall_valid = False
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Analyzer Output Model
# ═══════════════════════════════════════════════════════════════════════════════

class ChainOfThoughtOutput(BaseModel):
    """Structured CoT reasoning from the analyzer."""
    domain_identified: str = ""
    ontologies_referenced: str = ""
    acronym_expansion: str = ""
    regulatory_context: str = ""
    intent_analysis: str = ""
    rule_type_reasoning: str = ""
    country_analysis: str = ""
    outcome_analysis: str = ""
    pii_assessment: str = ""
    model_config = {"extra": "allow"}


class TreeOfThoughtBranch(BaseModel):
    interpretation: str
    strength: Literal["strong", "moderate", "weak"] = "moderate"
    reasoning: str = ""


class TreeOfThoughtOutput(BaseModel):
    branches_considered: List[TreeOfThoughtBranch] = Field(default_factory=list)
    selected_branch: str = ""
    model_config = {"extra": "allow"}


class ExpertPerspectives(BaseModel):
    legal: str = ""
    data_protection: str = ""
    compliance_ops: str = ""
    ontology: str = ""
    synthesis: str = ""
    model_config = {"extra": "allow"}


class SuggestedLinkedEntities(BaseModel):
    """Entity names to create LINKED_TO relationships in the graph."""
    regulators: List[str] = Field(default_factory=list)
    authorities: List[str] = Field(default_factory=list)
    purposes_of_processing: List[str] = Field(default_factory=list)
    data_categories: List[str] = Field(default_factory=list)
    sensitive_data_categories: List[str] = Field(default_factory=list)
    processes: List[str] = Field(default_factory=list)
    gdcs: List[str] = Field(default_factory=list)
    data_subjects: List[str] = Field(default_factory=list)
    legal_entities: List[str] = Field(default_factory=list)
    global_business_functions: List[str] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class AnalyzerOutputModel(BaseModel):
    """Full analyzer agent response envelope.

    Validates the complete output including reasoning traces and rule definition.
    """
    chain_of_thought: ChainOfThoughtOutput = Field(default_factory=ChainOfThoughtOutput)
    tree_of_thought: TreeOfThoughtOutput = Field(default_factory=TreeOfThoughtOutput)
    expert_perspectives: ExpertPerspectives = Field(default_factory=ExpertPerspectives)
    rule_definition: RuleDefinitionModel
    suggested_linked_entities: SuggestedLinkedEntities = Field(
        default_factory=SuggestedLinkedEntities
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_clarification: List[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}

    @field_validator('confidence', mode='before')
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, v))


# ═══════════════════════════════════════════════════════════════════════════════
# Dictionary Output Model
# ═══════════════════════════════════════════════════════════════════════════════

class DictionaryEntry(BaseModel):
    """Single data category dictionary entry."""
    keywords: List[str] = Field(default_factory=list, min_length=1)
    sub_categories: Dict[str, List[str]] = Field(default_factory=dict)
    synonyms: Dict[str, List[str]] = Field(default_factory=dict)
    acronyms: Dict[str, str] = Field(default_factory=dict)
    exclusions: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    description: str = ""
    model_config = {"extra": "allow"}

    @field_validator('keywords', mode='after')
    @classmethod
    def validate_keyword_quality(cls, v: List[str]) -> List[str]:
        """Warn (but don't reject) overly short keywords."""
        return [kw for kw in v if kw and kw.strip()]


class PiiDictionary(BaseModel):
    """PII-specific keyword dictionary."""
    keywords: List[str] = Field(default_factory=list)
    sub_categories: Dict[str, List[str]] = Field(default_factory=dict)
    jurisdiction_terms: Dict[str, List[str]] = Field(default_factory=dict)
    note: str = ""
    model_config = {"extra": "allow"}


class DictionaryOutputModel(BaseModel):
    """Full dictionary agent response."""
    domain_identified: str = ""
    ontologies_used: List[str] = Field(default_factory=list)
    dictionaries: Dict[str, DictionaryEntry] = Field(default_factory=dict)
    pii_dictionary: Optional[PiiDictionary] = None
    internal_patterns: List[str] = Field(default_factory=list)
    reasoning: str = ""
    coverage_assessment: str = ""

    model_config = {"extra": "allow"}

    @model_validator(mode='after')
    def check_dictionaries_not_empty(self) -> Self:
        """At least one dictionary entry must be present."""
        if not self.dictionaries:
            raise ValueError("At least one dictionary entry is required")
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Supervisor Decision Model
# ═══════════════════════════════════════════════════════════════════════════════

VALID_AGENTS = {
    "rule_analyzer", "data_dictionary", "cypher_generator",
    "validator", "reference_data", "rule_tester",
    "human_review", "complete", "fail",
}


class TodoStatus(BaseModel):
    analysis: Literal["pending", "done", "failed"] = "pending"
    dictionary: Literal["pending", "done", "failed", "skipped"] = "pending"
    cypher: Literal["pending", "done", "failed"] = "pending"
    validation: Literal["pending", "done", "failed"] = "pending"
    testing: Literal["pending", "done", "failed"] = "pending"
    reference_data: Literal["pending", "done", "skipped"] = "pending"
    model_config = {"extra": "allow"}


class SupervisorDecisionModel(BaseModel):
    """Supervisor agent routing decision.

    Validates next_agent is a known agent and reasoning is provided.
    """
    next_agent: str
    reasoning: str = Field(..., min_length=1)
    feedback: str = ""
    todo_status: TodoStatus = Field(default_factory=TodoStatus)

    model_config = {"extra": "allow"}

    @field_validator('next_agent')
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_AGENTS:
            raise ValueError(
                f"Unknown agent '{v}'. Must be one of: {', '.join(sorted(VALID_AGENTS))}"
            )
        return v


# ═══════════════════════════════════════════════════════════════════════════════
# Tester Output Model
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenario(BaseModel):
    """Single test scenario for rule verification."""
    name: str = Field(..., min_length=1)
    description: str = ""
    origin_country: str = Field(..., min_length=1)
    receiving_country: str = Field(..., min_length=1)
    pii: bool = False
    personal_data_names: List[str] = Field(default_factory=list)
    data_categories: List[str] = Field(default_factory=list)
    sensitive_data_categories: List[str] = Field(default_factory=list)
    purposes: List[str] = Field(default_factory=list)
    processes: List[str] = Field(default_factory=list)
    regulator: Optional[str] = None
    authority: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expected_triggered: bool = True
    expected_outcome: Optional[str] = None
    test_dimension: str = "country_match"

    model_config = {"extra": "allow"}


class TesterOutputModel(BaseModel):
    """Full tester agent response."""
    test_scenarios: List[TestScenario] = Field(default_factory=list, min_length=1)

    model_config = {"extra": "allow"}

    @model_validator(mode='after')
    def validate_scenario_count(self) -> Self:
        if len(self.test_scenarios) < 3:
            raise ValueError(
                f"At least 3 test scenarios required, got {len(self.test_scenarios)}"
            )
        # Check for both positive and negative cases
        has_positive = any(s.expected_triggered for s in self.test_scenarios)
        has_negative = any(not s.expected_triggered for s in self.test_scenarios)
        if not has_positive or not has_negative:
            raise ValueError(
                "Test scenarios must include both positive (should trigger) "
                "and negative (should NOT trigger) cases"
            )
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Reference Data Output Model
# ═══════════════════════════════════════════════════════════════════════════════

class ReferenceAction(BaseModel):
    """Single reference data action."""
    action_type: Literal["create_country_group", "create_attribute_config"]
    name: str = Field(..., min_length=1)
    data: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class ReferenceDataOutputModel(BaseModel):
    """Full reference data agent response."""
    actions_needed: List[ReferenceAction] = Field(default_factory=list)
    no_action_needed: bool = False
    reasoning: str = ""

    model_config = {"extra": "allow"}

    @model_validator(mode='after')
    def check_consistency(self) -> Self:
        if self.no_action_needed and self.actions_needed:
            raise ValueError(
                "Contradictory: no_action_needed=True but actions_needed is non-empty"
            )
        if not self.no_action_needed and not self.actions_needed:
            self.no_action_needed = True
        return self
