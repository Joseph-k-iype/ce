import { memo, useCallback, useEffect, useRef, useMemo } from 'react';
import { useReactFlow } from '@xyflow/react';
import { useEditorStore } from '../../stores/editorStore';
import { getNeighborhood } from '../../utils/pathfinding';

const PROTECTED_RELATIONSHIPS = new Set([
  'TRIGGERED_BY_ORIGIN',
  'TRIGGERED_BY_RECEIVING',
  'BELONGS_TO',
  'EXCLUDES_RECEIVING',
]);

function ContextMenuInner() {
  const { contextMenu, hideContextMenu, setHighlight, clearHighlight, openSidebar, enterAddEdgeMode, removeNode } =
    useEditorStore();
  const edges = useEditorStore((s) => s.visibleEdges);
  const nodes = useEditorStore((s) => s.visibleNodes);
  const { fitView, setCenter } = useReactFlow();
  const ref = useRef<HTMLDivElement>(null);

  const nodeId = contextMenu.nodeId;

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as HTMLElement)) {
        hideContextMenu();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [hideContextMenu]);

  // Compute connections for this node
  const connections = useMemo(() => {
    if (!nodeId) return { incoming: [], outgoing: [] };
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const incoming: { label: string; relationship: string }[] = [];
    const outgoing: { label: string; relationship: string }[] = [];

    for (const edge of edges) {
      if (edge.target === nodeId) {
        const src = nodeMap.get(edge.source);
        if (src) {
          incoming.push({
            label: (src.data as { label?: string })?.label || src.id,
            relationship: (edge.data as { relationship?: string })?.relationship || '',
          });
        }
      }
      if (edge.source === nodeId) {
        const tgt = nodeMap.get(edge.target);
        if (tgt) {
          outgoing.push({
            label: (tgt.data as { label?: string })?.label || tgt.id,
            relationship: (edge.data as { relationship?: string })?.relationship || '',
          });
        }
      }
    }
    return { incoming, outgoing };
  }, [nodeId, nodes, edges]);

  // Check if node has protected relationships
  const hasProtectedRels = useMemo(() => {
    if (!nodeId) return false;
    return edges.some(
      (e) =>
        (e.source === nodeId || e.target === nodeId) &&
        PROTECTED_RELATIONSHIPS.has((e.data as { relationship?: string })?.relationship || '')
    );
  }, [nodeId, edges]);

  const handleShowDetails = useCallback(() => {
    if (nodeId) openSidebar(nodeId);
    hideContextMenu();
  }, [nodeId, openSidebar, hideContextMenu]);

  const handleHighlightConnections = useCallback(() => {
    if (!nodeId) return;
    const result = getNeighborhood(nodeId, edges, 1);
    setHighlight(result.nodeIds, result.edgeIds);
    hideContextMenu();
  }, [nodeId, edges, setHighlight, hideContextMenu]);

  const handleFocusNeighborhood = useCallback(() => {
    if (!nodeId) return;
    const result = getNeighborhood(nodeId, edges, 1);
    setHighlight(result.nodeIds, result.edgeIds);
    fitView({ nodes: result.nodeIds.map((id) => ({ id })), padding: 0.3, duration: 400 });
    hideContextMenu();
  }, [nodeId, edges, setHighlight, fitView, hideContextMenu]);

  const handleCenterOnNode = useCallback(() => {
    if (!nodeId) return;
    const node = nodes.find((n) => n.id === nodeId);
    if (node) {
      setCenter(node.position.x + 110, node.position.y + 30, { zoom: 1.2, duration: 400 });
    }
    hideContextMenu();
  }, [nodeId, nodes, setCenter, hideContextMenu]);

  const handleEditNode = useCallback(() => {
    if (nodeId) openSidebar(nodeId);
    hideContextMenu();
  }, [nodeId, openSidebar, hideContextMenu]);

  const handleDeleteNode = useCallback(() => {
    if (!nodeId) return;
    if (hasProtectedRels) {
      alert('Cannot delete node with protected relationships (TRIGGERED_BY_ORIGIN, TRIGGERED_BY_RECEIVING, BELONGS_TO, EXCLUDES_RECEIVING).');
      hideContextMenu();
      return;
    }
    if (confirm(`Delete node "${(nodes.find((n) => n.id === nodeId)?.data as { label?: string })?.label || nodeId}"?`)) {
      removeNode(nodeId);
    }
    hideContextMenu();
  }, [nodeId, hasProtectedRels, nodes, removeNode, hideContextMenu]);

  const handleAddEdgeFromHere = useCallback(() => {
    if (nodeId) {
      enterAddEdgeMode(nodeId);
    }
    hideContextMenu();
  }, [nodeId, enterAddEdgeMode, hideContextMenu]);

  const handleClearHighlights = useCallback(() => {
    clearHighlight();
    hideContextMenu();
  }, [clearHighlight, hideContextMenu]);

  if (!contextMenu.visible) return null;

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-white rounded-lg shadow-xl border border-gray-200 py-1 min-w-[200px]"
      style={{ left: contextMenu.x, top: contextMenu.y }}
    >
      <button
        onClick={handleShowDetails}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Show Details
      </button>
      <button
        onClick={handleEditNode}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Edit Node
      </button>
      <button
        onClick={handleHighlightConnections}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Highlight Connections
      </button>
      <button
        onClick={handleFocusNeighborhood}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Focus Neighborhood
      </button>
      <button
        onClick={handleCenterOnNode}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Center on Node
      </button>

      <div className="border-t border-gray-100 my-1" />

      {/* Connection info */}
      {connections.incoming.length > 0 && (
        <div className="px-4 py-1.5">
          <span className="text-[10px] font-semibold text-gray-400 uppercase">Incoming ({connections.incoming.length})</span>
          <div className="max-h-20 overflow-y-auto">
            {connections.incoming.slice(0, 5).map((c, i) => (
              <div key={i} className="text-xs text-gray-500 truncate">
                <span className="text-gray-400">{c.relationship}</span> {c.label}
              </div>
            ))}
            {connections.incoming.length > 5 && (
              <span className="text-[10px] text-gray-400">+{connections.incoming.length - 5} more</span>
            )}
          </div>
        </div>
      )}
      {connections.outgoing.length > 0 && (
        <div className="px-4 py-1.5">
          <span className="text-[10px] font-semibold text-gray-400 uppercase">Outgoing ({connections.outgoing.length})</span>
          <div className="max-h-20 overflow-y-auto">
            {connections.outgoing.slice(0, 5).map((c, i) => (
              <div key={i} className="text-xs text-gray-500 truncate">
                <span className="text-gray-400">{c.relationship}</span> {c.label}
              </div>
            ))}
            {connections.outgoing.length > 5 && (
              <span className="text-[10px] text-gray-400">+{connections.outgoing.length - 5} more</span>
            )}
          </div>
        </div>
      )}

      <div className="border-t border-gray-100 my-1" />

      <button
        onClick={handleAddEdgeFromHere}
        className="w-full text-left px-4 py-2 text-sm text-purple-600 hover:bg-purple-50 transition-colors"
      >
        Add Edge From Here
      </button>
      <button
        onClick={handleDeleteNode}
        className={`w-full text-left px-4 py-2 text-sm transition-colors ${
          hasProtectedRels
            ? 'text-gray-400 cursor-not-allowed'
            : 'text-red-600 hover:bg-red-50'
        }`}
      >
        Delete Node {hasProtectedRels && '(protected)'}
      </button>

      <div className="border-t border-gray-100 my-1" />

      <button
        onClick={handleClearHighlights}
        className="w-full text-left px-4 py-2 text-sm text-gray-500 hover:bg-gray-50 transition-colors"
      >
        Clear Highlights
      </button>
    </div>
  );
}

export const ContextMenu = memo(ContextMenuInner);
