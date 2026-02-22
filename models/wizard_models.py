"""
Wizard Models
=============
Pydantic models for the 6-step rule ingestion wizard.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum
from datetime import datetime


class WizardStep(str, Enum):
    """Wizard step identifiers (6-step flow)"""
    COUNTRY = "country"
    METADATA = "metadata"
    RULE = "rule"
    REVIEW = "review"
    SANDBOX_TEST = "sandbox_test"
    APPROVE = "approve"


class WizardSessionStatus(str, Enum):
    """Status of a wizard session"""
    ACTIVE = "active"
    PROCESSING = "processing"
    AWAITING_REVIEW = "awaiting_review"
    SANDBOX_LOADED = "sandbox_loaded"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    FAILED = "failed"
    SAVED = "saved"


class WizardStartRequest(BaseModel):
    """Request to start a new wizard session"""
    user_id: str = Field(default="anonymous", description="User starting the session")


class WizardStartResponse(BaseModel):
    """Response when a wizard session is created"""
    session_id: str
    status: WizardSessionStatus = WizardSessionStatus.ACTIVE
    current_step: int = 1
    created_at: str


class WizardStepSubmission(BaseModel):
    """Data submitted at each wizard step"""
    step: int = Field(..., ge=1, le=6, description="Step number (1-6)")
    data: Dict[str, Any] = Field(..., description="Step-specific data")


class WizardSessionState(BaseModel):
    """Full state of a wizard session"""
    session_id: str
    user_id: str = "anonymous"
    status: WizardSessionStatus = WizardSessionStatus.ACTIVE
    current_step: int = 1
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    agentic_mode: bool = False

    # Step 1: Country
    origin_country: Optional[str] = None
    receiving_countries: List[str] = Field(default_factory=list)
    origin_legal_entity: Optional[List[str]] = Field(default_factory=list)
    receiving_legal_entity: Optional[List[str]] = Field(default_factory=list)

    @field_validator('origin_legal_entity', 'receiving_legal_entity', mode='before')
    @classmethod
    def coerce_legal_entity_to_list(cls, v):
        """Handle backward compat: string -> list, None -> []."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        if isinstance(v, list):
            return v
        return []

    # Step 2: Metadata
    data_categories: List[str] = Field(default_factory=list)
    purposes_of_processing: List[str] = Field(default_factory=list)
    process_l1: List[str] = Field(default_factory=list)
    process_l2: List[str] = Field(default_factory=list)
    process_l3: List[str] = Field(default_factory=list)
    group_data_categories: List[str] = Field(default_factory=list)
    valid_until: Optional[str] = None

    # Step 3: Rule text input
    rule_text: Optional[str] = None
    is_pii_related: bool = False

    # AI-generated results (from step 3 processing)
    analysis_result: Optional[Dict[str, Any]] = None
    dictionary_result: Optional[Dict[str, Any]] = None
    proposal: Optional[Dict[str, Any]] = None

    # Step 4: Review (editable AI output)
    edited_rule_definition: Optional[Dict[str, Any]] = None
    edited_terms_dictionary: Optional[Dict[str, Any]] = None
    review_snapshot: Optional[Dict[str, Any]] = None

    # Step 5: Sandbox
    sandbox_graph_name: Optional[str] = None
    sandbox_test_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Step 6: Approval
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    # Error tracking
    error_message: Optional[str] = None

    # Saved state
    saved_session_id: Optional[str] = None


class WizardSessionResponse(BaseModel):
    """Response for getting wizard session state"""
    session_id: str
    status: WizardSessionStatus
    current_step: int
    agentic_mode: bool = False
    origin_country: Optional[str] = None
    receiving_countries: List[str] = Field(default_factory=list)
    origin_legal_entity: Optional[List[str]] = Field(default_factory=list)
    receiving_legal_entity: Optional[List[str]] = Field(default_factory=list)
    data_categories: List[str] = Field(default_factory=list)

    @field_validator('origin_legal_entity', 'receiving_legal_entity', mode='before')
    @classmethod
    def coerce_legal_entity_to_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        if isinstance(v, list):
            return v
        return []
    purposes_of_processing: List[str] = Field(default_factory=list)
    process_l1: List[str] = Field(default_factory=list)
    process_l2: List[str] = Field(default_factory=list)
    process_l3: List[str] = Field(default_factory=list)
    group_data_categories: List[str] = Field(default_factory=list)
    valid_until: Optional[str] = None
    rule_text: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None
    dictionary_result: Optional[Dict[str, Any]] = None
    proposal: Optional[Dict[str, Any]] = None
    edited_rule_definition: Optional[Dict[str, Any]] = None
    edited_terms_dictionary: Optional[Dict[str, Any]] = None
    sandbox_graph_name: Optional[str] = None
    sandbox_test_results: List[Dict[str, Any]] = Field(default_factory=list)
    approved: bool = False
    error_message: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class RuleEditRequest(BaseModel):
    """Request to edit a rule definition in step 4"""
    rule_definition: Dict[str, Any] = Field(..., description="Edited rule definition")


class TermsEditRequest(BaseModel):
    """Request to edit terms dictionary in step 4"""
    terms_dictionary: Dict[str, Any] = Field(..., description="Edited terms dictionary")


class SandboxEvaluationRequest(BaseModel):
    """Request to evaluate rules in the sandbox"""
    origin_country: str
    receiving_country: str
    pii: bool = False
    purposes: Optional[List[str]] = None
    data_categories: Optional[List[str]] = None
    process_l1: Optional[List[str]] = None
    process_l2: Optional[List[str]] = None
    process_l3: Optional[List[str]] = None
    personal_data_names: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    origin_legal_entity: Optional[List[str]] = None
    receiving_legal_entity: Optional[str] = None


class WizardApprovalRequest(BaseModel):
    """Request to approve the wizard output and load to main graph"""
    approved_by: str = Field(default="admin", description="Who is approving")
    notes: Optional[str] = None


class SavedSessionSummary(BaseModel):
    """Summary of a saved wizard session"""
    session_id: str
    user_id: str
    origin_country: Optional[str] = None
    receiving_countries: List[str] = Field(default_factory=list)
    rule_text: Optional[str] = None
    current_step: int = 1
    status: str = "saved"
    saved_at: str = ""
    updated_at: str = ""
