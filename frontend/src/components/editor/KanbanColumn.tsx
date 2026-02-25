import { memo, useState, useMemo } from 'react';
import type { EditorNode, EditorEdge, LaneDefinition } from '../../types/editor';
import { KanbanCard } from './KanbanCard';
import { AddNodeDialog } from './AddNodeDialog';

const LANE_HEADER_COLORS: Record<string, string> = {
  originCountry: 'bg-sky-500',
  receivingCountry: 'bg-purple-500',
  rule: 'bg-red-500',
  dataCategory: 'bg-emerald-500',
  purpose: 'bg-amber-500',
  processes: 'bg-cyan-500',
  caseModule: 'bg-teal-500',
  gdc: 'bg-purple-500',
  legalEntity: 'bg-orange-500',
  dataSubject: 'bg-pink-500',
  permission: 'bg-green-500',
  prohibition: 'bg-red-400',
  attribute: 'bg-violet-500',
  authority: 'bg-purple-500',
  regulator: 'bg-rose-500',
  globalBusinessFunction: 'bg-lime-500',
  purposeOfProcessing: 'bg-yellow-500',
  sensitiveDataCategory: 'bg-fuchsia-500',
};

interface KanbanColumnProps {
  lane: LaneDefinition;
  nodes: EditorNode[];
  edges: EditorEdge[];
  selectedNodeIds: string[];
  highlightedNodeIds: string[];
  collapsed: boolean;
  onToggleCollapse: () => void;
  searchTerm: string;
}

function KanbanColumnInner({
  lane,
  nodes,
  edges,
  selectedNodeIds,
  highlightedNodeIds,
  collapsed,
  onToggleCollapse,
  searchTerm,
}: KanbanColumnProps) {
  const [showAddNode, setShowAddNode] = useState(false);

  const connectionCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const node of nodes) {
      counts[node.id] = 0;
    }
    const nodeIdSet = new Set(nodes.map((n) => n.id));
    for (const edge of edges) {
      if (nodeIdSet.has(edge.source)) counts[edge.source] = (counts[edge.source] || 0) + 1;
      if (nodeIdSet.has(edge.target)) counts[edge.target] = (counts[edge.target] || 0) + 1;
    }
    return counts;
  }, [nodes, edges]);

  const filteredNodes = useMemo(() => {
    if (!searchTerm.trim()) return nodes;
    const lower = searchTerm.toLowerCase();
    return nodes.filter((n) => {
      const data = n.data as Record<string, unknown>;
      const label = ((data.label as string) || '').toLowerCase();
      const desc = ((data.description as string) || '').toLowerCase();
      return label.includes(lower) || desc.includes(lower);
    });
  }, [nodes, searchTerm]);

  const headerColor = LANE_HEADER_COLORS[lane.id] || 'bg-gray-500';

  const highlightSet = useMemo(() => new Set(highlightedNodeIds), [highlightedNodeIds]);

  return (
    <div className="flex flex-col min-w-[260px] max-w-[320px] bg-white/40 backdrop-blur-sm rounded-xl border border-gray-200/60 overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-300">
      {/* Column Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer select-none bg-white/60 border-b border-gray-100"
        onClick={onToggleCollapse}
      >
        <div className="flex items-center gap-2.5">
          <div className={`w-3 h-3 rounded-full ${headerColor} shadow-inner`} />
          <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">{lane.label}</span>
          <span className="bg-gray-100 text-gray-500 text-[10px] px-1.5 py-0.5 rounded-full font-bold">{filteredNodes.length}</span>
        </div>
        <button className="text-gray-400 hover:text-gray-600 transition-colors">
          <svg className={`w-4 h-4 transition-transform ${collapsed ? '-rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {!collapsed && (
        <>
          {/* Card List */}
          <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-2.5 max-h-[calc(100vh-240px)] scrollbar-thin">
            {filteredNodes.length === 0 ? (
              <div className="text-[11px] text-gray-400 text-center py-8 italic font-medium">No entities found</div>
            ) : (
              filteredNodes.map((node) => (
                <KanbanCard
                  key={node.id}
                  node={node}
                  isSelected={selectedNodeIds.includes(node.id)}
                  isHighlighted={highlightSet.has(node.id)}
                  connectionCount={connectionCounts[node.id] || 0}
                />
              ))
            )}
          </div>

          {/* Add Node Button */}
          <div className="px-3 pb-3 pt-1">
            <button
              onClick={(e) => { e.stopPropagation(); setShowAddNode(true); }}
              className="w-full py-2 text-[10px] font-bold text-gray-400 hover:text-purple-600 hover:bg-purple-50/50 rounded-lg transition-all border border-dashed border-gray-200 hover:border-purple-200 uppercase tracking-widest"
            >
              + Create Entity
            </button>
          </div>

          {showAddNode && <AddNodeDialog onClose={() => setShowAddNode(false)} />}
        </>
      )}
    </div>
  );
}

export const KanbanColumn = memo(KanbanColumnInner);
