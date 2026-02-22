import { create } from 'zustand';
import type {
  EditorNode,
  EditorEdge,
  LaneDefinition,
  ContextMenuState,
  FilterState,
} from '../types/editor';
import { PRIMARY_LANES, EXTRA_LANES } from '../types/editor';
import {
  updateNode as apiUpdateNode,
  deleteNode as apiDeleteNode,
  createNode as apiCreateNode,
  createEdge as apiCreateEdge,
  deleteEdge as apiDeleteEdge,
  getEditorNetwork,
} from '../services/editorApi';

type ViewMode = 'full' | 'focused';

interface EditorState {
  // Graph data (controlled React Flow)
  nodes: EditorNode[];
  edges: EditorEdge[];
  lanes: LaneDefinition[];

  // Derived visible data (materialized to avoid new-reference-per-render)
  visibleNodes: EditorNode[];
  visibleEdges: EditorEdge[];
  visibleLanes: LaneDefinition[];

  // Lane visibility
  visibleLaneIds: Set<string>;

  // Selection
  selectedNodeIds: string[];
  selectedEdgeIds: string[];

  // Context menu
  contextMenu: ContextMenuState;
  showContextMenu: (x: number, y: number, nodeId: string) => void;
  hideContextMenu: () => void;

  // Highlights
  highlightedNodeIds: string[];
  highlightedEdgeIds: string[];
  setHighlight: (nodeIds: string[], edgeIds: string[]) => void;
  clearHighlight: () => void;

  // Sidebar
  sidebarNodeId: string | null;
  openSidebar: (nodeId: string) => void;
  closeSidebar: () => void;

  // Filters
  filters: FilterState;
  setFilter: (key: keyof FilterState, value: string) => void;
  clearFilters: () => void;

  // Loading
  isLoading: boolean;
  error: string | null;

  // Add Edge mode
  addEdgeMode: boolean;
  addEdgeSource: string | null;
  pendingEdgeTarget: string | null;
  enterAddEdgeMode: (sourceId: string) => void;
  exitAddEdgeMode: () => void;
  completeAddEdge: (targetId: string) => void;
  confirmAddEdge: (relationshipType: string) => void;
  cancelPendingEdge: () => void;

  // View mode (progressive loading)
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;

  // Actions
  setGraphData: (nodes: EditorNode[], edges: EditorEdge[], lanes: LaneDefinition[]) => void;
  setNodes: (nodes: EditorNode[]) => void;
  setEdges: (edges: EditorEdge[]) => void;
  updateNodePosition: (nodeId: string, x: number, y: number) => void;
  toggleLaneVisibility: (laneId: string) => void;
  setLaneVisibility: (laneId: string, visible: boolean) => void;
  selectNode: (nodeId: string | null) => void;
  selectEdge: (edgeId: string | null) => void;
  clearSelection: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // CRUD mutations (optimistic updates)
  updateNodeData: (nodeId: string, properties: Record<string, unknown>) => Promise<void>;
  removeNode: (nodeId: string) => Promise<void>;
  addNode: (data: { label: string; type: string; lane: string; properties: Record<string, unknown> }) => Promise<void>;
  removeEdge: (edgeId: string) => Promise<void>;
  addEdge: (data: { source_id: string; target_id: string; relationship_type: string; properties?: Record<string, unknown> }) => Promise<void>;
  refetchGraph: () => Promise<void>;
}

const defaultVisibleLaneIds = new Set([...PRIMARY_LANES, ...EXTRA_LANES].map((l) => l.id));
const allLanes = [...PRIMARY_LANES, ...EXTRA_LANES];
const defaultFilters: FilterState = { country: '', ruleSearch: '', dataCategory: '', process: '' };

function computeVisible(
  nodes: EditorNode[],
  edges: EditorEdge[],
  lanes: LaneDefinition[],
  visibleLaneIds: Set<string>,
  filters: FilterState,
  viewMode: ViewMode = 'full'
) {
  const visibleLanes = lanes
    .filter((l) => visibleLaneIds.has(l.id))
    .sort((a, b) => a.order - b.order);

  // Lane filter
  let visibleNodes = nodes.filter((n) => {
    const lane = (n.data as { lane?: string })?.lane;
    return lane ? visibleLaneIds.has(lane) : true;
  });

  // Progressive loading: in focused mode, only show Rule nodes + 1-hop neighbors
  if (viewMode === 'focused' && nodes.length > 200) {
    const ruleNodeIds = new Set(
      visibleNodes
        .filter((n) => (n.data as { nodeType?: string })?.nodeType === 'Rule')
        .map((n) => n.id)
    );
    const neighborIds = new Set<string>();
    for (const e of edges) {
      if (ruleNodeIds.has(e.source)) neighborIds.add(e.target);
      if (ruleNodeIds.has(e.target)) neighborIds.add(e.source);
    }
    const focusedIds = new Set([...ruleNodeIds, ...neighborIds]);
    visibleNodes = visibleNodes.filter((n) => focusedIds.has(n.id));
  }

  // Text-based filters
  const hasCountryFilter = filters.country.trim().length > 0;
  const hasRuleFilter = filters.ruleSearch.trim().length > 0;
  const hasDataCategoryFilter = filters.dataCategory.trim().length > 0;
  const hasProcessFilter = filters.process.trim().length > 0;

  if (hasCountryFilter || hasRuleFilter || hasDataCategoryFilter || hasProcessFilter) {
    const countryLower = filters.country.toLowerCase();
    const ruleLower = filters.ruleSearch.toLowerCase();
    const dataCatLower = filters.dataCategory.toLowerCase();
    const processLower = filters.process.toLowerCase();

    visibleNodes = visibleNodes.filter((n) => {
      const nodeType = (n.data as { nodeType?: string })?.nodeType;
      const label = ((n.data as { label?: string })?.label || '').toLowerCase();

      if (hasCountryFilter && (nodeType === 'Country' || nodeType === 'CountryGroup')) {
        return label.includes(countryLower);
      }
      if (hasRuleFilter && nodeType === 'Rule') {
        const desc = ((n.data as { description?: string })?.description || '').toLowerCase();
        return label.includes(ruleLower) || desc.includes(ruleLower);
      }
      if (hasDataCategoryFilter && nodeType === 'DataCategory') {
        return label.includes(dataCatLower);
      }
      if (hasProcessFilter && nodeType === 'Process') {
        return label.includes(processLower);
      }
      // Non-filtered node types always visible
      return true;
    });
  }

  const visibleNodeIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = edges.filter(
    (e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)
  );

  return { visibleNodes, visibleEdges, visibleLanes };
}

export const useEditorStore = create<EditorState>((set, get) => ({
  nodes: [],
  edges: [],
  lanes: allLanes,
  visibleNodes: [],
  visibleEdges: [],
  visibleLanes: PRIMARY_LANES.sort((a, b) => a.order - b.order),
  visibleLaneIds: defaultVisibleLaneIds,
  selectedNodeIds: [],
  selectedEdgeIds: [],
  isLoading: false,
  error: null,

  // Context menu
  contextMenu: { visible: false, x: 0, y: 0, nodeId: null },
  showContextMenu: (x, y, nodeId) =>
    set({ contextMenu: { visible: true, x, y, nodeId } }),
  hideContextMenu: () =>
    set({ contextMenu: { visible: false, x: 0, y: 0, nodeId: null } }),

  // Highlights
  highlightedNodeIds: [],
  highlightedEdgeIds: [],
  setHighlight: (nodeIds, edgeIds) =>
    set({ highlightedNodeIds: nodeIds, highlightedEdgeIds: edgeIds }),
  clearHighlight: () =>
    set({ highlightedNodeIds: [], highlightedEdgeIds: [] }),

  // Sidebar
  sidebarNodeId: null,
  openSidebar: (nodeId) => set({ sidebarNodeId: nodeId }),
  closeSidebar: () => set({ sidebarNodeId: null }),

  // Filters
  filters: defaultFilters,
  setFilter: (key, value) =>
    set((state) => {
      const newFilters = { ...state.filters, [key]: value };
      return {
        filters: newFilters,
        ...computeVisible(state.nodes, state.edges, state.lanes, state.visibleLaneIds, newFilters, state.viewMode),
      };
    }),
  clearFilters: () =>
    set((state) => ({
      filters: defaultFilters,
      ...computeVisible(state.nodes, state.edges, state.lanes, state.visibleLaneIds, defaultFilters, state.viewMode),
    })),

  // Add Edge mode
  addEdgeMode: false,
  addEdgeSource: null,
  pendingEdgeTarget: null,
  enterAddEdgeMode: (sourceId) => set({ addEdgeMode: true, addEdgeSource: sourceId }),
  exitAddEdgeMode: () => set({ addEdgeMode: false, addEdgeSource: null, pendingEdgeTarget: null }),
  completeAddEdge: (targetId) => {
    const state = get();
    if (!state.addEdgeSource || state.addEdgeSource === targetId) {
      set({ addEdgeMode: false, addEdgeSource: null, pendingEdgeTarget: null });
      return;
    }
    // Store target and wait for relationship type selection
    set({ addEdgeMode: false, pendingEdgeTarget: targetId });
  },
  confirmAddEdge: (relationshipType) => {
    const state = get();
    if (state.addEdgeSource && state.pendingEdgeTarget && relationshipType.trim()) {
      state.addEdge({
        source_id: state.addEdgeSource,
        target_id: state.pendingEdgeTarget,
        relationship_type: relationshipType.trim(),
      });
    }
    set({ addEdgeSource: null, pendingEdgeTarget: null });
  },
  cancelPendingEdge: () => set({ addEdgeSource: null, pendingEdgeTarget: null }),

  // View mode
  viewMode: 'full',
  setViewMode: (mode) =>
    set((state) => ({
      viewMode: mode,
      ...computeVisible(state.nodes, state.edges, state.lanes, state.visibleLaneIds, state.filters, mode),
    })),

  setGraphData: (nodes, edges, lanes) =>
    set((state) => ({
      nodes,
      edges,
      lanes,
      ...computeVisible(nodes, edges, lanes, state.visibleLaneIds, state.filters, state.viewMode),
    })),

  setNodes: (nodes) =>
    set((state) => ({
      nodes,
      ...computeVisible(nodes, state.edges, state.lanes, state.visibleLaneIds, state.filters, state.viewMode),
    })),

  setEdges: (edges) =>
    set((state) => ({
      edges,
      ...computeVisible(state.nodes, edges, state.lanes, state.visibleLaneIds, state.filters, state.viewMode),
    })),

  updateNodePosition: (nodeId, x, y) =>
    set((state) => {
      const nodes = state.nodes.map((n) =>
        n.id === nodeId ? { ...n, position: { x, y } } : n
      );
      return {
        nodes,
        ...computeVisible(nodes, state.edges, state.lanes, state.visibleLaneIds, state.filters, state.viewMode),
      };
    }),

  toggleLaneVisibility: (laneId) =>
    set((state) => {
      const newSet = new Set(state.visibleLaneIds);
      if (newSet.has(laneId)) {
        newSet.delete(laneId);
      } else {
        newSet.add(laneId);
      }
      return {
        visibleLaneIds: newSet,
        ...computeVisible(state.nodes, state.edges, state.lanes, newSet, state.filters, state.viewMode),
      };
    }),

  setLaneVisibility: (laneId, visible) =>
    set((state) => {
      const newSet = new Set(state.visibleLaneIds);
      if (visible) newSet.add(laneId);
      else newSet.delete(laneId);
      return {
        visibleLaneIds: newSet,
        ...computeVisible(state.nodes, state.edges, state.lanes, newSet, state.filters, state.viewMode),
      };
    }),

  selectNode: (nodeId) =>
    set({ selectedNodeIds: nodeId ? [nodeId] : [], selectedEdgeIds: [] }),

  selectEdge: (edgeId) =>
    set({ selectedEdgeIds: edgeId ? [edgeId] : [], selectedNodeIds: [] }),

  clearSelection: () => set({ selectedNodeIds: [], selectedEdgeIds: [] }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  // CRUD mutations with optimistic updates
  updateNodeData: async (nodeId, properties) => {
    const state = get();
    // Optimistic update
    const nodes = state.nodes.map((n) =>
      n.id === nodeId ? { ...n, data: { ...n.data, ...properties } } : n
    );
    set({
      nodes,
      ...computeVisible(nodes, state.edges, state.lanes, state.visibleLaneIds, state.filters, state.viewMode),
    });
    try {
      await apiUpdateNode(nodeId, properties);
    } catch {
      // On error, refetch full graph
      await get().refetchGraph();
    }
  },

  removeNode: async (nodeId) => {
    const state = get();
    const nodes = state.nodes.filter((n) => n.id !== nodeId);
    const edges = state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
    set({
      nodes,
      edges,
      sidebarNodeId: state.sidebarNodeId === nodeId ? null : state.sidebarNodeId,
      ...computeVisible(nodes, edges, state.lanes, state.visibleLaneIds, state.filters, state.viewMode),
    });
    try {
      await apiDeleteNode(nodeId);
    } catch {
      await get().refetchGraph();
    }
  },

  addNode: async (data) => {
    try {
      const result = await apiCreateNode(data);
      // Refetch to get the real node with proper ID
      if (result) {
        await get().refetchGraph();
      }
    } catch {
      set({ error: 'Failed to create node' });
    }
  },

  removeEdge: async (edgeId) => {
    const state = get();
    const edgeToDelete = state.edges.find((e) => e.id === edgeId);
    const edges = state.edges.filter((e) => e.id !== edgeId);
    set({
      edges,
      ...computeVisible(state.nodes, edges, state.lanes, state.visibleLaneIds, state.filters, state.viewMode),
    });
    try {
      // Extract names from node IDs for the backend
      const srcNode = edgeToDelete ? state.nodes.find(n => n.id === edgeToDelete.source) : null;
      const tgtNode = edgeToDelete ? state.nodes.find(n => n.id === edgeToDelete.target) : null;
      const srcName = (srcNode?.data as { label?: string })?.label || '';
      const tgtName = (tgtNode?.data as { label?: string })?.label || '';
      const relType = (edgeToDelete?.data as { relationship?: string })?.relationship || '';
      await apiDeleteEdge(edgeId, srcName, tgtName, relType);
    } catch {
      await get().refetchGraph();
    }
  },

  addEdge: async (data) => {
    try {
      await apiCreateEdge(data);
      await get().refetchGraph();
    } catch {
      set({ error: 'Failed to create edge' });
    }
  },

  refetchGraph: async () => {
    try {
      set({ isLoading: true });
      const response = await getEditorNetwork();
      const state = get();
      set({
        nodes: response.nodes as EditorNode[],
        edges: response.edges as EditorEdge[],
        lanes: response.lanes as LaneDefinition[],
        isLoading: false,
        ...computeVisible(
          response.nodes as EditorNode[],
          response.edges as EditorEdge[],
          response.lanes as LaneDefinition[],
          state.visibleLaneIds,
          state.filters,
          state.viewMode
        ),
      });
    } catch {
      set({ isLoading: false, error: 'Failed to refresh graph' });
    }
  },
}));
