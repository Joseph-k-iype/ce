"""
Pydantic Models for the Compliance Engine API
=============================================
Request and Response models for all API endpoints.
Pydantic v2 compatible.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import datetime


# =============================================================================
# ENUMS
# =============================================================================

class TransferStatus(str, Enum):
    """Transfer evaluation outcome"""
    ALLOWED = "ALLOWED"
    PROHIBITED = "PROHIBITED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class RuleOutcomeType(str, Enum):
    """Type of rule outcome"""
    PERMISSION = "permission"
    PROHIBITION = "prohibition"


class AssessmentStatus(str, Enum):
    """Status of an assessment"""
    COMPLETED = "Completed"
    IN_PROGRESS = "In Progress"
    NOT_STARTED = "Not Started"
    NOT_APPLICABLE = "N/A"


# =============================================================================
# REQUEST MODELS
# =============================================================================

def parse_csv_field(value: Any) -> List[str]:
    """Parse a comma-separated string or list into a list of trimmed strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(value).strip()] if str(value).strip() else []


class RulesEvaluationRequest(BaseModel):
    """Request model for evaluating transfer rules.
    Only origin_country is required. All other fields are optional.
    String fields can be comma-separated for multiple values.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_country": "United Kingdom",
                "receiving_country": "India",
                "pii": True,
                "purpose_of_processing": "Risk Management, Fraud Detection",
                "processes": "Anti-Money Laundering",
            }
        }
    )

    origin_country: str = Field(..., description="Country where data originates (REQUIRED)")
    receiving_country: Any = Field(default="", description="Country/countries receiving the data (string, CSV, or list)")
    pii: bool = Field(default=False, description="Whether the transfer involves PII")

    # New simplified fields (comma-separated strings or lists)
    purpose_of_processing: Any = Field(default="", description="Purposes of processing (comma-separated or list)")
    data_categories: Any = Field(default="", description="Data categories (comma-separated or list)")
    sensitive_data_categories: Any = Field(default="", description="Sensitive data categories (comma-separated or list)")
    processes: Any = Field(default="", description="Processes (comma-separated or list)")
    gbgf: Any = Field(default="", description="Global business functions (comma-separated or list)")
    gdc: Any = Field(default="", description="Group data categories (comma-separated or list)")
    data_subjects: Any = Field(default="", description="Data subjects (comma-separated or list)")
    regulator: Any = Field(default="", description="Regulators (comma-separated or list)")
    authority: Any = Field(default="", description="Authorities (comma-separated or list)")
    legal_entities: Any = Field(default="", description="Legal entities (comma-separated or list)")
    personal_data_names: Any = Field(default=None, description="Types of personal data (comma-separated, list, or None)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata for attribute detection")

    # Legacy fields (backward compatibility)
    purposes: Optional[List[str]] = Field(default=None, description="Processing purposes (legacy)")
    process_l1: Optional[List[str]] = Field(default=None, description="Level 1 processes (legacy)")
    process_l2: Optional[List[str]] = Field(default=None, description="Level 2 processes (legacy)")
    process_l3: Optional[List[str]] = Field(default=None, description="Level 3 processes (legacy)")
    use_ai: bool = Field(default=False, description="Whether to use AI for rule interpretation")
    origin_legal_entity: Optional[str] = Field(default=None, description="Legal entity in the origin country")
    receiving_legal_entity: Optional[List[str]] = Field(default=None, description="Legal entities in receiving countries")

    def get_receiving_countries(self) -> List[str]:
        """Normalize receiving_country to a list."""
        return parse_csv_field(self.receiving_country)

    def get_purposes(self) -> List[str]:
        """Get purposes from new or legacy field."""
        result = parse_csv_field(self.purpose_of_processing)
        if not result and self.purposes:
            result = self.purposes
        return result

    def get_processes(self) -> List[str]:
        """Get processes from new or legacy field."""
        result = parse_csv_field(self.processes)
        if not result:
            # Combine all legacy process levels
            for field in [self.process_l1, self.process_l2, self.process_l3]:
                if field:
                    result.extend(field)
        return result

    def get_data_categories(self) -> List[str]:
        return parse_csv_field(self.data_categories)

    def get_personal_data_names(self) -> List[str]:
        return parse_csv_field(self.personal_data_names)

    def get_data_subjects(self) -> List[str]:
        return parse_csv_field(self.data_subjects)

    def get_gdc(self) -> List[str]:
        return parse_csv_field(self.gdc)

    def get_regulators(self) -> List[str]:
        return parse_csv_field(self.regulator)

    def get_authorities(self) -> List[str]:
        return parse_csv_field(self.authority)


class SearchCasesRequest(BaseModel):
    """Request model for searching historical cases"""
    origin_country: Optional[str] = Field(default=None, description="Filter by origin country")
    receiving_country: Optional[str] = Field(default=None, description="Filter by receiving country")
    purposes: Optional[List[str]] = Field(default=None, description="Filter by purposes")
    process_l1: Optional[List[str]] = Field(default=None, description="Filter by L1 processes")
    process_l2: Optional[List[str]] = Field(default=None, description="Filter by L2 processes")
    process_l3: Optional[List[str]] = Field(default=None, description="Filter by L3 processes")
    pii: Optional[bool] = Field(default=None, description="Filter by PII flag")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Results offset for pagination")


class AIRuleGenerationRequest(BaseModel):
    """Request model for AI-powered rule generation"""
    rule_text: str = Field(..., description="Natural language description of the rule")
    rule_country: str = Field(..., description="Primary country the rule relates to")
    rule_type: Optional[str] = Field(default=None, description="Hint: 'transfer' or 'attribute'")
    test_in_temp_graph: bool = Field(default=True, description="Whether to test in temporary graph first")
    agentic_mode: bool = Field(default=False, description="Enable agentic mode for autonomous reference data creation")


class AgentApprovalRequest(BaseModel):
    """Request to approve or reject an agent action"""
    entry_id: str = Field(..., description="The entry ID to approve/reject")
    action: str = Field(..., description="'approve' or 'reject'")
    reason: Optional[str] = Field(default=None, description="Reason for rejection")
    approved_by: str = Field(default="admin", description="Who is approving")


# =============================================================================
# RESPONSE MODELS - Components
# =============================================================================

class DutyInfo(BaseModel):
    """Information about a duty/obligation"""
    duty_id: str
    name: str
    module: str = ""
    value: str = ""
    description: Optional[str] = None


class PermissionInfo(BaseModel):
    """Information about a permission"""
    permission_id: str
    name: str
    description: Optional[str] = None
    duties: List[DutyInfo] = Field(default_factory=list)


class ProhibitionInfo(BaseModel):
    """Information about a prohibition"""
    prohibition_id: str
    name: str
    description: Optional[str] = None


class TriggeredRule(BaseModel):
    """Information about a triggered rule"""
    rule_id: str
    rule_name: str
    rule_type: str
    priority: str
    origin_match_type: str = "group"
    receiving_match_type: str = "group"
    odrl_type: str = "Permission"
    has_pii_required: bool = False
    description: Optional[str] = None
    outcome: RuleOutcomeType
    permissions: List[PermissionInfo] = Field(default_factory=list)
    prohibitions: List[ProhibitionInfo] = Field(default_factory=list)
    required_assessments: List[str] = Field(default_factory=list)
    required_actions: List[str] = Field(default_factory=list)
    matched_entities: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Entity dimensions that matched this rule, e.g. {'DataCategory': ['Health Data'], 'Regulator': ['ICO']}"
    )


class FieldMatch(BaseModel):
    """Shows how a specific field matched between query and case"""
    field_name: str
    query_values: List[str] = Field(default_factory=list)
    case_values: List[str] = Field(default_factory=list)
    match_type: str = "exact"
    match_percentage: float = 0.0


class CaseMatch(BaseModel):
    """Information about a matching case - used as evidence for precedent"""
    case_id: str
    case_ref_id: str
    case_status: str
    origin_country: str
    receiving_country: str
    pia_status: Optional[str] = None
    tia_status: Optional[str] = None
    hrpr_status: Optional[str] = None
    is_compliant: bool
    purposes: List[str] = Field(default_factory=list)
    process_l1: List[str] = Field(default_factory=list)
    process_l2: List[str] = Field(default_factory=list)
    process_l3: List[str] = Field(default_factory=list)
    personal_data_names: List[str] = Field(default_factory=list)
    data_categories: List[str] = Field(default_factory=list)
    legal_basis: Optional[str] = None
    created_date: Optional[str] = None
    last_updated: Optional[str] = None
    match_score: float = Field(default=1.0, description="How well this case matches the query (0-1)")
    field_matches: List[FieldMatch] = Field(default_factory=list, description="Field-by-field match analysis")
    relevance_explanation: Optional[str] = Field(default=None, description="Why this case is relevant as precedent")


class EvidenceSummary(BaseModel):
    """Summary of evidence supporting the evaluation decision"""
    total_cases_searched: int = 0
    compliant_cases_found: int = 0
    strongest_match_score: float = 0.0
    strongest_match_case_id: Optional[str] = None
    common_purposes: List[str] = Field(default_factory=list)
    common_data_categories: List[str] = Field(default_factory=list)
    assessment_coverage: Dict[str, str] = Field(default_factory=dict)
    confidence_level: str = "low"
    evidence_narrative: str = ""


class PrecedentValidation(BaseModel):
    """Results of precedent case validation"""
    total_matches: int
    compliant_matches: int
    has_valid_precedent: bool
    matching_cases: List[CaseMatch] = Field(default_factory=list)
    evidence_summary: Optional[EvidenceSummary] = None
    message: Optional[str] = None


class AssessmentCompliance(BaseModel):
    """Assessment compliance status"""
    pia_required: bool = False
    pia_compliant: bool = False
    tia_required: bool = False
    tia_compliant: bool = False
    hrpr_required: bool = False
    hrpr_compliant: bool = False
    all_compliant: bool = False
    missing_assessments: List[str] = Field(default_factory=list)


class DetectedAttribute(BaseModel):
    """Information about a detected attribute"""
    attribute_name: str
    detection_method: str
    matched_terms: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class EvaluationNode(BaseModel):
    """A node in the evaluation graph for visualization"""
    id: str
    type: str
    data: Dict[str, Any]
    position: Dict[str, float] = Field(default={"x": 0, "y": 0})


class EvaluationEdge(BaseModel):
    """An edge in the evaluation graph for visualization"""
    id: str
    source: str
    target: str
    type: str = "laneEdge"
    data: Dict[str, Any] = Field(default_factory=dict)


class EvaluationGraph(BaseModel):
    """A graph representing the evaluation path"""
    nodes: List[EvaluationNode] = Field(default_factory=list)
    edges: List[EvaluationEdge] = Field(default_factory=list)


# =============================================================================
# RESPONSE MODELS - Main
# =============================================================================

class RulesEvaluationResponse(BaseModel):
    """Response model for rules evaluation"""
    transfer_status: TransferStatus
    origin_country: str
    receiving_country: str
    pii: bool
    scenario_summary: Optional[str] = Field(default=None, description="Human-readable summary of the evaluated scenario")
    triggered_rules: List[TriggeredRule] = Field(default_factory=list)
    evaluation_graph: Optional[EvaluationGraph] = Field(default=None, description="Graph visualization of the evaluation path")
    precedent_validation: Optional[PrecedentValidation] = None
    assessment_compliance: Optional[AssessmentCompliance] = None
    detected_attributes: List[DetectedAttribute] = Field(default_factory=list)
    consolidated_duties: List[str] = Field(default_factory=list)
    required_actions: List[str] = Field(default_factory=list)
    prohibition_reasons: List[str] = Field(default_factory=list)
    evidence_summary: Optional[EvidenceSummary] = Field(default=None)
    message: str
    evaluation_time_ms: float = 0.0


class SearchCasesResponse(BaseModel):
    """Response model for case search"""
    total_count: int
    returned_count: int
    cases: List[CaseMatch]
    query_time_ms: float = 0.0


# Rules Overview - Table-friendly format for homepage
class RuleTableRow(BaseModel):
    """Single row in the rules overview table"""
    rule_id: str
    sending_country: str
    receiving_country: str
    rule_name: str
    rule_details: str
    permission_prohibition: str
    duty: str
    priority: str = "low"


class RulesOverviewTableResponse(BaseModel):
    """Table-friendly rules overview for homepage"""
    total_rules: int
    total_countries: int
    rows: List[RuleTableRow]
    filters: Dict[str, List[str]] = Field(default_factory=dict)


class RuleOverview(BaseModel):
    """Business-friendly rule overview"""
    rule_id: str
    name: str
    description: str
    rule_type: str
    priority: str
    origin_scope: str
    receiving_scope: str
    origin_match_type: str = "group"
    receiving_match_type: str = "group"
    outcome: str
    required_assessments: List[str]
    conditions: List[str]
    enabled: bool


class RulesOverviewResponse(BaseModel):
    """Response model for rules overview"""
    total_rules: int
    case_matching_rules: List[RuleOverview]
    transfer_rules: List[RuleOverview]
    attribute_rules: List[RuleOverview]


class AttributeConfigResponse(BaseModel):
    """Attribute detection configuration for attribute-level rules"""
    attribute_name: str
    keywords: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    detection_settings: Dict[str, Any] = Field(default_factory=dict)
    config_file_path: Optional[str] = None


class AgentActionEntry(BaseModel):
    """Record of a single agent action for traceability"""
    entry_id: str
    action_type: str
    agent_name: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    requires_approval: bool = False
    error_message: Optional[str] = None
    timestamp: str = ""


class AgentSessionSummary(BaseModel):
    """Summary of an agentic session"""
    session_id: str
    correlation_id: str
    session_type: str
    status: str
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    pending_approvals: int = 0
    agentic_mode: bool = False
    actions: List[AgentActionEntry] = Field(default_factory=list)
    created_at: str = ""
    completed_at: Optional[str] = None


class ReferenceDataResult(BaseModel):
    """Result of agentic reference data creation"""
    created: bool = False
    data_type: str = ""
    name: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = True
    approval_status: str = "pending"


class AIRuleGenerationResponse(BaseModel):
    """Response model for AI rule generation"""
    success: bool
    rule_id: Optional[str] = None
    rule_type: Optional[str] = None
    generated_dictionary: Optional[Dict[str, Any]] = None
    generated_cypher: Optional[str] = None
    generated_python_code: Optional[str] = None
    attribute_config: Optional[AttributeConfigResponse] = None
    attribute_config_json: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = Field(default_factory=list)
    message: str
    review_required: bool = True
    agentic_mode: bool = False
    reference_data_created: List[ReferenceDataResult] = Field(default_factory=list)
    agent_session: Optional[AgentSessionSummary] = None


class StatsResponse(BaseModel):
    """Dashboard statistics response"""
    total_cases: int
    total_countries: int
    total_jurisdictions: int
    total_purposes: int
    pia_completed_count: int
    tia_completed_count: int
    hrpr_completed_count: int
    rules_count: int
    cache_hit_rate: Optional[float] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    database_connected: bool
    rules_graph_loaded: bool
    data_graph_loaded: bool
    ai_service_available: bool
    timestamp: datetime


# =============================================================================
# ERROR MODELS
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ValidationErrorDetail(BaseModel):
    """Validation error detail"""
    field: str
    message: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "Validation Error"
    details: List[ValidationErrorDetail]
