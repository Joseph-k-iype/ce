import { memo, useCallback } from 'react';
import { useEditorStore } from '../../stores/editorStore';

export function KanbanContextMenu() {
  const contextMenu = useEditorStore((s) => s.contextMenu);
  const hideContextMenu = useEditorStore((s) => s.hideContextMenu);
  const openSidebar = useEditorStore((s) => s.openSidebar);
  const clearHighlight = useEditorStore((s) => s.clearHighlight);
  const selectNode = useEditorStore((s) => s.selectNode);
  const nodes = useEditorStore((s) => s.visibleNodes);
  const edges = useEditorStore((s) => s.visibleEdges);
  const setHighlight = useEditorStore((s) => s.setHighlight);
  const removeNode = useEditorStore((s) => s.removeNode);

  const handleDetails = useCallback(() => {
    if (contextMenu.nodeId) {
      openSidebar(contextMenu.nodeId);
    }
    hideContextMenu();
  }, [contextMenu.nodeId, openSidebar, hideContextMenu]);

  const handleHighlight = useCallback(() => {
    if (!contextMenu.nodeId) return;
    
    selectNode(contextMenu.nodeId);
    
    const neighborNodeIds = new Set<string>();
    const neighborEdgeIds = new Set<string>();
    
    edges.forEach(edge => {
      if (edge.source === contextMenu.nodeId) {
        neighborNodeIds.add(edge.target);
        neighborEdgeIds.add(edge.id);
      }
      if (edge.target === contextMenu.nodeId) {
        neighborNodeIds.add(edge.source);
        neighborEdgeIds.add(edge.id);
      }
    });
    
    setHighlight(Array.from(neighborNodeIds), Array.from(neighborEdgeIds));
    hideContextMenu();
  }, [contextMenu.nodeId, edges, selectNode, setHighlight, hideContextMenu]);

  const enterAddEdgeMode = useEditorStore((s) => s.enterAddEdgeMode);

  const handleAddEdge = useCallback(() => {
    if (contextMenu.nodeId) {
      enterAddEdgeMode(contextMenu.nodeId);
    }
    hideContextMenu();
  }, [contextMenu.nodeId, enterAddEdgeMode, hideContextMenu]);

  const handleDelete = useCallback(async () => {
    if (!contextMenu.nodeId) return;
    
    const node = nodes.find(n => n.id === contextMenu.nodeId);
    const label = (node?.data as { label?: string })?.label || contextMenu.nodeId;
    
    if (confirm(`Delete node "${label}"?`)) {
      await removeNode(contextMenu.nodeId);
    }
    hideContextMenu();
  }, [contextMenu.nodeId, nodes, removeNode, hideContextMenu]);

  const handleClear = useCallback(() => {
    clearHighlight();
    selectNode('');
    hideContextMenu();
  }, [clearHighlight, selectNode, hideContextMenu]);

  if (!contextMenu.visible) return null;

  return (
    <div
      className="fixed bg-white border border-gray-200 rounded-lg shadow-xl py-1 min-w-[160px]"
      style={{ 
        top: contextMenu.y, 
        left: contextMenu.x,
        zIndex: 1000 
      }}
      onMouseLeave={hideContextMenu}
    >
      <button
        onClick={handleDetails}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition-colors flex items-center gap-2"
      >
        <span className="text-lg">ℹ️</span> Show Details
      </button>
      <button
        onClick={handleHighlight}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition-colors flex items-center gap-2"
      >
        <span className="text-lg">🎯</span> Highlight Path
      </button>
      <button
        onClick={handleAddEdge}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition-colors flex items-center gap-2"
      >
        <span className="text-lg">🔗</span> Add Edge
      </button>
      <div className="h-px bg-gray-100 my-1" />
      <button
        onClick={handleClear}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2"
      >
        <span className="text-lg">🧹</span> Clear Selection
      </button>
      <button
        onClick={handleDelete}
        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center gap-2"
      >
        <span className="text-lg">🗑️</span> Delete Node
      </button>
    </div>
  );
}

export const KanbanContextMenuMemo = memo(KanbanContextMenu);
