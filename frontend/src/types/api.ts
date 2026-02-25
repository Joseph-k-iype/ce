export interface RulesEvaluationRequest {
  origin_country: string;
  receiving_country?: string | string[];
  pii?: boolean;

  // New simplified fields (comma-separated strings or arrays)
  purpose_of_processing?: string | string[];
  data_categories?: string | string[];
  sensitive_data_categories?: string | string[];
  processes?: string | string[];
  gbgf?: string | string[];
  gdc?: string | string[];
  data_subjects?: string | string[];
  regulator?: string | string[];
  authority?: string | string[];
  legal_entities?: string | string[];
  personal_data_names?: string | string[];
  metadata?: Record<string, unknown>;

  // Legacy fields (backward compatibility)
  purposes?: string[];
  process_l1?: string[];
  process_l2?: string[];
  process_l3?: string[];
  origin_legal_entity?: string;
  receiving_legal_entity?: string[];
}

export interface TriggeredRule {
  rule_id: string;
  rule_name: string;
  rule_type: string;
  priority: string;
  origin_match_type?: string;
  receiving_match_type?: string;
  odrl_type: string;
  has_pii_required?: boolean;
  outcome: string;
  description?: string;
  required_assessments: string[];
  required_actions: string[];
  permissions: {
    permission_id: string;
    name: string;
    description?: string;
    duties: { duty_id: string; name: string; module: string; value: string; description?: string }[];
  }[];
  prohibitions: {
    prohibition_id: string;
    name: string;
    description?: string;
  }[];
  matched_entities?: Record<string, string[]>;
}

export interface CaseMatch {
  case_id: string;
  case_ref_id: string;
  case_status: string;
  origin_country: string;
  receiving_country: string;
  pia_status?: string;
  tia_status?: string;
  hrpr_status?: string;
  is_compliant: boolean;
  match_score: number;
  relevance_explanation?: string;
}

export interface EvidenceSummary {
  total_cases_searched: number;
  compliant_cases_found: number;
  strongest_match_score: number;
  confidence_level: string;
  evidence_narrative: string;
}

export interface AssessmentCompliance {
  pia_required: boolean;
  tia_required: boolean;
  hrpr_required: boolean;
  pia_compliant?: boolean;
  tia_compliant?: boolean;
  hrpr_compliant?: boolean;
  all_compliant?: boolean;
  missing_assessments?: string[];
}

export interface DetectedAttribute {
  attribute_name: string;
  detection_method?: string;
  matched_terms?: string[];
  confidence: number;
}

export interface EvaluationNode {
  id: string;
  type: string;
  data: {
    label: string;
    nodeType: string;
    lane: string;
    outcome?: string;
    priority?: string;
    [key: string]: unknown;
  };
  position: { x: number; y: number };
}

export interface EvaluationEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
  data?: {
    relationship: string;
    [key: string]: unknown;
  };
}

export interface EvaluationGraph {
  nodes: EvaluationNode[];
  edges: EvaluationEdge[];
}

export interface RulesEvaluationResponse {
  transfer_status: 'ALLOWED' | 'PROHIBITED' | 'REQUIRES_REVIEW' | 'INSUFFICIENT_DATA';
  origin_country: string;
  receiving_country: string;
  pii: boolean;
  scenario_summary?: string;
  triggered_rules: TriggeredRule[];
  evaluation_graph?: EvaluationGraph;
  precedent_validation?: {
    total_matches: number;
    compliant_matches: number;
    has_valid_precedent: boolean;
    matching_cases: CaseMatch[];
    evidence_summary?: EvidenceSummary;
  };
  assessment_compliance?: AssessmentCompliance;
  detected_attributes: DetectedAttribute[];
  consolidated_duties: string[];
  required_actions: string[];
  prohibition_reasons: string[];
  evidence_summary?: EvidenceSummary;
  message: string;
  evaluation_time_ms: number;
}

export interface DictionaryEntry {
  name: string;
  category: string;
}

export interface DropdownValues {
  countries: string[];
  purposes: string[];
  processes: {
    l1: string[];
    l2: string[];
    l3: string[];
  };
  processes_dict: DictionaryEntry[];
  purposes_dict: DictionaryEntry[];
  data_subjects: DictionaryEntry[];
  gdc: DictionaryEntry[];
  legal_entities: Record<string, string[]>;
  purpose_of_processing: (string | { name: string; description?: string })[];
  group_data_categories: DictionaryEntry[];

  // New entity types (graph-native)
  regulators?: { id: string; name: string; country_code: string }[];
  authorities?: { id: string; name: string; country_code: string }[];
  global_business_functions?: DictionaryEntry[];
  sensitive_data_categories?: DictionaryEntry[];
  data_categories?: DictionaryEntry[];
  country_groups?: string[];
}

export interface RuleTableRow {
  rule_id: string;
  sending_country: string;
  receiving_country: string;
  rule_name: string;
  rule_details: string;
  permission_prohibition: string;
  duty: string;
  priority: string;
}

export interface RulesOverviewTableResponse {
  total_rules: number;
  total_countries: number;
  rows: RuleTableRow[];
  filters: Record<string, string[]>;
}

export interface HealthCheck {
  status: string;
  version: string;
  database_connected: boolean;
  rules_graph_loaded: boolean;
  data_graph_loaded: boolean;
  ai_service_available: boolean;
}

export interface RuleOverview {
  rule_id: string;
  name: string;
  description: string;
  rule_type: string;
  priority: string;
  origin_scope: string;
  receiving_scope: string;
  outcome: string;
  required_assessments: string[];
  conditions: string[];
  enabled: boolean;
}

export interface RulesOverviewResponse {
  total_rules: number;
  case_matching_rules: RuleOverview[];
  transfer_rules: RuleOverview[];
  attribute_rules: RuleOverview[];
}
