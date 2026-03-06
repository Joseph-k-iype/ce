import { useState } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { useEditorData } from '../hooks/useEditorData';
import { useEditorStore } from '../stores/editorStore';
import { NodeDetailsSidebar } from '../components/editor/NodeDetailsSidebar';
import { RulesOverviewTable } from '../components/editor/RulesOverviewTable';
import { KanbanBoardView } from '../components/editor/KanbanBoardView';

type EditorView = 'table' | 'kanban';

export function EditorPage() {
  const [view, setView] = useState<EditorView>('table');
  const { isLoading, error } = useEditorData();
  const sidebarNodeId = useEditorStore((s) => s.sidebarNodeId);

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col">
      <div className="px-6 py-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Policy Editor</h1>
        <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setView('table')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              view === 'table' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Rules Table
          </button>
          <button
            onClick={() => setView('kanban')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              view === 'kanban' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Kanban Board
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-6 mb-3 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          Failed to load graph data: {error.message}
        </div>
      )}

      {view === 'table' ? (
        <div className="flex-1 mx-6 mb-4 overflow-y-auto">
          <RulesOverviewTable />
        </div>
      ) : (
        <div className="flex-1 overflow-hidden bg-white flex">
          {isLoading ? (
            <div className="flex items-center justify-center h-full flex-1">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-gray-500">Loading policy graph...</span>
              </div>
            </div>
          ) : (
            <ReactFlowProvider>
              <div className="flex-1 flex overflow-hidden">
                <div className="flex-1 overflow-hidden">
                  <KanbanBoardView />
                </div>
                {sidebarNodeId && <NodeDetailsSidebar />}
              </div>
            </ReactFlowProvider>
          )}
        </div>
      )}
    </div>
  );
}
