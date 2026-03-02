/**
 * Step 3.5: Graph Selection Component
 * =====================================
 * Allows users to select external data source graphs for precedent search.
 *
 * Features:
 * - AI-suggested graphs with relevance scores
 * - Manual graph selection
 * - Graph preview modal
 * - Conditional display (only shows if external graphs exist or AI detects relevance)
 * - Auto-save on selection changes
 */

import { useState, useEffect } from 'react';
import { useWizardStore } from '../../../stores/wizardStore';
import {
  getGraphSuggestions,
  getAvailableGraphs,
  configureGraphs,
} from '../../../services/wizardApi';
import { GraphSuggestionCard } from '../GraphSuggestionCard';
import { GraphPreviewModal } from '../GraphPreviewModal';

interface GraphSuggestion {
  graph_name: string;
  relevance_score: number;
  reasoning: string;
  matched_entities: Record<string, string[]>;
  sample_data: any[];
  node_count: number;
}

interface AvailableGraph {
  name: string;
  graph_type: string;
  description: string;
  node_labels: string[];
  relationship_types: string[];
  enabled: boolean;
}

export function Step3GraphSelection() {
  const { sessionId } = useWizardStore();

  // State
  const [suggestions, setSuggestions] = useState<GraphSuggestion[]>([]);
  const [allGraphs, setAllGraphs] = useState<AvailableGraph[]>([]);
  const [selectedGraphs, setSelectedGraphs] = useState<string[]>(['DataTransferGraph']);
  const [previewGraph, setPreviewGraph] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [confidence, setConfidence] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch graph suggestions and available graphs on mount
  useEffect(() => {
    if (!sessionId) return;

    const fetchGraphData = async () => {
      try {
        setLoading(true);
        setError(null);

        const [suggestionsRes, graphsRes] = await Promise.all([
          getGraphSuggestions(sessionId),
          getAvailableGraphs(sessionId),
        ]);

        setSuggestions(suggestionsRes.relevant_graphs || []);
        setConfidence(suggestionsRes.confidence || 0);
        setAllGraphs(graphsRes.available_graphs || []);
        setSelectedGraphs(graphsRes.current_selection || ['DataTransferGraph']);
      } catch (err: any) {
        console.error('Failed to load graph data:', err);
        setError(err?.message || 'Failed to load graph data');
      } finally {
        setLoading(false);
      }
    };

    fetchGraphData();
  }, [sessionId]);

  // Toggle graph selection
  const toggleGraph = async (graphName: string) => {
    const newSelection = selectedGraphs.includes(graphName)
      ? selectedGraphs.filter((g) => g !== graphName)
      : [...selectedGraphs, graphName];

    setSelectedGraphs(newSelection);

    // Auto-save selection
    if (sessionId) {
      try {
        setSaving(true);
        await configureGraphs(sessionId, newSelection);
      } catch (err) {
        console.error('Failed to save graph selection:', err);
      } finally {
        setSaving(false);
      }
    }
  };

  // Preview graph
  const handlePreview = async (graphName: string) => {
    try {
      setLoadingPreview(true);
      const response = await fetch(`/api/graphs/${graphName}/preview`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load preview');
      }

      const data = await response.json();
      setPreviewData(data);
      setPreviewGraph(graphName);
    } catch (err) {
      console.error('Failed to load preview:', err);
      setError('Failed to load preview');
    } finally {
      setLoadingPreview(false);
    }
  };

  // Close preview modal
  const closePreview = () => {
    setPreviewGraph(null);
    setPreviewData(null);
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <svg
            className="animate-spin h-8 w-8 text-purple-500 mx-auto mb-3"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <p className="text-gray-400">Loading graph suggestions...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="card-dark p-6">
        <div className="flex items-start gap-3 text-red-400">
          <svg
            className="w-5 h-5 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <p className="font-semibold">Error Loading Graphs</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-2xl font-bold text-white mb-2">
          Step 3.5: Select Data Sources
        </h3>
        <p className="text-gray-300 text-sm">
          Choose which external data sources to query for precedent cases and compliance
          insights. The system will search these graphs for similar scenarios during rule
          evaluation.
        </p>
      </div>

      {/* AI Recommendations Section */}
      {suggestions.length > 0 && (
        <div className="card-dark p-6">
          <div className="flex items-center gap-2 mb-4">
            <svg
              className="w-5 h-5 text-purple-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            <h4 className="text-lg font-semibold text-white">AI Recommendations</h4>
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                confidence >= 0.7
                  ? 'bg-green-500/20 text-green-300'
                  : confidence >= 0.4
                  ? 'bg-yellow-500/20 text-yellow-300'
                  : 'bg-gray-500/20 text-gray-300'
              }`}
            >
              {Math.round(confidence * 100)}% confidence
            </span>
            {saving && (
              <span className="text-xs text-gray-500 ml-auto">Saving...</span>
            )}
          </div>

          <p className="text-sm text-gray-400 mb-4">
            Based on your rule text and extracted entities, these graphs may contain
            relevant precedent data:
          </p>

          <div className="space-y-3">
            {suggestions.map((graph) => (
              <GraphSuggestionCard
                key={graph.graph_name}
                graph={graph}
                selected={selectedGraphs.includes(graph.graph_name)}
                onToggle={() => toggleGraph(graph.graph_name)}
                onPreview={() => handlePreview(graph.graph_name)}
              />
            ))}
          </div>
        </div>
      )}

      {/* All Available Graphs Section */}
      <div className="card-dark p-6">
        <h4 className="text-lg font-semibold text-white mb-4">
          All Available Data Sources
        </h4>

        {allGraphs.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <svg
              className="w-12 h-12 mx-auto text-gray-600 mb-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
              />
            </svg>
            <p className="font-medium mb-1">No external data sources found</p>
            <p className="text-sm">
              Import data from CSV, JSON, or JDBC to create precedent graphs that can be
              searched during rule evaluation.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {allGraphs
              .filter((g) => g.graph_type !== 'rules') // Exclude system graphs from manual selection
              .map((graph) => (
                <div
                  key={graph.name}
                  className={`border rounded-lg p-3 flex items-center gap-3 transition-all ${
                    selectedGraphs.includes(graph.name)
                      ? 'border-purple-500 bg-purple-500/10'
                      : 'border-gray-600 hover:border-gray-500'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedGraphs.includes(graph.name)}
                    onChange={() => toggleGraph(graph.name)}
                    className="w-4 h-4 rounded border-gray-400 text-purple-600 focus:ring-purple-500"
                    aria-label={`Select ${graph.name}`}
                  />
                  <div className="flex-1">
                    <div className="font-medium text-white">{graph.name}</div>
                    <div className="text-xs text-gray-400">{graph.description}</div>
                  </div>
                  <button
                    onClick={() => handlePreview(graph.name)}
                    disabled={loadingPreview}
                    className="text-xs text-purple-400 hover:text-purple-300 transition-colors disabled:opacity-50"
                  >
                    Preview
                  </button>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Selection Summary */}
      {selectedGraphs.length > 0 && (
        <div className="card-dark p-4 bg-purple-500/10 border-purple-500/30">
          <p className="text-sm text-gray-300">
            <span className="font-semibold text-purple-300">
              {selectedGraphs.length}
            </span>{' '}
            graph{selectedGraphs.length !== 1 ? 's' : ''} selected for precedent search:
            <span className="ml-2 text-purple-400">
              {selectedGraphs.join(', ')}
            </span>
          </p>
        </div>
      )}

      {/* Preview Modal */}
      {previewGraph && previewData && (
        <GraphPreviewModal
          graphName={previewGraph}
          data={previewData}
          onClose={closePreview}
        />
      )}
    </div>
  );
}
