/**
 * Graph Suggestion Card Component
 * =================================
 * Displays individual graph suggestion with relevance score, matched entities, and preview.
 *
 * Features:
 * - Color-coded relevance badges (green >70%, yellow >40%, gray <40%)
 * - Matched entity tags
 * - Checkbox for selection
 * - Preview button
 * - Reasoning text
 */



interface GraphSuggestionCardProps {
  graph: {
    graph_name: string;
    relevance_score: number;
    reasoning: string;
    matched_entities: Record<string, string[]>;
    sample_data: any[];
    node_count: number;
  };
  selected: boolean;
  onToggle: () => void;
  onPreview: () => void;
}

export function GraphSuggestionCard({
  graph,
  selected,
  onToggle,
  onPreview,
}: GraphSuggestionCardProps) {
  const scorePercentage = Math.round(graph.relevance_score * 100);

  // Color-coded badge based on relevance score
  const getBadgeColor = (score: number): string => {
    if (score >= 0.7) return 'bg-green-500/20 text-green-300 border-green-500/30';
    if (score >= 0.4) return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
    return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
  };

  const getScoreLabel = (score: number): string => {
    if (score >= 0.7) return 'High Match';
    if (score >= 0.4) return 'Medium Match';
    return 'Low Match';
  };

  return (
    <div
      className={`border rounded-lg p-4 transition-all ${selected
          ? 'border-purple-500 bg-purple-500/10 shadow-md'
          : 'border-gray-600 bg-gray-800/50 hover:border-gray-500'
        }`}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="mt-1 w-4 h-4 rounded border-gray-400 text-purple-600 focus:ring-purple-500 focus:ring-offset-gray-900"
          aria-label={`Select ${graph.graph_name}`}
        />

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header: Graph name + Relevance badge */}
          <div className="flex items-start justify-between gap-3 mb-2">
            <div>
              <h5 className="text-base font-semibold text-white mb-1">
                {graph.graph_name}
              </h5>
              <p className="text-sm text-gray-400">{graph.reasoning}</p>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <span
                className={`text-xs px-2.5 py-1 rounded-full border font-medium ${getBadgeColor(
                  graph.relevance_score
                )}`}
              >
                {scorePercentage}% {getScoreLabel(graph.relevance_score)}
              </span>
            </div>
          </div>

          {/* Matched Entities */}
          {Object.keys(graph.matched_entities).length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-1.5">Matched Entities:</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(graph.matched_entities).map(([dimension, values]) =>
                  values.map((value) => (
                    <span
                      key={`${dimension}-${value}`}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 text-xs"
                    >
                      <span className="text-indigo-400 font-medium">
                        {dimension.replace(/_/g, ' ')}:
                      </span>
                      {value}
                    </span>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Node count */}
          {graph.node_count > 0 && (
            <p className="text-xs text-gray-500 mb-2">
              Contains {graph.node_count} nodes
            </p>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={onPreview}
              className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
              aria-label={`Preview ${graph.graph_name}`}
            >
              <svg
                className="w-4 h-4 inline mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                />
              </svg>
              Preview Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
