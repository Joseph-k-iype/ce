export interface WizardSession {
  session_id: string;
  status: string;
  current_step: number;
  origin_country?: string;
  receiving_countries: string[];
  origin_legal_entity?: string;
  receiving_legal_entity?: string;
  data_categories: string[];
  purposes_of_processing: string[];
  process_l1: string[];
  process_l2: string[];
  process_l3: string[];
  group_data_categories: string[];
  sensitive_data_categories: string[];
  regulators: string[];
  authorities: string[];
  data_subjects: string[];
  valid_until?: string;
  rule_text?: string;
  analysis_result?: Record<string, unknown>;
  dictionary_result?: Record<string, unknown>;
  proposal?: Record<string, unknown>;
  edited_rule_definition?: Record<string, unknown>;
  edited_terms_dictionary?: Record<string, unknown>;
  sandbox_graph_name?: string;
  sandbox_test_results: Record<string, unknown>[];
  approved: boolean;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface WizardStepData {
  step: number;
  data: Record<string, unknown>;
}

export interface TriggerLogicResponse {
  origin_group?: string;
  origin_countries: string[];
  receiving_group?: string;
  receiving_countries: string[];
  logic: 'OR' | 'AND';
  dimensions: Record<string, string[]>;
  attribute_keywords_count: number;
  requires_pii: boolean;
}

export interface SavedSession {
  session_id: string;
  user_id: string;
  origin_country?: string;
  receiving_countries: string[];
  rule_text?: string;
  current_step: number;
  status: string;
  saved_at: string;
  updated_at: string;
}
