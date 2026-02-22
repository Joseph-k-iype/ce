import { memo, useMemo, useState, useCallback } from 'react';
import { useEditorStore } from '../../stores/editorStore';

const NODE_TYPE_COLORS: Record<string, string> = {
  Rule: 'bg-red-100 text-red-700',
  Country: 'bg-sky-100 text-sky-700',
  CountryGroup: 'bg-blue-100 text-blue-700',
  DataCategory: 'bg-emerald-100 text-emerald-700',
  Purpose: 'bg-amber-100 text-amber-700',
  Process: 'bg-cyan-100 text-cyan-700',
  GDC: 'bg-purple-100 text-purple-700',
  Duty: 'bg-teal-100 text-teal-700',
  Action: 'bg-teal-100 text-teal-700',
  Permission: 'bg-green-100 text-green-700',
  Prohibition: 'bg-red-100 text-red-700',
  LegalEntity: 'bg-orange-100 text-orange-700',
  DataSubject: 'bg-pink-100 text-pink-700',
  Attribute: 'bg-violet-100 text-violet-700',
  Authority: 'bg-indigo-100 text-indigo-700',
  Regulator: 'bg-rose-100 text-rose-700',
  GlobalBusinessFunction: 'bg-lime-100 text-lime-700',
  PurposeOfProcessing: 'bg-yellow-100 text-yellow-700',
  SensitiveDataCategory: 'bg-fuchsia-100 text-fuchsia-700',
};

const PROTECTED_RELATIONSHIPS = new Set([
  'TRIGGERED_BY_ORIGIN',
  'TRIGGERED_BY_RECEIVING',
  'BELONGS_TO',
  'EXCLUDES_RECEIVING',
]);

// Human-readable labels for relationship groups
const RELATIONSHIP_LABELS: Record<string, string> = {
  TRIGGERED_BY_ORIGIN: 'Originating Countries/Groups',
  TRIGGERED_BY_RECEIVING: 'Receiving Countries/Groups',
  EXCLUDES_RECEIVING: 'Excluded Receiving Groups',
  BELONGS_TO: 'Country Groups',
  HAS_PERMISSION: 'Permissions',
  HAS_PROHIBITION: 'Prohibitions',
  HAS_ACTION: 'Actions',
  HAS_DATA_CATEGORY: 'Data Categories',
  HAS_PURPOSE: 'Purposes',
  HAS_PROCESS: 'Processes',
  HAS_GDC: 'GDCs',
  HAS_DUTY: 'Duties',
  CAN_HAVE_DUTY: 'Duties',
  HAS_ATTRIBUTE: 'Attributes',
  HAS_DATA_SUBJECT: 'Data Subjects',
  HAS_LEGAL_ENTITY: 'Legal Entities',
  HAS_AUTHORITY: 'Authorities',
  HAS_REGULATOR: 'Regulators',
  HAS_GBGF: 'Global Business Functions',
  HAS_SENSITIVE_DATA_CATEGORY: 'Sensitive Data Categories',
  HAS_SUBPROCESS: 'Sub-Processes',
  BELONGS_TO_GBGF: 'Global Business Function',
  LINKED_TO: 'Linked Entities',
};

interface ConnectionItem {
  nodeId: string;
  edgeId: string;
  label: string;
  nodeType: string;
  relationship: string;
}

interface GroupedConnections {
  label: string;
  relationship: string;
  items: ConnectionItem[];
  direction: 'incoming' | 'outgoing';
}

function NodeDetailsSidebarInner() {
  const sidebarNodeId = useEditorStore((s) => s.sidebarNodeId);
  const closeSidebar = useEditorStore((s) => s.closeSidebar);
  const nodes = useEditorStore((s) => s.visibleNodes);
  const edges = useEditorStore((s) => s.visibleEdges);
  const openSidebar = useEditorStore((s) => s.openSidebar);
  const updateNodeData = useEditorStore((s) => s.updateNodeData);
  const removeNode = useEditorStore((s) => s.removeNode);
  const removeEdge = useEditorStore((s) => s.removeEdge);

  const [editMode, setEditMode] = useState(false);
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const node = useMemo(
    () => nodes.find((n) => n.id === sidebarNodeId),
    [nodes, sidebarNodeId]
  );

  // Build grouped connections for aggregated neighbor display
  const groupedConnections = useMemo(() => {
    if (!sidebarNodeId) return [];
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const groups = new Map<string, GroupedConnections>();

    for (const edge of edges) {
      let direction: 'incoming' | 'outgoing' | null = null;
      let neighborNode;

      if (edge.target === sidebarNodeId) {
        direction = 'incoming';
        neighborNode = nodeMap.get(edge.source);
      } else if (edge.source === sidebarNodeId) {
        direction = 'outgoing';
        neighborNode = nodeMap.get(edge.target);
      }

      if (!direction || !neighborNode) continue;

      const relationship = (edge.data as { relationship?: string })?.relationship || 'UNKNOWN';
      const groupKey = `${direction}:${relationship}`;
      const groupLabel = RELATIONSHIP_LABELS[relationship] || relationship.replace(/_/g, ' ');

      if (!groups.has(groupKey)) {
        groups.set(groupKey, {
          label: groupLabel,
          relationship,
          items: [],
          direction,
        });
      }

      groups.get(groupKey)!.items.push({
        nodeId: neighborNode.id,
        edgeId: edge.id,
        label: (neighborNode.data as { label?: string })?.label || neighborNode.id,
        nodeType: (neighborNode.data as { nodeType?: string })?.nodeType || '',
        relationship,
      });
    }

    // Sort: outgoing first, then by label
    return Array.from(groups.values()).sort((a, b) => {
      if (a.direction !== b.direction) return a.direction === 'outgoing' ? -1 : 1;
      return a.label.localeCompare(b.label);
    });
  }, [sidebarNodeId, nodes, edges]);

  const toggleGroup = useCallback((groupKey: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupKey)) next.delete(groupKey);
      else next.add(groupKey);
      return next;
    });
  }, []);

  const enterEditMode = useCallback(() => {
    if (!node) return;
    const data = node.data as unknown as Record<string, unknown>;
    const skipKeys = new Set(['nodeType', 'lane']);
    const vals: Record<string, string> = {};
    for (const [k, v] of Object.entries(data)) {
      if (!skipKeys.has(k) && v !== undefined && v !== null) {
        vals[k] = Array.isArray(v) ? v.join(', ') : String(v);
      }
    }
    setEditValues(vals);
    setEditMode(true);
  }, [node]);

  const handleSave = useCallback(async () => {
    if (!sidebarNodeId) return;
    setSaving(true);
    try {
      await updateNodeData(sidebarNodeId, editValues);
      setEditMode(false);
    } finally {
      setSaving(false);
    }
  }, [sidebarNodeId, editValues, updateNodeData]);

  const handleDeleteNode = useCallback(async () => {
    if (!sidebarNodeId || !node) return;
    const hasProtected = edges.some(
      (e) =>
        (e.source === sidebarNodeId || e.target === sidebarNodeId) &&
        PROTECTED_RELATIONSHIPS.has((e.data as { relationship?: string })?.relationship || '')
    );
    if (hasProtected) {
      alert('Cannot delete node with protected relationships.');
      return;
    }
    const label = (node.data as { label?: string })?.label || sidebarNodeId;
    if (confirm(`Delete node "${label}"? This action cannot be undone.`)) {
      closeSidebar();
      await removeNode(sidebarNodeId);
    }
  }, [sidebarNodeId, node, edges, closeSidebar, removeNode]);

  const handleDeleteEdge = useCallback(async (edgeId: string, relationship: string) => {
    if (PROTECTED_RELATIONSHIPS.has(relationship)) {
      alert('Cannot delete protected relationship.');
      return;
    }
    if (confirm(`Delete edge "${relationship}"?`)) {
      await removeEdge(edgeId);
    }
  }, [removeEdge]);

  const navigateToNode = useCallback((nodeId: string) => {
    openSidebar(nodeId);
  }, [openSidebar]);

  if (!sidebarNodeId || !node) return null;

  const data = node.data as unknown as Record<string, unknown>;
  const nodeType = (data.nodeType as string) || '';
  const label = (data.label as string) || node.id;
  const badgeColor = NODE_TYPE_COLORS[nodeType] || 'bg-gray-100 text-gray-700';

  const skipKeys = new Set(['label', 'nodeType', 'lane']);
  const properties = Object.entries(data).filter(
    ([k, v]) => !skipKeys.has(k) && v !== undefined && v !== null && v !== ''
  );

  const totalConnections = groupedConnections.reduce((sum, g) => sum + g.items.length, 0);

  return (
    <div className="w-96 bg-white border-l border-gray-200 overflow-y-auto flex flex-col shadow-lg">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-gray-100 bg-gray-50/50">
        <div className="flex-1 min-w-0">
          <span className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full mb-1.5 ${badgeColor}`}>
            {nodeType}
          </span>
          <h3 className="text-sm font-semibold text-gray-800 truncate">{label}</h3>
          <span className="text-[10px] text-gray-400">
            {totalConnections} connection{totalConnections !== 1 ? 's' : ''} across {groupedConnections.length} relationship type{groupedConnections.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div className="flex items-center gap-1 ml-2">
          <button
            onClick={editMode ? () => setEditMode(false) : enterEditMode}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              editMode ? 'bg-gray-200 text-gray-700' : 'text-gray-500 hover:bg-gray-100'
            }`}
            title={editMode ? 'Cancel edit' : 'Edit node'}
          >
            {editMode ? 'Cancel' : 'Edit'}
          </button>
          <button
            onClick={closeSidebar}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            &times;
          </button>
        </div>
      </div>

      {/* Properties */}
      {editMode ? (
        <div className="p-4 border-b border-gray-100">
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Edit Properties</h4>
          <div className="space-y-2">
            {Object.entries(editValues).map(([key, value]) => (
              <div key={key} className="flex flex-col">
                <label className="text-[10px] text-gray-400 mb-0.5">{key}</label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) =>
                    setEditValues((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                  className="text-xs text-gray-700 border border-gray-200 rounded px-2 py-1 focus:ring-1 focus:ring-blue-400 focus:border-blue-400 outline-none"
                />
              </div>
            ))}
            <div className="pt-2 border-t border-gray-100 mt-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="New key"
                  id="new-prop-key"
                  className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:border-blue-400"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const keyInput = e.currentTarget;
                      const valInput = document.getElementById('new-prop-val') as HTMLInputElement;
                      if (keyInput.value && valInput.value) {
                        setEditValues(prev => ({ ...prev, [keyInput.value]: valInput.value }));
                        keyInput.value = '';
                        valInput.value = '';
                        keyInput.focus();
                      }
                    }
                  }}
                />
                <input
                  type="text"
                  placeholder="Value"
                  id="new-prop-val"
                  className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:border-blue-400"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const valInput = e.currentTarget;
                      const keyInput = document.getElementById('new-prop-key') as HTMLInputElement;
                      if (keyInput.value && valInput.value) {
                        setEditValues(prev => ({ ...prev, [keyInput.value]: valInput.value }));
                        keyInput.value = '';
                        valInput.value = '';
                        keyInput.focus();
                      }
                    }
                  }}
                />
                <button
                  onClick={() => {
                    const keyInput = document.getElementById('new-prop-key') as HTMLInputElement;
                    const valInput = document.getElementById('new-prop-val') as HTMLInputElement;
                    if (keyInput.value && valInput.value) {
                      setEditValues(prev => ({ ...prev, [keyInput.value]: valInput.value }));
                      keyInput.value = '';
                      valInput.value = '';
                    }
                  }}
                  className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200"
                >
                  +
                </button>
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button
              onClick={handleDeleteNode}
              className="px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
      ) : (
        properties.length > 0 && (
          <div className="p-4 border-b border-gray-100">
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Properties</h4>
            <dl className="space-y-1.5">
              {properties.map(([key, value]) => (
                <div key={key} className="flex flex-col">
                  <dt className="text-[10px] text-gray-400">{key}</dt>
                  <dd className="text-xs text-gray-700 break-words">
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )
      )}

      {/* Aggregated Neighbor Groups */}
      {groupedConnections.length > 0 && (
        <div className="flex-1">
          <div className="px-4 pt-3 pb-1">
            <h4 className="text-xs font-semibold text-gray-500 uppercase">
              Connections ({totalConnections})
            </h4>
          </div>

          {groupedConnections.map((group) => {
            const groupKey = `${group.direction}:${group.relationship}`;
            const isCollapsed = collapsedGroups.has(groupKey);
            const isProtected = PROTECTED_RELATIONSHIPS.has(group.relationship);
            const dirIcon = group.direction === 'outgoing' ? '\u2192' : '\u2190';

            return (
              <div key={groupKey} className="border-b border-gray-50 last:border-b-0">
                <button
                  onClick={() => toggleGroup(groupKey)}
                  className="w-full flex items-center justify-between px-4 py-2 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <svg
                      className={`w-3 h-3 text-gray-400 transition-transform ${isCollapsed ? '' : 'rotate-90'}`}
                      fill="none" viewBox="0 0 24 24" stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    <span className="text-[10px] text-gray-400">{dirIcon}</span>
                    <span className="text-xs font-medium text-gray-700">{group.label}</span>
                  </div>
                  <span className="text-[10px] font-bold text-gray-400 bg-gray-100 rounded-full px-1.5 py-0.5">
                    {group.items.length}
                  </span>
                </button>

                {!isCollapsed && (
                  <ul className="px-4 pb-2 space-y-0.5">
                    {group.items.map((item, i) => {
                      const itemColor = NODE_TYPE_COLORS[item.nodeType] || 'bg-gray-100 text-gray-700';
                      return (
                        <li key={i} className="flex items-center justify-between group/item">
                          <button
                            onClick={() => navigateToNode(item.nodeId)}
                            className="flex-1 text-left text-xs hover:bg-blue-50 rounded px-2 py-1 transition-colors truncate flex items-center gap-1.5"
                          >
                            <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${itemColor.split(' ')[0].replace('100', '400')}`} />
                            <span className="font-medium text-gray-700">{item.label}</span>
                            <span className="text-[10px] text-gray-400">({item.nodeType})</span>
                          </button>
                          {isProtected ? (
                            <span className="text-[9px] text-gray-300 px-1 opacity-0 group-hover/item:opacity-100">locked</span>
                          ) : (
                            <button
                              onClick={() => handleDeleteEdge(item.edgeId, item.relationship)}
                              className="text-red-300 hover:text-red-500 text-[10px] px-1 opacity-0 group-hover/item:opacity-100 transition-opacity"
                              title="Delete edge"
                            >
                              ×
                            </button>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export const NodeDetailsSidebar = memo(NodeDetailsSidebarInner);
