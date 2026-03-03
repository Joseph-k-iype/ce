/**
 * Graph Preview Modal Component
 * ==============================
 * Modal to preview graph data before selection.
 *
 * Features:
 * - Graph metadata (name, type, description)
 * - Node labels and relationship types
 * - Sample nodes (5 items)
 * - Accessible modal with ESC key support
 * - Click outside to close
 */

import { useEffect, useRef } from 'react';

interface GraphPreviewModalProps {
  graphName: string;
  data: {
    graph_name: string;
    graph_type: string;
    description: string;
    node_labels: string[];
    relationship_types: string[];
    sample_nodes: any[];
    node_count: number;
  };
  onClose: () => void;
}

export function GraphPreviewModal({
  data,
  onClose,
}: GraphPreviewModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Handle ESC key press
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Handle click outside modal
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // Focus trap - focus modal on mount
  useEffect(() => {
    modalRef.current?.focus();
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        ref={modalRef}
        className="bg-gray-800 rounded-lg shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden"
        tabIndex={-1}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 id="modal-title" className="text-2xl font-bold text-white">
              {data.graph_name}
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Type: <span className="text-purple-400">{data.graph_type}</span>
              {data.node_count > 0 && (
                <span className="ml-3">
                  Nodes: <span className="text-purple-400">{data.node_count}</span>
                </span>
              )}
            </p>
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Close preview"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Description */}
          {data.description && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
                Description
              </h3>
              <p className="text-white">{data.description}</p>
            </div>
          )}

          {/* Node Labels */}
          {data.node_labels && data.node_labels.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Node Labels ({data.node_labels.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {data.node_labels.map((label) => (
                  <span
                    key={label}
                    className="px-3 py-1.5 bg-blue-500/20 text-blue-300 rounded-md text-sm font-medium border border-blue-500/30"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Relationship Types */}
          {data.relationship_types && data.relationship_types.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Relationship Types ({data.relationship_types.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {data.relationship_types.map((rel) => (
                  <span
                    key={rel}
                    className="px-3 py-1.5 bg-green-500/20 text-green-300 rounded-md text-sm font-medium border border-green-500/30"
                  >
                    {rel}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Sample Nodes */}
          {data.sample_nodes && data.sample_nodes.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Sample Nodes ({data.sample_nodes.length})
              </h3>
              <div className="space-y-3">
                {data.sample_nodes.map((item, idx) => {
                  const node = item.n || item;
                  const labels = node.labels || [];
                  const properties = node.properties || {};

                  return (
                    <div
                      key={idx}
                      className="bg-gray-900/50 rounded-lg p-4 border border-gray-700"
                    >
                      {/* Node labels */}
                      {labels.length > 0 && (
                        <div className="flex gap-2 mb-2">
                          {labels.map((label: string, labelIdx: number) => (
                            <span
                              key={labelIdx}
                              className="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded"
                            >
                              {label}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Node properties */}
                      {Object.keys(properties).length > 0 ? (
                        <div className="space-y-1">
                          {Object.entries(properties).map(([key, value]) => (
                            <div key={key} className="flex items-start gap-2 text-sm">
                              <span className="text-gray-400 min-w-[100px]">
                                {key}:
                              </span>
                              <span className="text-white flex-1">
                                {typeof value === 'object'
                                  ? JSON.stringify(value)
                                  : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 italic">No properties</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Empty state */}
          {(!data.sample_nodes || data.sample_nodes.length === 0) &&
            (!data.node_labels || data.node_labels.length === 0) && (
              <div className="text-center py-8">
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
                <p className="text-gray-400">No preview data available</p>
              </div>
            )}
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors font-medium"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}
