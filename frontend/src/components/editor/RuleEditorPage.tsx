import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  Controls,
  Background,
  BackgroundVariant,
  MiniMap,
  type Node,
  type Edge,
  ReactFlowProvider,
} from '@xyflow/react';
import api from '../../services/api';

interface SubgraphNode {
  id: string;
  label: string;
  node_type: string;
  properties: Record<string, unknown>;
}

interface SubgraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_type: string;
}

interface SubgraphData {
  rule_id: string;
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
}

interface LinkedEntity {
  target_type: string;
  target_name: string;
  target_id?: string;
}

const NODE_COLORS: Record<string, string> = {
  Rule: '#1e293b',
  'Country/Group': '#3b82f6',
  Country: '#3b82f6',
  Permission: '#10b981',
  Prohibition: '#ef4444',
  Duty: '#f59e0b',
  Process: '#8b5cf6',
  Purpose: '#06b6d4',
  DataCategory: '#ec4899',
  LinkedEntity: '#6366f1',
  Entity: '#64748b',
};

// Map entity type to the API endpoint that lists available entities
const ENTITY_ENDPOINTS: Record<string, { endpoint: string; nameField: string; nestedKey?: string }> = {
  Regulator:              { endpoint: '/regulators', nameField: 'name' },
  Authority:              { endpoint: '/authorities', nameField: 'name' },
  Process:                { endpoint: '/all-dropdown-values', nameField: 'name', nestedKey: 'processes_dict' },
  PurposeOfProcessing:    { endpoint: '/purpose-of-processing', nameField: 'name' },
  DataCategory:           { endpoint: '/data-categories', nameField: 'name' },
  SensitiveDataCategory:  { endpoint: '/sensitive-data-categories', nameField: 'name' },
  GDC:                    { endpoint: '/all-dropdown-values', nameField: 'name', nestedKey: 'gdc' },
  DataSubject:            { endpoint: '/all-dropdown-values', nameField: 'name', nestedKey: 'data_subjects' },
  LegalEntity:            { endpoint: '/legal-entities', nameField: 'name' },
  GlobalBusinessFunction: { endpoint: '/global-business-functions', nameField: 'name' },
};

function toReactFlowNodes(subNodes: SubgraphNode[]): Node[] {
  const ruleNode = subNodes.find(n => n.node_type === 'Rule');
  const others = subNodes.filter(n => n.node_type !== 'Rule');

  const nodes: Node[] = [];

  // Center rule node
  if (ruleNode) {
    nodes.push({
      id: ruleNode.id,
      position: { x: 400, y: 300 },
      data: { label: ruleNode.label },
      style: {
        background: NODE_COLORS.Rule,
        color: '#fff',
        border: 'none',
        borderRadius: '12px',
        padding: '12px 20px',
        fontSize: '13px',
        fontWeight: 600,
        minWidth: '180px',
        textAlign: 'center' as const,
      },
    });
  }

  // Arrange neighbors in a circle around the rule
  const radius = 250;
  others.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / others.length - Math.PI / 2;
    const x = 400 + radius * Math.cos(angle);
    const y = 300 + radius * Math.sin(angle);
    const color = NODE_COLORS[node.node_type] || NODE_COLORS.Entity;

    nodes.push({
      id: node.id,
      position: { x, y },
      data: { label: node.label },
      style: {
        background: '#fff',
        color: '#1e293b',
        border: `2px solid ${color}`,
        borderRadius: '10px',
        padding: '8px 16px',
        fontSize: '12px',
        fontWeight: 500,
        minWidth: '120px',
        textAlign: 'center' as const,
      },
    });
  });

  return nodes;
}

function toReactFlowEdges(subEdges: SubgraphEdge[]): Edge[] {
  return subEdges.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.relationship_type,
    labelStyle: { fontSize: '10px', fill: '#94a3b8' },
    style: { stroke: '#cbd5e1', strokeWidth: 1.5 },
    type: 'default',
  }));
}

function RuleEditorContent() {
  const { ruleId } = useParams<{ ruleId: string }>();
  const navigate = useNavigate();
  const [subgraph, setSubgraph] = useState<SubgraphData | null>(null);
  const [links, setLinks] = useState<LinkedEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Link form state
  const [linkType, setLinkType] = useState('Regulator');
  const [linkName, setLinkName] = useState('');
  const [linkLoading, setLinkLoading] = useState(false);

  // Entity suggestions for autocomplete
  const [entitySuggestions, setEntitySuggestions] = useState<string[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!ruleId) return;
    setLoading(true);
    try {
      const [subRes, linksRes] = await Promise.all([
        api.get<SubgraphData>(`/rules/${encodeURIComponent(ruleId)}/subgraph`),
        api.get<LinkedEntity[]>(`/rules/${encodeURIComponent(ruleId)}/links`),
      ]);
      setSubgraph(subRes.data);
      setLinks(linksRes.data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load rule');
    } finally {
      setLoading(false);
    }
  }, [ruleId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Fetch entity suggestions when linkType changes
  useEffect(() => {
    const config = ENTITY_ENDPOINTS[linkType];
    if (!config) {
      setEntitySuggestions([]);
      return;
    }

    let cancelled = false;
    setSuggestionsLoading(true);

    api.get(config.endpoint).then(res => {
      if (cancelled) return;
      let items = res.data;

      // Handle nested keys (e.g., all-dropdown-values returns { gdc: [...], data_subjects: [...] })
      if (config.nestedKey && items && typeof items === 'object' && !Array.isArray(items)) {
        items = items[config.nestedKey] || [];
      }

      // Handle legal_entities which returns Record<string, string[]>
      if (linkType === 'LegalEntity' && items && typeof items === 'object' && !Array.isArray(items)) {
        const allNames: string[] = [];
        Object.values(items).forEach((les) => {
          if (Array.isArray(les)) allNames.push(...les);
        });
        setEntitySuggestions([...new Set(allNames)].sort());
        setSuggestionsLoading(false);
        return;
      }

      if (Array.isArray(items)) {
        const names = items
          .map((item: string | Record<string, unknown>) =>
            typeof item === 'string' ? item : String(item[config.nameField] || '')
          )
          .filter(Boolean)
          .sort();
        setEntitySuggestions([...new Set(names)]);
      } else {
        setEntitySuggestions([]);
      }
      setSuggestionsLoading(false);
    }).catch(() => {
      if (!cancelled) {
        setEntitySuggestions([]);
        setSuggestionsLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [linkType]);

  const nodes = useMemo(() => subgraph ? toReactFlowNodes(subgraph.nodes) : [], [subgraph]);
  const edges = useMemo(() => subgraph ? toReactFlowEdges(subgraph.edges) : [], [subgraph]);

  const handleAddLink = async () => {
    if (!ruleId || !linkName.trim()) return;
    setLinkLoading(true);
    try {
      await api.post(`/rules/${encodeURIComponent(ruleId)}/link`, {
        target_type: linkType,
        target_name: linkName.trim(),
      });
      setLinkName('');
      await fetchData();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || (err instanceof Error ? err.message : 'Failed to create link'));
    } finally {
      setLinkLoading(false);
    }
  };

  const handleRemoveLink = async (entity: LinkedEntity) => {
    if (!ruleId) return;
    try {
      await api.delete(`/rules/${encodeURIComponent(ruleId)}/unlink`, {
        data: { target_type: entity.target_type, target_name: entity.target_name },
      });
      await fetchData();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || (err instanceof Error ? err.message : 'Failed to remove link'));
    }
  };

  const entityTypes = [
    'Regulator', 'Authority', 'Process', 'PurposeOfProcessing',
    'DataCategory', 'SensitiveDataCategory', 'GDC', 'DataSubject',
    'LegalEntity', 'GlobalBusinessFunction',
  ];

  // Datalist ID for the entity name autocomplete
  const datalistId = `entity-suggestions-${linkType}`;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-3 border-gray-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Graph view */}
      <div className="flex-1 relative">
        <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
          <button
            onClick={() => navigate('/editor')}
            className="bg-white border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:border-gray-300 transition-colors shadow-sm"
          >
            &larr; Back to Rules
          </button>
          <span className="text-sm font-medium text-gray-900">{ruleId}</span>
        </div>

        {error && (
          <div className="absolute top-3 right-3 z-10 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 max-w-xs">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-400 hover:text-red-600">&times;</button>
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
          <MiniMap pannable zoomable style={{ bottom: 12, right: 12 }} />
          <Controls position="bottom-left" />
        </ReactFlow>
      </div>

      {/* Sidebar: links management */}
      <div className="w-80 border-l border-gray-200 bg-gray-50/50 overflow-y-auto">
        <div className="p-4 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">Linked Entities</h3>

          {/* Current links */}
          <div className="space-y-1.5">
            {links.length === 0 && (
              <p className="text-xs text-gray-400">No linked entities yet.</p>
            )}
            {links.map((link, i) => (
              <div key={i} className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-3 py-2">
                <div>
                  <span className="text-xs font-medium text-gray-500">{link.target_type}</span>
                  <p className="text-sm text-gray-900">{link.target_name}</p>
                </div>
                <button
                  onClick={() => handleRemoveLink(link)}
                  className="text-xs text-red-500 hover:text-red-700"
                  title="Remove link"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>

          {/* Add link form */}
          <div className="border-t border-gray-200 pt-3 space-y-2">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Add Link</h4>
            <select
              value={linkType}
              onChange={e => { setLinkType(e.target.value); setLinkName(''); }}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
            >
              {entityTypes.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            {suggestionsLoading ? (
              <div className="text-xs text-gray-400 py-1">Loading entities...</div>
            ) : entitySuggestions.length > 0 ? (
              <>
                <input
                  type="text"
                  list={datalistId}
                  value={linkName}
                  onChange={e => setLinkName(e.target.value)}
                  placeholder={`Search ${linkType}...`}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
                  onKeyDown={e => e.key === 'Enter' && handleAddLink()}
                />
                <datalist id={datalistId}>
                  {entitySuggestions.map(name => (
                    <option key={name} value={name} />
                  ))}
                </datalist>
              </>
            ) : (
              <input
                type="text"
                value={linkName}
                onChange={e => setLinkName(e.target.value)}
                placeholder="Entity name..."
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
                onKeyDown={e => e.key === 'Enter' && handleAddLink()}
              />
            )}
            <button
              onClick={handleAddLink}
              disabled={linkLoading || !linkName.trim()}
              className="w-full bg-gray-900 text-white rounded-lg px-3 py-2 text-sm font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {linkLoading ? 'Linking...' : 'Add Link'}
            </button>
          </div>

          {/* Rule properties */}
          {subgraph && subgraph.nodes.length > 0 && (() => {
            const ruleNode = subgraph.nodes.find(n => n.node_type === 'Rule');
            if (!ruleNode) return null;
            const props = ruleNode.properties;
            return (
              <div className="border-t border-gray-200 pt-3 space-y-2">
                <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">Rule Properties</h4>
                <div className="space-y-1">
                  {Object.entries(props).filter(([k]) => !['name', 'rule_id'].includes(k)).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-gray-500">{key}</span>
                      <span className="text-gray-900 font-medium text-right max-w-[150px] truncate">
                        {String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

export function RuleEditorPage() {
  return (
    <div className="flex-1 flex flex-col h-full">
      <ReactFlowProvider>
        <RuleEditorContent />
      </ReactFlowProvider>
    </div>
  );
}
