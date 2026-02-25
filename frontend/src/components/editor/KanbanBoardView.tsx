import { memo, useState, useMemo, useCallback } from 'react';
import { useEditorStore } from '../../stores/editorStore';
import { KanbanColumn } from './KanbanColumn';
import { KanbanEdgeOverlay } from './KanbanEdgeOverlay';
import { KanbanContextMenuMemo } from './KanbanContextMenu';
import type { LaneDefinition } from '../../types/editor';

const COMMON_RELATIONSHIP_TYPES = [
  'TRIGGERED_BY_ORIGIN',
  'TRIGGERED_BY_RECEIVING',
  'ORIGINATES_FROM',
  'RECEIVED_IN',
  'HAS_DATA_CATEGORY',
  'HAS_PURPOSE',
  'HAS_GDC',
  'HAS_PROCESS',
  'HAS_ACTION',
  'HAS_PERMISSION',
  'HAS_PROHIBITION',
  'HAS_DUTY',
  'HAS_ATTRIBUTE',
  'HAS_DATA_SUBJECT',
  'HAS_LEGAL_ENTITY',
  'LINKED_TO',
  'HAS_AUTHORITY',
  'HAS_GBGF',
  'HAS_REGULATOR',
  'HAS_SENSITIVE_DATA_CATEGORY',
  'CAN_HAVE_DUTY',
  'BELONGS_TO',
  'BELONGS_TO_GBGF',
  'HAS_SUBPROCESS',
  'EXCLUDES_RECEIVING',
];

function KanbanBoardViewInner() {
  const nodes = useEditorStore((s) => s.visibleNodes);
  const edges = useEditorStore((s) => s.visibleEdges);
  const lanes = useEditorStore((s) => s.lanes);
  const selectedNodeIds = useEditorStore((s) => s.selectedNodeIds);
  const highlightedNodeIds = useEditorStore((s) => s.highlightedNodeIds);
  const clearHighlight = useEditorStore((s) => s.clearHighlight);
  const selectNode = useEditorStore((s) => s.selectNode);
  const addEdgeMode = useEditorStore((s) => s.addEdgeMode);
  const addEdgeSource = useEditorStore((s) => s.addEdgeSource);
  const pendingEdgeTarget = useEditorStore((s) => s.pendingEdgeTarget);
  const exitAddEdgeMode = useEditorStore((s) => s.exitAddEdgeMode);
  const confirmAddEdge = useEditorStore((s) => s.confirmAddEdge);
  const cancelPendingEdge = useEditorStore((s) => s.cancelPendingEdge);

  const [collapsedLanes, setCollapsedLanes] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');

  const sortedLanes = useMemo(
    () => [...lanes].sort((a, b) => a.order - b.order),
    [lanes]
  );

  const nodesByLane = useMemo(() => {
    const map: Record<string, typeof nodes> = {};
    for (const lane of sortedLanes) {
      map[lane.id] = [];
    }
    for (const node of nodes) {
      const lane = (node.data as Record<string, unknown>)?.lane as string;
      if (lane && map[lane]) {
        map[lane].push(node);
      }
    }
    return map;
  }, [nodes, sortedLanes]);

  const toggleCollapse = useCallback((laneId: string) => {
    setCollapsedLanes((prev) => {
      const next = new Set(prev);
      if (next.has(laneId)) next.delete(laneId);
      else next.add(laneId);
      return next;
    });
  }, []);

  const nonEmptyLanes = useMemo(
    () => sortedLanes.filter((lane) => (nodesByLane[lane.id]?.length || 0) > 0),
    [sortedLanes, nodesByLane]
  );

  const handleBoardClick = useCallback(() => {
    if (addEdgeMode) {
      exitAddEdgeMode();
      return;
    }
    clearHighlight();
    selectNode('');
  }, [clearHighlight, selectNode, addEdgeMode, exitAddEdgeMode]);

  // Get source node label for add-edge mode indicator
  const sourceNodeLabel = useMemo(() => {
    if (!addEdgeSource) return '';
    const sourceNode = nodes.find((n) => n.id === addEdgeSource);
    return (sourceNode?.data as { label?: string })?.label || addEdgeSource;
  }, [addEdgeSource, nodes]);

  const targetNodeLabel = useMemo(() => {
    if (!pendingEdgeTarget) return '';
    const targetNode = nodes.find((n) => n.id === pendingEdgeTarget);
    return (targetNode?.data as { label?: string })?.label || pendingEdgeTarget;
  }, [pendingEdgeTarget, nodes]);

  return (
    <div className="flex flex-col h-full bg-slate-50/50" onClick={handleBoardClick}>
      {/* Add Edge Mode Banner */}
      {addEdgeMode && (
        <div className="flex items-center gap-3 px-4 py-2 bg-purple-50 border-b border-purple-200 text-purple-700 text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
          Click a target node to create an edge from &ldquo;{sourceNodeLabel}&rdquo;
          <button
            onClick={(e) => { e.stopPropagation(); exitAddEdgeMode(); }}
            className="ml-auto px-2 py-0.5 bg-purple-100 hover:bg-purple-200 rounded text-purple-600 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Pending Edge Relationship Type Selection */}
      {pendingEdgeTarget && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50" onClick={(e) => { e.stopPropagation(); cancelPendingEdge(); }}>
          <div className="bg-white rounded-xl shadow-2xl p-5 w-80 max-h-96 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-bold text-gray-800 mb-1">Select Relationship Type</h3>
            <p className="text-[11px] text-gray-500 mb-3">
              {sourceNodeLabel} &rarr; {targetNodeLabel}
            </p>
            <div className="space-y-1">
              {COMMON_RELATIONSHIP_TYPES.map((rel) => (
                <button
                  key={rel}
                  onClick={() => confirmAddEdge(rel)}
                  className="w-full text-left px-3 py-1.5 text-xs text-gray-700 hover:bg-purple-50 hover:text-purple-700 rounded-md transition-colors"
                >
                  {rel}
                </button>
              ))}
            </div>
            <button
              onClick={cancelPendingEdge}
              className="mt-3 w-full py-1.5 text-xs text-gray-500 hover:text-gray-700 bg-gray-50 rounded-md transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Kanban Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-20">
        <div className="text-[11px] font-bold text-gray-400 uppercase tracking-tight">
          {nodes.length} Nodes &middot; {edges.length} Edges &middot; {nonEmptyLanes.length} Lanes
        </div>
        <div className="h-4 w-px bg-gray-200 mx-1" />

        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter entities..."
            className="pl-8 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-400/20 focus:border-purple-400 outline-none w-56 transition-all bg-gray-50/50"
          />
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
        </div>

        <div className="flex items-center gap-1.5 ml-auto">
          <button
            onClick={(e) => { e.stopPropagation(); setCollapsedLanes(new Set()); }}
            className="px-3 py-1.5 text-xs font-semibold text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-all"
          >
            Expand All
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); setCollapsedLanes(new Set(sortedLanes.map((l) => l.id))); }}
            className="px-3 py-1.5 text-xs font-semibold text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-all"
          >
            Collapse All
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6 relative group">
        <div className="flex gap-6 h-full min-w-max relative">
          {/* Edge SVG Overlay */}
          <KanbanEdgeOverlay />

          {nonEmptyLanes.map((lane: LaneDefinition) => (
            <KanbanColumn
              key={lane.id}
              lane={lane}
              nodes={nodesByLane[lane.id] || []}
              edges={edges}
              selectedNodeIds={selectedNodeIds}
              highlightedNodeIds={highlightedNodeIds}
              collapsed={collapsedLanes.has(lane.id)}
              onToggleCollapse={() => toggleCollapse(lane.id)}
              searchTerm={searchTerm}
            />
          ))}
        </div>
      </div>

      {/* Context Menu */}
      <KanbanContextMenuMemo />
    </div>
  );
}

export const KanbanBoardView = memo(KanbanBoardViewInner);
