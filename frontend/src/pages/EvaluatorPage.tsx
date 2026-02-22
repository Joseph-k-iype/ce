import { useEffect, useState } from 'react';
import { EvaluatorForm } from '../components/evaluator/EvaluatorForm';
import { EvaluationResult } from '../components/evaluator/EvaluationResult';
import { EvaluationFlowView } from '../components/evaluator/EvaluationFlowView';
import { useSchemaStore } from '../stores/schemaStore';
import { useEvaluationStore } from '../stores/evaluationStore';

type EvaluatorTab = 'form' | 'flow';

export function EvaluatorPage() {
  const [activeTab, setActiveTab] = useState<EvaluatorTab>('form');
  const fetchSchema = useSchemaStore((s) => s.fetchSchema);
  const result = useEvaluationStore((s) => s.result);

  useEffect(() => {
    fetchSchema();
  }, [fetchSchema]);

  // Auto-switch to flow tab when results arrive with graph data
  useEffect(() => {
    if (result?.evaluation_graph?.nodes?.length) {
      setActiveTab('flow');
    }
  }, [result]);

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col">
      <div className="px-6 py-4 flex items-center justify-between border-b border-gray-100 bg-white">
        <h1 className="text-2xl font-bold text-gray-800">Policy Evaluator</h1>

        <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setActiveTab('form')}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'form' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Evaluation Form
          </button>
          <button
            onClick={() => setActiveTab('flow')}
            disabled={!result}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'flow' ? 'bg-white text-gray-900 shadow-sm' :
              !result ? 'text-gray-300 cursor-not-allowed' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Flow Diagram
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'form' ? (
          <div className="h-full overflow-y-auto p-6">
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 max-w-7xl mx-auto">
              <div className="lg:col-span-3">
                <EvaluatorForm />
              </div>
              <div className="lg:col-span-2">
                <EvaluationResult />
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex">
            {/* Flow diagram takes most space */}
            <div className="flex-1 h-full">
              <EvaluationFlowView />
            </div>
            {/* Result summary panel on the right */}
            {result && (
              <div className="w-96 h-full overflow-y-auto border-l border-gray-200 bg-gray-50/50 p-4">
                <EvaluationResult />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
