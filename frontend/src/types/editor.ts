import type { Node, Edge } from '@xyflow/react';

// Lane definitions
export interface LaneDefinition {
  id: string;
  label: string;
  order: number;
  primary: boolean;
}

export const PRIMARY_LANES: LaneDefinition[] = [
  { id: 'originCountry', label: 'Originating Country', order: 0, primary: true },
  { id: 'receivingCountry', label: 'Receiving Country', order: 1, primary: true },
  { id: 'rule', label: 'Rule', order: 2, primary: true },
  { id: 'dataCategory', label: 'Data Category', order: 3, primary: true },
  { id: 'purpose', label: 'Purpose of Processing', order: 4, primary: true },
  { id: 'processes', label: 'Processes', order: 5, primary: true },
  { id: 'caseModule', label: 'Case Module', order: 6, primary: true },
];

export const EXTRA_LANES: LaneDefinition[] = [
  { id: 'gdc', label: 'GDC', order: 7, primary: false },
  { id: 'legalEntity', label: 'Legal Entity', order: 8, primary: false },
  { id: 'dataSubject', label: 'Data Subject', order: 9, primary: false },
  { id: 'permission', label: 'Permission', order: 10, primary: false },
  { id: 'prohibition', label: 'Prohibition', order: 11, primary: false },
  { id: 'attribute', label: 'Attribute', order: 12, primary: false },
  { id: 'authority', label: 'Authority', order: 13, primary: false },
  { id: 'regulator', label: 'Regulator', order: 14, primary: false },
  { id: 'globalBusinessFunction', label: 'Global Business Function', order: 15, primary: false },
  { id: 'purposeOfProcessing', label: 'Purpose of Processing (Detail)', order: 16, primary: false },
  { id: 'sensitiveDataCategory', label: 'Sensitive Data Category', order: 17, primary: false },
];

export const ALL_LANES: LaneDefinition[] = [...PRIMARY_LANES, ...EXTRA_LANES];

// Node types for React Flow registration
export type EditorNodeType =
  | 'countryGroupNode'
  | 'countryNode'
  | 'ruleNode'
  | 'dataCategoryNode'
  | 'purposeNode'
  | 'gdcNode'
  | 'processNode'
  | 'caseModuleNode';

// Base data all editor nodes share
export interface EditorNodeDataBase {
  label: string;
  nodeType: string;
  lane: string;
  description?: string;
  [key: string]: unknown;
}

// Specific node data shapes
export interface CountryGroupNodeData extends EditorNodeDataBase {
  nodeType: 'CountryGroup';
  countries: string[];
  countryCount: number;
  expanded?: boolean;
}

export interface CountryNodeData extends EditorNodeDataBase {
  nodeType: 'Country';
  countryCount?: number;
}

export interface RuleNodeData extends EditorNodeDataBase {
  nodeType: 'Rule';
  ruleId: string;
  odrlType: 'Permission' | 'Prohibition';
  priority?: number;
  hasPiiRequired?: boolean;
  permissionName?: string;
  prohibitionName?: string;
  actionName?: string;
}

export interface DataCategoryNodeData extends EditorNodeDataBase {
  nodeType: 'DataCategory';
}

export interface PurposeNodeData extends EditorNodeDataBase {
  nodeType: 'Purpose';
}

export interface GdcNodeData extends EditorNodeDataBase {
  nodeType: 'GDC';
}

export interface ProcessNodeData extends EditorNodeDataBase {
  nodeType: 'Process';
  category?: string;
}

export interface CaseModuleNodeData extends EditorNodeDataBase {
  nodeType: 'Duty' | 'Action' | 'Permission' | 'Prohibition' | 'Authority' | 'Regulator' | 'GlobalBusinessFunction' | 'PurposeOfProcessing' | 'SensitiveDataCategory';
  subType?: string;
}

export type EditorNodeData =
  | CountryGroupNodeData
  | CountryNodeData
  | RuleNodeData
  | DataCategoryNodeData
  | PurposeNodeData
  | GdcNodeData
  | ProcessNodeData
  | CaseModuleNodeData;

// React Flow node/edge aliases
export type EditorNode = Node<EditorNodeData>;
export type EditorEdge = Edge<{ relationship: string }>;

// API response shape
export interface EditorNetworkResponse {
  nodes: EditorNode[];
  edges: EditorEdge[];
  lanes: LaneDefinition[];
  stats: {
    total_nodes: number;
    total_edges: number;
  };
}

// Edge relationship types
export type RelationshipType =
  | 'TRIGGERED_BY_ORIGIN'
  | 'TRIGGERED_BY_RECEIVING'
  | 'HAS_DATA_CATEGORY'
  | 'HAS_PURPOSE'
  | 'HAS_GDC'
  | 'HAS_PROCESS'
  | 'HAS_ACTION'
  | 'HAS_PERMISSION'
  | 'HAS_PROHIBITION'
  | 'HAS_DUTY'
  | 'BELONGS_TO'
  | 'EXCLUDES_RECEIVING'
  | 'HAS_ATTRIBUTE'
  | 'HAS_DATA_SUBJECT'
  | 'HAS_LEGAL_ENTITY'
  | 'LINKED_TO'
  | 'HAS_AUTHORITY'
  | 'HAS_GBGF'
  | 'HAS_REGULATOR'
  | 'HAS_SENSITIVE_DATA_CATEGORY'
  | 'CAN_HAVE_DUTY'
  | 'BELONGS_TO_GBGF'
  | 'HAS_SUBPROCESS';

// Neighbor data for side panel (future use)
export interface NeighborData {
  ingress: { node: EditorNode; edge: EditorEdge }[];
  egress: { node: EditorNode; edge: EditorEdge }[];
}

// Path result
export interface PathResult {
  nodeIds: string[];
  edgeIds: string[];
}

// Context menu state
export interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  nodeId: string | null;
}

// Filter state
export interface FilterState {
  country: string;
  ruleSearch: string;
  dataCategory: string;
  process: string;
}
