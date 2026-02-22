export interface GraphNode {
  id: string;
  type: string;
  data: {
    label?: string;
    rule_id?: string;
    priority?: number;
    odrl_type?: string;
    outcome?: string;
    countries?: string[];
    country_count?: number;
    has_pii_required?: boolean;
    permission_name?: string;
    prohibition_name?: string;
    expanded?: boolean;
    onExpand?: () => void;
    side?: 'origin' | 'receiving';
  };
  position: { x: number; y: number };
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  data?: {
    relationship: string;
  };
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_rules: number;
    total_groups: number;
    total_edges: number;
  };
}

// Admin-specific types
export interface AdminNodeData {
  label: string;
  category?: string;
  dictType?: 'processes' | 'purposes' | 'data_subjects' | 'gdc';
}

export interface AdminGraphNode {
  id: string;
  type: 'ruleNode' | 'countryGroup' | 'adminNode';
  data: Record<string, unknown>;
  position: { x: number; y: number };
}

export interface AdminRule {
  rule_id: string;
  name: string;
  description: string;
  rule_type: string;
  priority: string;
  outcome: string;
  origin_match_type: string;
  receiving_match_type: string;
  enabled: boolean;
  odrl_type: string;
  origin_scopes: string[];
  receiving_scopes: string[];
  required_assessments: string[];
}

export interface AdminCountryGroup {
  name: string;
  countries: string[];
}

export interface AdminDictionaryEntry {
  name: string;
  category: string;
}
