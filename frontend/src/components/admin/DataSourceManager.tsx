/**
 * DataSourceManager Component
 *
 * Manages external data source connections for importing data to graphs.
 * Supports JDBC databases, REST APIs, CSV, JSON, and more.
 */

import { useState, useEffect } from 'react';
import api from '../../services/api';
import { DataSourceCreateWizard } from './DataSourceCreateWizard';
import { DataSourceImportWizard } from './DataSourceImportWizard';

type DataSourceType = 'jdbc' | 'rest_api' | 'csv' | 'json' | 'graphql';

interface DataSource {
  source_id: string;
  name: string;
  source_type: DataSourceType;
  description: string;
  enabled: boolean;
  created_at: string;
}

export function DataSourceManager() {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateWizard, setShowCreateWizard] = useState(false);
  const [importSource, setImportSource] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const response = await api.get('/data-sources/list');
      setSources(response.data.sources || []);
    } catch (error) {
      console.error('Failed to fetch data sources:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (sourceId: string) => {
    if (!confirm('Are you sure you want to delete this data source?')) return;

    try {
      await api.delete(`/data-sources/${sourceId}`);
      fetchSources();
    } catch (error) {
      console.error('Failed to delete data source:', error);
      alert('Failed to delete data source');
    }
  };

  const getTypeColor = (type: DataSourceType) => {
    const colors = {
      jdbc: 'bg-indigo-100 text-indigo-800 border-indigo-300',
      rest_api: 'bg-blue-100 text-blue-800 border-blue-300',
      csv: 'bg-green-100 text-green-800 border-green-300',
      json: 'bg-purple-100 text-purple-800 border-purple-300',
      graphql: 'bg-orange-100 text-orange-800 border-orange-300',
    };
    return colors[type] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  const getTypeIcon = (type: DataSourceType) => {
    const icons = {
      jdbc: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
      ),
      rest_api: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
        </svg>
      ),
      csv: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      json: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      ),
      graphql: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
    };
    return icons[type] || null;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Data Source Connections</h2>
          <p className="text-sm text-gray-600 mt-1">
            Connect external data sources (APIs, databases, files) and import to graphs
          </p>
        </div>
        <button
          onClick={() => setShowCreateWizard(true)}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Data Source
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-4 border-gray-300 border-t-purple-600 rounded-full animate-spin" />
        </div>
      )}

      {/* Empty State */}
      {!loading && sources.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-300">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No data sources</h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by creating a new data source connection.
          </p>
          <div className="mt-6">
            <button
              onClick={() => setShowCreateWizard(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-purple-600 hover:bg-purple-700"
            >
              <svg className="mr-2 -ml-1 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Data Source
            </button>
          </div>
        </div>
      )}

      {/* Data Sources Grid */}
      {!loading && sources.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sources.map(source => (
            <div
              key={source.source_id}
              className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-shadow"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${getTypeColor(source.source_type)}`}>
                    {getTypeIcon(source.source_type)}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{source.name}</h3>
                    <span className={`inline-block mt-1 px-2 py-0.5 text-xs rounded-full border ${getTypeColor(source.source_type)}`}>
                      {source.source_type.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Description */}
              {source.description && (
                <p className="text-sm text-gray-600 mb-4">{source.description}</p>
              )}

              {/* Metadata */}
              <div className="text-xs text-gray-500 mb-4">
                Created {new Date(source.created_at).toLocaleDateString()}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setImportSource({ id: source.source_id, name: source.name })}
                  className="flex-1 px-3 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 transition-colors"
                >
                  Import to Graph
                </button>
                <button
                  onClick={() => handleDelete(source.source_id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete source"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Data Source Creation Wizard */}
      {showCreateWizard && (
        <DataSourceCreateWizard
          onClose={() => setShowCreateWizard(false)}
          onSuccess={() => {
            setShowCreateWizard(false);
            fetchSources(); // Refresh the list
          }}
        />
      )}

      {/* Data Source Import Wizard */}
      {importSource && (
        <DataSourceImportWizard
          sourceId={importSource.id}
          sourceName={importSource.name}
          onClose={() => setImportSource(null)}
          onSuccess={() => {
            setImportSource(null);
            // Optionally refresh or show success message
          }}
        />
      )}
    </div>
  );
}
