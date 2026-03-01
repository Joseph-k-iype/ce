/**
 * LogicTreeBuilder Type Definitions
 *
 * Defines the structure for the visual logic tree builder component
 * used across rules table, policy generator, and other interfaces.
 */

export type NodeType = 'AND' | 'OR' | 'CONDITION';

export interface LogicNode {
  type: NodeType;
  dimension?: string;      // For CONDITION only
  value?: string;          // For CONDITION only (comma-separated multi-select values)
  children?: LogicNode[];  // For AND/OR only
}

export interface DimensionConfig {
  name: string;            // 'DataCategory', 'Regulator', etc.
  label: string;           // 'Data Category', 'Regulator', etc.
  category: 'geography' | 'data' | 'regulatory';
  allowMultiSelect: boolean;
  allowCreate: boolean;    // Can create new values via API
  createEndpoint?: string; // POST /metadata/nodes
  nodeLabel: string;       // Graph node label (e.g., 'DataCategory')
  relationshipType: string; // Graph relationship type (e.g., 'HAS_DATA_CATEGORY')
}

export interface DropdownDataResponse {
  countries?: string[];
  data_categories?: Array<{ name: string; category?: string }>;
  purposes?: string[];
  processes?: {
    l1?: string[];
    l2?: string[];
    l3?: string[];
  };
  regulators?: Array<{ name: string }>;
  authorities?: Array<{ name: string }>;
  data_subjects?: Array<{ name: string }>;
  gdc?: Array<{ name: string }>;
  sensitive_data_categories?: Array<{ name: string }>;
  actions?: string[];  // For required actions/duties
}

export interface LogicTreeBuilderProps {
  initialTree?: LogicNode;
  dimensionConfigs: DimensionConfig[];
  dropdownData: DropdownDataResponse | null;
  onChange: (tree: LogicNode) => void;
  onValidate?: (tree: LogicNode) => ValidationResult;
  readOnly?: boolean;
  mode?: 'compact' | 'full';  // Compact for modals, full for dashboard
  className?: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: Array<{
    path: number[];  // Path to node with error
    message: string;
  }>;
}

export interface LogicTreeState {
  tree: LogicNode;
  history: LogicNode[];
  historyIndex: number;
}

export interface LogicTreeActions {
  updateNode: (path: number[], newNode: LogicNode) => void;
  removeNode: (path: number[]) => void;
  addChildNode: (path: number[], child: LogicNode) => void;
  setTree: (tree: LogicNode) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

export interface SelectOption {
  value: string;
  label: string;
}
