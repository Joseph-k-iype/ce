import { memo, useState, useEffect } from 'react';
import { useReactFlow } from '@xyflow/react';
import { useEditorStore } from '../../../stores/editorStore';
import { useSchemaStore } from '../../../stores/schemaStore';
import { useAutoLayout } from '../../../hooks/useAutoLayout';
import { EXTRA_LANES } from '../../../types/editor';
import { AddNodeDialog } from '../AddNodeDialog';
import { SchemaEditorDialog } from '../SchemaEditorDialog';

function EditorToolbarInner() {
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const { runLayout } = useAutoLayout();
  const visibleLaneIds = useEditorStore((s) => s.visibleLaneIds);
  const toggleLaneVisibility = useEditorStore((s) => s.toggleLaneVisibility);
  const nodes = useEditorStore((s) => s.nodes);
  const edges = useEditorStore((s) => s.edges);
  const viewMode = useEditorStore((s) => s.viewMode);
  const setViewMode = useEditorStore((s) => s.setViewMode);
  const enterAddEdgeMode = useEditorStore((s) => s.enterAddEdgeMode);

  const schemaExtraLanes = useSchemaStore((s) => s.extraLanes);
  const fetchSchema = useSchemaStore((s) => s.fetchSchema);
  const schemaLoaded = useSchemaStore((s) => s.schema !== null);

  const [showAddNode, setShowAddNode] = useState(false);
  const [showSchemaEditor, setShowSchemaEditor] = useState(false);

  // Fetch schema on mount if not yet loaded
  useEffect(() => {
    if (!schemaLoaded) fetchSchema();
  }, [schemaLoaded, fetchSchema]);

  // Use schema-driven extra lanes when available, fall back to hardcoded
  const displayExtraLanes = schemaExtraLanes.length > 0
    ? schemaExtraLanes.map((l) => ({ id: l.id, label: l.label }))
    : EXTRA_LANES.map((l) => ({ id: l.id, label: l.label }));

  const handleAutoLayout = async () => {
    await runLayout();
    setTimeout(() => fitView({ padding: 0.08, maxZoom: 0.85, duration: 300 }), 100);
  };

  const handleAddEdge = () => {
    enterAddEdgeMode('');
  };

  return (
    <>
      <div className="flex items-center gap-3 px-4 py-2 bg-white border-b border-gray-200 flex-wrap">
        {/* Graph stats */}
        <div className="text-xs text-gray-500 mr-2">
          {nodes.length} nodes &middot; {edges.length} edges
        </div>

        <div className="h-5 w-px bg-gray-200" />

        {/* Layout controls */}
        <button
          onClick={handleAutoLayout}
          className="px-3 py-1.5 text-xs font-medium text-white bg-blue-500 rounded-md hover:bg-blue-600 transition-colors"
        >
          Auto Layout
        </button>
        <button
          onClick={() => fitView({ padding: 0.08, maxZoom: 0.85, duration: 300 })}
          className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
        >
          Fit View
        </button>
        <button
          onClick={() => zoomIn({ duration: 200 })}
          className="px-2 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
        >
          +
        </button>
        <button
          onClick={() => zoomOut({ duration: 200 })}
          className="px-2 py-1.5 text-xs font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
        >
          −
        </button>

        <div className="h-5 w-px bg-gray-200" />

        {/* CRUD controls */}
        <button
          onClick={() => setShowAddNode(true)}
          className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-md hover:bg-green-100 transition-colors"
        >
          + Node
        </button>
        <button
          onClick={handleAddEdge}
          className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
        >
          + Edge
        </button>
        <button
          onClick={() => setShowSchemaEditor(true)}
          className="px-3 py-1.5 text-xs font-medium text-purple-700 bg-purple-50 border border-purple-200 rounded-md hover:bg-purple-100 transition-colors"
        >
          Schema
        </button>

        <div className="h-5 w-px bg-gray-200" />

        {/* Progressive loading toggle */}
        {nodes.length > 200 && (
          <>
            <button
              onClick={() => setViewMode(viewMode === 'full' ? 'focused' : 'full')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                viewMode === 'focused'
                  ? 'bg-purple-100 text-purple-700 border-purple-200'
                  : 'bg-gray-100 text-gray-600 border-gray-200 hover:bg-gray-200'
              }`}
            >
              {viewMode === 'focused' ? 'Expand All' : 'Focus Rules'}
            </button>
            <div className="h-5 w-px bg-gray-200" />
          </>
        )}

        {/* Lane visibility toggles */}
        <span className="text-xs text-gray-500">Lanes:</span>
        <div className="flex items-center gap-1.5 flex-wrap">
          {displayExtraLanes.map((lane) => {
            const active = visibleLaneIds.has(lane.id);
            return (
              <button
                key={lane.id}
                onClick={() => toggleLaneVisibility(lane.id)}
                className={`px-2 py-1 text-[10px] font-medium rounded-full border transition-colors ${
                  active
                    ? 'bg-gray-800 text-white border-gray-800'
                    : 'bg-white text-gray-500 border-gray-300 hover:border-gray-400'
                }`}
              >
                {lane.label}
              </button>
            );
          })}
        </div>
      </div>

      {showAddNode && <AddNodeDialog onClose={() => setShowAddNode(false)} />}
      {showSchemaEditor && <SchemaEditorDialog onClose={() => setShowSchemaEditor(false)} />}
    </>
  );
}

export const EditorToolbar = memo(EditorToolbarInner);
