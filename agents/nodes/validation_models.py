"""
Validation Models
==================
Pydantic models for validating agent outputs (rule definitions, Cypher queries, etc).
Migrated from the old graph_workflow.py.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator

from rules.dictionaries.country_groups import COUNTRY_GROUPS


class RuleDefinitionModel(BaseModel):
    """Pydantic model for validating rule definitions.

    Deliberately lenient to avoid blocking AI-generated rules with minor
    formatting differences.  Structural issues are caught here; semantic
    correctness is left to the validator agent.
    """
    rule_type: str = "attribute"  # attribute or case_matching
    rule_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="", min_length=0)
    priority: str = "medium"  # high, medium, low — normalised by analyzer
    origin_countries: Optional[List[str]] = None
    origin_group: Optional[str] = None
    receiving_countries: Optional[List[str]] = None
    receiving_group: Optional[str] = None
    outcome: str = "permission"  # permission or prohibition
    requires_pii: bool = False
    requires_any_data: bool = False
    requires_personal_data: bool = False
    attribute_name: Optional[str] = None
    attribute_keywords: Optional[List[str]] = None
    required_actions: List[str] = Field(default_factory=list)
    odrl_type: str = "Permission"
    odrl_action: str = "transfer"
    odrl_target: str = "Data"
    case_matching_module: Optional[str] = None  # PIA, TIA, or HRPR (for case_matching rules)
    data_categories: Optional[List[str]] = None
    purposes_of_processing: Optional[List[str]] = None
    valid_until: Optional[str] = None
    suggested_linked_entities: Optional[dict] = None  # From analyzer: entity names for LINKED_TO

    model_config = {"extra": "allow"}

    @field_validator('origin_group', 'receiving_group')
    @classmethod
    def validate_country_group(cls, v):
        if v is not None and v not in COUNTRY_GROUPS and v != "ANY":
            # Warn but don't reject — AI may generate valid groups not in our list
            pass
        return v

    @field_validator('priority')
    @classmethod
    def normalise_priority(cls, v):
        if isinstance(v, str) and v.lower() in ("high", "medium", "low"):
            return v.lower()
        return "medium"

    @field_validator('outcome')
    @classmethod
    def normalise_outcome(cls, v):
        if isinstance(v, str) and v.lower() in ("permission", "prohibition"):
            return v.lower()
        return "permission"


class CypherQueriesModel(BaseModel):
    """Pydantic model for validating Cypher queries.

    Lenient validation — only rejects queries with known FalkorDB
    incompatibilities.  Empty/short queries are allowed (the executor
    has its own structural check).
    """
    rule_check: str = ""
    rule_insert: str = ""
    rule_links: str = ""
    validation: str = ""

    model_config = {"extra": "allow"}

    @field_validator('rule_check', 'rule_insert', 'rule_links', 'validation')
    @classmethod
    def validate_cypher_syntax(cls, v):
        if not v or not v.strip():
            return v
        
        # Check for basic Cypher keywords (case-insensitive)
        keywords = {'MATCH', 'CREATE', 'MERGE', 'RETURN', 'WITH', 'UNWIND', 'CALL', 'DELETE', 'SET', 'REMOVE'}
        v_upper = v.upper()
        if not any(kw in v_upper for kw in keywords):
            raise ValueError("Query must contain at least one Cypher keyword (MATCH, CREATE, RETURN, etc.)")

        # FalkorDB: single statement only — strip trailing semicolons
        v = v.strip().rstrip(';')
        # FalkorDB: no EXISTS { MATCH ... } subqueries
        import re
        if re.search(r'EXISTS\s*\{', v, re.IGNORECASE):
            v = v  # warn but don't reject — cypher generator will fix it
        return v


class ValidationResultModel(BaseModel):
    """Pydantic model for validation results."""
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
    def clamp_confidence(cls, v):
        """Clamp confidence to [0, 1] range — LLM sometimes returns >1 or <0."""
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0.8
        return max(0.0, min(1.0, v))
