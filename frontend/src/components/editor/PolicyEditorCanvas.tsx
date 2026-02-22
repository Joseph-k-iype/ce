import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  type NodeChange,
  type EdgeChange,
  type Node,
  type Edge,
  type Connection,
  ConnectionMode,
  applyNodeChanges,
  applyEdgeChanges,
  type NodeTypes,
  type EdgeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useEditorStore } from '../../stores/editorStore';
import { useAutoLayout } from '../../hooks/useAutoLayout';
import { LaneBackground } from './LaneBackground';
import { LaneHeader } from './LaneHeader';
import { EditorToolbar } from './toolbar/EditorToolbar';
import { FilterBar } from './toolbar/FilterBar';
import { ContextMenu } from './ContextMenu';

import { CountryGroupNode } from './nodes/CountryGroupNode';
import { CountryNode } from './nodes/CountryNode';
import { RuleNode } from './nodes/RuleNode';
import { DataCategoryNode } from './nodes/DataCategoryNode';
import { PurposeNode } from './nodes/PurposeNode';
import { GdcNode } from './nodes/GdcNode';
import { ProcessNode } from './nodes/ProcessNode';
import { CaseModuleNode } from './nodes/CaseModuleNode';
import { LaneEdge } from './edges/LaneEdge';
import { computeLaneRanges, NODE_WIDTH } from '../../utils/laneGeometry';

const nodeTypes: NodeTypes = {
  countryGroupNode: CountryGroupNode,
  countryNode: CountryNode,
  ruleNode: RuleNode,
  dataCategoryNode: DataCategoryNode,
  purposeNode: PurposeNode,
  gdcNode: GdcNode,
  processNode: ProcessNode,
  caseModuleNode: CaseModuleNode,
};

const edgeTypes: EdgeTypes = {
  laneEdge: LaneEdge,
};

export function PolicyEditorCanvas() {
  const nodes = useEditorStore((s) => s.visibleNodes);
  const edges = useEditorStore((s) => s.visibleEdges);
  const setNodes = useEditorStore((s) => s.setNodes);
  const setEdges = useEditorStore((s) => s.setEdges);
  const allNodes = useEditorStore((s) => s.nodes);
  const selectNode = useEditorStore((s) => s.selectNode);
  const selectEdge = useEditorStore((s) => s.selectEdge);
  const clearSelection = useEditorStore((s) => s.clearSelection);
  const updateNodePosition = useEditorStore((s) => s.updateNodePosition);
  const visibleLanes = useEditorStore((s) => s.visibleLanes);
  const contextMenu = useEditorStore((s) => s.contextMenu);
  const showContextMenu = useEditorStore((s) => s.showContextMenu);
  const hideContextMenu = useEditorStore((s) => s.hideContextMenu);
  const highlightedNodeIds = useEditorStore((s) => s.highlightedNodeIds);
  const highlightedEdgeIds = useEditorStore((s) => s.highlightedEdgeIds);
  const setHighlight = useEditorStore((s) => s.setHighlight);
  const addEdgeMode = useEditorStore((s) => s.addEdgeMode);
  const addEdgeSource = useEditorStore((s) => s.addEdgeSource);
  const pendingEdgeTarget = useEditorStore((s) => s.pendingEdgeTarget);
  const confirmAddEdge = useEditorStore((s) => s.confirmAddEdge);
  const cancelPendingEdge = useEditorStore((s) => s.cancelPendingEdge);
  const addEdge = useEditorStore((s) => s.addEdge);
  const openSidebar = useEditorStore((s) => s.openSidebar);
  const { runLayout } = useAutoLayout();

  // Relationship type dialog state (for drag-to-connect and toolbar add-edge)
  const [relTypeDialog, setRelTypeDialog] = useState<{ source: string; target: string } | null>(null);
  const [relTypeValue, setRelTypeValue] = useState('LINKED_TO');

  // When the store sets pendingEdgeTarget (from toolbar flow), show the dialog
  useEffect(() => {
    if (pendingEdgeTarget && addEdgeSource) {
      setRelTypeDialog({ source: addEdgeSource, target: pendingEdgeTarget });
      setRelTypeValue('LINKED_TO');
    }
  }, [pendingEdgeTarget, addEdgeSource]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const reactFlowInstanceRef = useRef<any>(null);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const onInit = useCallback((instance: any) => {
    reactFlowInstanceRef.current = instance;
  }, []);

  // Run auto-layout once when data first loads, then fitView after layout
  const dataLoaded = allNodes.length > 0;
  useEffect(() => {
    if (dataLoaded) {
      runLayout().then(() => {
        setTimeout(() => {
          reactFlowInstanceRef.current?.fitView({
            padding: 0.08,
            maxZoom: 0.85,
            minZoom: 0.15,
          });
        }, 100);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataLoaded]);

  // Re-trigger fitView on container resize for responsive aspect ratio
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(() => {
      if (reactFlowInstanceRef.current && dataLoaded) {
        reactFlowInstanceRef.current.fitView({
          padding: 0.08,
          maxZoom: 0.85,
          minZoom: 0.15,
        });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [dataLoaded]);

  const laneRanges = useMemo(() => computeLaneRanges(visibleLanes), [visibleLanes]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const store = useEditorStore.getState();
      const updated = applyNodeChanges(changes, store.nodes as unknown as Node[]);
      setNodes(updated as unknown as typeof store.nodes);
    },
    [setNodes]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const store = useEditorStore.getState();
      const updated = applyEdgeChanges(changes, store.edges as Edge[]);
      setEdges(updated as typeof store.edges);
    },
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: { id: string }) => {
      // If in add-edge mode, handle edge creation
      if (addEdgeMode && addEdgeSource) {
        const store = useEditorStore.getState();
        store.completeAddEdge(node.id);
        return;
      }
      selectNode(node.id);
    },
    [selectNode, addEdgeMode, addEdgeSource]
  );

  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      selectEdge(edge.id);
      setHighlight([edge.source, edge.target], [edge.id]);
    },
    [selectEdge, setHighlight]
  );

  const onPaneClick = useCallback(() => {
    clearSelection();
    hideContextMenu();
    // Exit add-edge mode on pane click
    if (addEdgeMode) {
      useEditorStore.getState().exitAddEdgeMode();
    }
  }, [clearSelection, hideContextMenu, addEdgeMode]);

  // Lock nodes to their assigned lane on drag
  const onNodeDragStop = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const lane = (node.data as { lane?: string })?.lane;
      const assignedLane = laneRanges.find((lr) => lr.id === lane);
      if (assignedLane) {
        const centeredX = assignedLane.xCenter - NODE_WIDTH / 2;
        updateNodePosition(node.id, centeredX, node.position.y);
      } else {
        // Fallback: snap to nearest lane
        const snap = computeLaneRanges(visibleLanes).find((lr) => lr.id === lane);
        if (snap) {
          updateNodePosition(node.id, snap.xCenter - NODE_WIDTH / 2, node.position.y);
        }
      }
    },
    [laneRanges, updateNodePosition, visibleLanes]
  );

  const onNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.preventDefault();
      showContextMenu(event.clientX, event.clientY, node.id);
    },
    [showContextMenu]
  );

  // Drag-to-connect: open relationship type dialog
  const onConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target && connection.source !== connection.target) {
        setRelTypeDialog({ source: connection.source, target: connection.target });
        setRelTypeValue('LINKED_TO');
      }
    },
    []
  );

  const handleRelTypeConfirm = useCallback(() => {
    if (relTypeDialog && relTypeValue.trim()) {
      // If this came from the toolbar pending edge flow, use confirmAddEdge
      if (pendingEdgeTarget) {
        confirmAddEdge(relTypeValue.trim());
      } else {
        addEdge({
          source_id: relTypeDialog.source,
          target_id: relTypeDialog.target,
          relationship_type: relTypeValue.trim(),
        });
      }
    }
    setRelTypeDialog(null);
  }, [relTypeDialog, relTypeValue, addEdge, pendingEdgeTarget, confirmAddEdge]);

  const handleRelTypeCancel = useCallback(() => {
    setRelTypeDialog(null);
    if (pendingEdgeTarget) {
      cancelPendingEdge();
    }
  }, [pendingEdgeTarget, cancelPendingEdge]);

  // Double-click node to open sidebar
  const onNodeDoubleClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      openSidebar(node.id);
    },
    [openSidebar]
  );

  const defaultEdgeOptions = useMemo(
    () => ({
      type: 'laneEdge',
      animated: false,
    }),
    []
  );

  // Compute highlight styles
  const hasHighlight = highlightedNodeIds.length > 0 || highlightedEdgeIds.length > 0;
  const highlightNodeSet = useMemo(() => new Set(highlightedNodeIds), [highlightedNodeIds]);
  const highlightEdgeSet = useMemo(() => new Set(highlightedEdgeIds), [highlightedEdgeIds]);

  const styledNodes = useMemo(() => {
    if (!hasHighlight) return nodes;
    return nodes.map((n) => ({
      ...n,
      style: {
        ...n.style,
        opacity: highlightNodeSet.has(n.id) ? 1 : 0.15,
        transition: 'opacity 0.2s ease',
      },
    }));
  }, [nodes, hasHighlight, highlightNodeSet]);

  const styledEdges = useMemo(() => {
    if (!hasHighlight) return edges;
    return edges.map((e) => ({
      ...e,
      style: {
        ...e.style,
        opacity: highlightEdgeSet.has(e.id) ? 1 : 0.1,
        strokeWidth: highlightEdgeSet.has(e.id) ? 3 : 1,
        transition: 'opacity 0.2s ease, stroke-width 0.2s ease',
      },
    }));
  }, [edges, hasHighlight, highlightEdgeSet]);

  return (
    <div className="flex flex-col h-full">
      <EditorToolbar />
      <FilterBar />
      <div ref={containerRef} className="flex-1 relative">
        <LaneHeader />
        {addEdgeMode && (
          <div className="absolute top-1 left-1/2 -translate-x-1/2 z-20 bg-blue-600 text-white text-xs px-3 py-1 rounded-full shadow">
            Click a target node to create an edge {addEdgeSource ? `from ${addEdgeSource}` : ''} — click canvas to cancel
          </div>
        )}
        <ReactFlow
          nodes={styledNodes as unknown as Node[]}
          edges={styledEdges as unknown as Edge[]}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          onNodeDragStop={onNodeDragStop}
          onNodeContextMenu={onNodeContextMenu}
          onNodeDoubleClick={onNodeDoubleClick}
          onConnect={onConnect}
          connectionMode={ConnectionMode.Loose}
          onInit={onInit}
          defaultEdgeOptions={defaultEdgeOptions}
          minZoom={0.1}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <LaneBackground />
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
          <MiniMap
            nodeStrokeWidth={3}
            pannable
            zoomable
            style={{ bottom: 12, right: 12 }}
          />
          <Controls position="bottom-left" />
        </ReactFlow>
        {contextMenu.visible && <ContextMenu />}

        {/* Relationship type dialog for drag-to-connect */}
        {relTypeDialog && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/20">
            <div className="bg-white rounded-lg shadow-xl p-4 w-72 space-y-3">
              <h3 className="text-sm font-semibold text-gray-900">New Relationship</h3>
              <p className="text-xs text-gray-500">
                {relTypeDialog.source} &rarr; {relTypeDialog.target}
              </p>
              <select
                value={relTypeValue}
                onChange={e => setRelTypeValue(e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
              >
                {[
                  'LINKED_TO', 'HAS_PROCESS', 'HAS_PERMISSION', 'HAS_PROHIBITION',
                  'HAS_DUTY', 'HAS_DATA_CATEGORY', 'HAS_PURPOSE', 'HAS_DATA_SUBJECT',
                  'TRIGGERED_BY_ORIGIN', 'TRIGGERED_BY_RECEIVING',
                  'HAS_REGULATOR', 'HAS_AUTHORITY', 'BELONGS_TO',
                  'HAS_GBGF', 'HAS_SENSITIVE_DATA_CATEGORY', 'CAN_HAVE_DUTY',
                  'BELONGS_TO_GBGF', 'HAS_SUBPROCESS', 'HAS_LEGAL_ENTITY',
                ].map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <div className="flex gap-2">
                <button
                  onClick={handleRelTypeCancel}
                  className="flex-1 px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRelTypeConfirm}
                  className="flex-1 px-3 py-1.5 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
