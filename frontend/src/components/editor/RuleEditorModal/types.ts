/**
 * RuleEditorModal Type Definitions
 *
 * Defines interfaces for the comprehensive rule creation/editing modal
 */

import type { LogicNode } from '../../shared/LogicTreeBuilder/types';

export interface RuleFormData {
  // Basic Info
  name: string;
  description: string;
  outcome: 'permission' | 'prohibition';
  priority: 'high' | 'medium' | 'low';
  enabled: boolean;
  valid_until: string | null;
  requires_pii: boolean;

  // Trigger Logic
  logic_tree: LogicNode;

  // Entity Mapping
  data_categories: string[];
  purposes: string[];
  processes: string[];
  regulators: string[];
  authorities: string[];
  data_subjects: string[];
  gdc: string[];
  sensitive_data_categories: string[];

  // Duties
  required_assessments: string[];  // ['PIA', 'TIA', 'HRPR']
  required_actions: string[];      // Free-form action strings
}

export interface RuleEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  ruleId?: string | null;  // null for create mode, string for edit mode
  onSave?: (ruleId: string) => void;  // Callback after successful save
}

export interface TestScenario {
  origin_country?: string;
  receiving_country?: string;
  data_categories?: string[];
  purposes?: string[];
  processes?: string[];
  regulators?: string[];
  authorities?: string[];
  data_subjects?: string[];
  gdc?: string[];
  sensitive_data_categories?: string[];
}

export interface TestResult {
  matched: boolean;
  evaluation_result: {
    allowed: boolean;
    reason: string;
    matched_rules: string[];
    required_duties: string[];
  };
}
