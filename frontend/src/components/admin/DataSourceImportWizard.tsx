import { useState, useEffect } from 'react';
import api from '../../services/api';

interface ImportWizardProps {
  sourceId: string;
  sourceName: string;
  onClose: () => void;
  onSuccess: () => void;
}

interface PreviewData {
  columns: string[];
  sample_rows: any[];
  total_count: number;
  data_types: Record<string, string>;
}

export interface NodeMapping {
  id: string;
  node_label: string;
  id_field: string;
  property_mappings: Record<string, string>;
}

export interface RelationshipMapping {
  id: string;
  relationship_type: string;
  source_node_id: string;
  target_node_id: string;
  source_id_field: string;
  target_id_field: string;
  foreign_key_field: string;
  properties: Record<string, string>;
}

export function DataSourceImportWizard({ sourceId, sourceName, onClose, onSuccess }: ImportWizardProps) {
  const [step, setStep] = useState(1);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(false);

  // Step 1: Base Graph Config
  const [graphName, setGraphName] = useState('');
  const [clearExisting, setClearExisting] = useState(false);

  // State: Mappings Data
  const [nodeMappings, setNodeMappings] = useState<NodeMapping[]>([]);
  const [relationshipMappings, setRelationshipMappings] = useState<RelationshipMapping[]>([]);

  // State: Node Building Form
  const [isAddingNode, setIsAddingNode] = useState(false);
  const [newNodeLabel, setNewNodeLabel] = useState('');
  const [newNodeIdField, setNewNodeIdField] = useState('');
  const [newNodeProps, setNewNodeProps] = useState<Record<string, string>>({});

  // State: Relationship Building Form
  const [isAddingRel, setIsAddingRel] = useState(false);
  const [newRelType, setNewRelType] = useState('');
  const [newRelSourceNodeId, setNewRelSourceNodeId] = useState('');
  const [newRelTargetNodeId, setNewRelTargetNodeId] = useState('');
  const [newRelSourceIdField, setNewRelSourceIdField] = useState('');
  const [newRelForeignKey, setNewRelForeignKey] = useState('');

  // Import Execution
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);

  useEffect(() => {
    fetchPreview();
  }, [sourceId]);

  const fetchPreview = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/data-sources/${sourceId}/preview?limit=100`);
      setPreview(response.data.preview);
    } catch (error) {
      console.error('Failed to fetch preview:', error);
    } finally {
      setLoading(false);
    }
  };

  // --- Node Mapping Logic ---
  const handleAddNode = () => {
    if (!newNodeLabel || !newNodeIdField) return;

    setNodeMappings([...nodeMappings, {
      id: Math.random().toString(36).substring(7),
      node_label: newNodeLabel,
      id_field: newNodeIdField,
      property_mappings: { ...newNodeProps }
    }]);

    setIsAddingNode(false);
    setNewNodeLabel('');
    setNewNodeIdField('');
    setNewNodeProps({});
  };

  const removeNode = (id: string) => {
    setNodeMappings(nodeMappings.filter(n => n.id !== id));
    // Also remove relations that depended on this node
    setRelationshipMappings(relationshipMappings.filter(r => r.source_node_id !== id && r.target_node_id !== id));
  };

  const toggleNodeProperty = (column: string) => {
    setNewNodeProps(prev => {
      const next = { ...prev };
      if (next[column]) {
        delete next[column];
      } else {
        next[column] = column;
      }
      return next;
    });
  };

  // --- Rel Mapping Logic ---
  const handleAddRel = () => {
    if (!newRelType || !newRelSourceNodeId || !newRelTargetNodeId || !newRelSourceIdField || !newRelForeignKey) return;

    // Find the actual nodes to get their internal ID fields
    const sourceNode = nodeMappings.find(n => n.id === newRelSourceNodeId);
    const targetNode = nodeMappings.find(n => n.id === newRelTargetNodeId);

    if (!sourceNode || !targetNode) return;

    setRelationshipMappings([...relationshipMappings, {
      id: Math.random().toString(36).substring(7),
      relationship_type: newRelType,
      source_node_id: newRelSourceNodeId,
      target_node_id: newRelTargetNodeId,
      source_id_field: newRelSourceIdField,
      target_id_field: targetNode.id_field, // target_id_field is defining what property exists on the target node
      foreign_key_field: newRelForeignKey,
      properties: {}
    }]);

    setIsAddingRel(false);
    setNewRelType('');
    setNewRelSourceNodeId('');
    setNewRelTargetNodeId('');
    setNewRelSourceIdField('');
    setNewRelForeignKey('');
  };

  const removeRel = (id: string) => {
    setRelationshipMappings(relationshipMappings.filter(r => r.id !== id));
  };

  // --- Import Logic ---
  const handleImport = async () => {
    setImporting(true);
    try {
      const nodeMappingsPayload = nodeMappings.map(n => ({
        node_label: n.node_label,
        id_field: n.id_field,
        property_mappings: n.property_mappings
      }));

      const relMappingsPayload = relationshipMappings.map(r => {
        const sourceNode = nodeMappings.find(n => n.id === r.source_node_id);
        const targetNode = nodeMappings.find(n => n.id === r.target_node_id);

        return {
          relationship_type: r.relationship_type,
          source_node_label: sourceNode?.node_label || '',
          target_node_label: targetNode?.node_label || '',
          source_id_field: r.source_id_field,
          target_id_field: r.target_id_field,
          foreign_key_field: r.foreign_key_field,
          properties: r.properties
        };
      });

      const response = await api.post('/data-sources/import', {
        source_id: sourceId,
        graph_name: graphName,
        node_mappings: nodeMappingsPayload,
        relationship_mappings: relMappingsPayload,
        clear_existing: clearExisting
      });

      setImportResult(response.data);
      setStep(5);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const renderProgress = () => (
    <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
      <div className="flex items-center justify-between text-xs font-medium text-gray-500 mb-2 px-1">
        <span className={step >= 1 ? 'text-purple-600' : ''}>1. Preview</span>
        <span className={step >= 2 ? 'text-purple-600' : ''}>2. Nodes</span>
        <span className={step >= 3 ? 'text-purple-600' : ''}>3. Relationships</span>
        <span className={step >= 4 ? 'text-purple-600' : ''}>4. Execute</span>
      </div>
      <div className="flex items-center gap-2">
        {[1, 2, 3, 4].map(s => (
          <div key={s} className={`flex-1 h-2 rounded-full ${s <= step ? 'bg-purple-600' : 'bg-gray-300'}`} />
        ))}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />

      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[95vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Map Data to Graph</h2>
              <p className="text-sm text-gray-500 mt-0.5">Source: {sourceName}</p>
            </div>
            <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {step < 5 && renderProgress()}

          {/* Wrapper for scrolling content */}
          <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
            {/* Step 1: Preview Data & Target Graph */}
            {step === 1 && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Target Graph Configuration</h3>
                  <div className="grid grid-cols-2 gap-6 bg-white p-4 rounded-xl border border-gray-200">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Graph Database Name *</label>
                      <input
                        type="text"
                        value={graphName}
                        onChange={e => setGraphName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                        placeholder="e.g., Compliance_KG"
                      />
                      <p className="text-xs text-gray-500 mt-1">Provide a unique name for this graph.</p>
                    </div>
                    <div className="flex items-center">
                      <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg w-full">
                        <input
                          type="checkbox"
                          checked={clearExisting}
                          onChange={e => setClearExisting(e.target.checked)}
                          className="w-4 h-4 text-red-600 rounded border-gray-300"
                        />
                        <label className="text-sm font-medium text-red-900">
                          Clear existing data in graph completely
                        </label>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Flat Data Preview</h3>
                  {loading ? (
                    <div className="flex justify-center py-8"><div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div></div>
                  ) : preview ? (
                    <div className="overflow-x-auto border border-gray-200 rounded-lg shadow-sm bg-white">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                          <tr>
                            {preview.columns.map(col => (
                              <th key={col} className="px-4 py-3 text-left font-semibold text-gray-700 whitespace-nowrap">
                                {col}
                                <span className="text-xs text-gray-400 font-normal ml-1 border border-gray-200 rounded px-1">
                                  {preview.data_types[col]}
                                </span>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {preview.sample_rows.slice(0, 5).map((row, i) => (
                            <tr key={i} className="hover:bg-gray-50">
                              {preview.columns.map(col => (
                                <td key={col} className="px-4 py-2 text-gray-600 whitespace-nowrap">
                                  {row[col] !== null ? String(row[col]) : <span className="text-gray-300 italic">null</span>}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-gray-500 p-4">No preview data available</div>
                  )}
                </div>
              </div>
            )}

            {/* Step 2: Node Mappings */}
            {step === 2 && preview && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Extract Node Entities</h3>
                    <p className="text-sm text-gray-500">Define which columns convert into standalone graph Nodes.</p>
                  </div>
                  {!isAddingNode && (
                    <button
                      onClick={() => setIsAddingNode(true)}
                      className="px-4 py-2 bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg font-medium flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                      Add Node Mapping
                    </button>
                  )}
                </div>

                {isAddingNode && (
                  <div className="bg-white border-2 border-purple-200 shadow-md rounded-xl p-6">
                    <h4 className="font-semibold text-purple-900 mb-4 border-b pb-2">New Node Mapping</h4>

                    <div className="grid grid-cols-2 gap-6 mb-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Graph Node Label *</label>
                        <input
                          type="text"
                          value={newNodeLabel}
                          onChange={e => setNewNodeLabel(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                          placeholder="e.g., Customer, Product"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Unique ID Column *</label>
                        <select
                          value={newNodeIdField}
                          onChange={e => setNewNodeIdField(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500"
                        >
                          <option value="">-- Select Column --</option>
                          {preview.columns.map(col => <option key={col} value={col}>{col}</option>)}
                        </select>
                      </div>
                    </div>

                    <div className="mb-6">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Properties to Attach to Node (Optional)</label>
                      <div className="grid grid-cols-3 gap-3 border border-gray-200 bg-gray-50 p-4 rounded-lg max-h-60 overflow-y-auto">
                        {preview.columns.map(col => (
                          <label key={col} className="flex items-center gap-2 p-2 hover:bg-gray-100 rounded cursor-pointer">
                            <input
                              type="checkbox"
                              checked={!!newNodeProps[col]}
                              onChange={() => toggleNodeProperty(col)}
                              className="w-4 h-4 text-purple-600 rounded"
                            />
                            <span className="text-sm text-gray-700 truncate">{col}</span>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-end gap-3">
                      <button onClick={() => setIsAddingNode(false)} className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">Cancel</button>
                      <button
                        onClick={handleAddNode}
                        disabled={!newNodeLabel || !newNodeIdField}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                      >
                        Save Node Configuration
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {nodeMappings.length === 0 && !isAddingNode && (
                    <div className="text-center py-12 bg-white border border-gray-200 border-dashed rounded-xl">
                      <p className="text-gray-500">No nodes defined yet. You must define at least one node to import anything.</p>
                      <button onClick={() => setIsAddingNode(true)} className="mt-4 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">Add Node First</button>
                    </div>
                  )}

                  {nodeMappings.map(node => (
                    <div key={node.id} className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl shadow-sm">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center font-bold">
                          {node.node_label.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">{node.node_label}</h4>
                          <p className="text-sm text-gray-500">ID mapping to <strong>{node.id_field}</strong> • {Object.keys(node.property_mappings).length} properties attached</p>
                        </div>
                      </div>
                      <button onClick={() => removeNode(node.id)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Step 3: Relationship Mappings */}
            {step === 3 && preview && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">Define Relationships (Edges)</h3>
                    <p className="text-sm text-gray-500">Connect your extracted node entities together using foreign keys found in the same row.</p>
                  </div>
                  {!isAddingRel && nodeMappings.length >= 1 && (
                    <button
                      onClick={() => setIsAddingRel(true)}
                      className="px-4 py-2 bg-indigo-100 text-indigo-700 hover:bg-indigo-200 rounded-lg font-medium flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                      Add Relationship
                    </button>
                  )}
                </div>

                {isAddingRel && (
                  <div className="bg-white border-2 border-indigo-200 shadow-md rounded-xl p-6">
                    <h4 className="font-semibold text-indigo-900 mb-4 border-b pb-2">New Relationship Edge</h4>

                    <div className="grid grid-cols-[1fr,auto,1fr] gap-4 items-center mb-6">
                      {/* Source */}
                      <div className="bg-gray-50 p-4 border border-gray-200 rounded-lg">
                        <label className="block text-sm font-medium text-gray-700 mb-2">1. Source Node</label>
                        <select
                          value={newRelSourceNodeId}
                          onChange={e => {
                            setNewRelSourceNodeId(e.target.value);
                            const source = nodeMappings.find(n => n.id === e.target.value);
                            if (source) setNewRelSourceIdField(source.id_field); // Default to the source's natural ID field
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500"
                        >
                          <option value="">-- Source Entity --</option>
                          {nodeMappings.map(n => <option key={n.id} value={n.id}>{n.node_label}</option>)}
                        </select>

                        {newRelSourceNodeId && (
                          <div className="mt-3">
                            <label className="block text-xs font-medium text-gray-500 mb-1">Row Column mapped to Source ID</label>
                            <select
                              value={newRelSourceIdField}
                              onChange={e => setNewRelSourceIdField(e.target.value)}
                              className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-indigo-500"
                            >
                              <option value="">-- Column --</option>
                              {preview.columns.map(col => <option key={col} value={col}>{col}</option>)}
                            </select>
                          </div>
                        )}
                      </div>

                      {/* Edge Label */}
                      <div className="flex flex-col items-center">
                        <label className="block text-sm font-medium text-gray-700 mb-2">2. Action / Verb</label>
                        <input
                          type="text"
                          value={newRelType}
                          onChange={e => setNewRelType(e.target.value.toUpperCase().replace(/\s+/g, '_'))}
                          className="w-48 px-3 py-2 border-2 border-indigo-300 rounded-full text-center font-mono focus:ring-indigo-500 focus:border-indigo-500"
                          placeholder="e.g. LIVES_IN"
                        />
                        <svg className="w-6 h-6 text-indigo-400 mt-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                      </div>

                      {/* Target */}
                      <div className="bg-gray-50 p-4 border border-gray-200 rounded-lg">
                        <label className="block text-sm font-medium text-gray-700 mb-2">3. Target Node</label>
                        <select
                          value={newRelTargetNodeId}
                          onChange={e => setNewRelTargetNodeId(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-indigo-500"
                        >
                          <option value="">-- Target Entity --</option>
                          {nodeMappings.map(n => <option key={n.id} value={n.id}>{n.node_label}</option>)}
                        </select>

                        {newRelTargetNodeId && (
                          <div className="mt-3">
                            <label className="block text-xs font-medium text-gray-500 mb-1">Row Column mapped to Target ID (FOREIGN KEY)</label>
                            <select
                              value={newRelForeignKey}
                              onChange={e => setNewRelForeignKey(e.target.value)}
                              className="w-full px-2 py-1 text-sm border border-gray-300 rounded outline-none focus:ring-indigo-500 bg-yellow-50 border-yellow-300"
                            >
                              <option value="">-- Foreign Key Column --</option>
                              {preview.columns.map(col => <option key={col} value={col}>{col}</option>)}
                            </select>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex justify-end gap-3 mt-4">
                      <button onClick={() => setIsAddingRel(false)} className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">Cancel</button>
                      <button
                        onClick={handleAddRel}
                        disabled={!newRelType || !newRelSourceNodeId || !newRelTargetNodeId || !newRelSourceIdField || !newRelForeignKey}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                      >
                        Save Relationship Edge
                      </button>
                    </div>
                  </div>
                )}

                <div className="space-y-3">
                  {nodeMappings.length < 2 && relationshipMappings.length === 0 && (
                    <div className="text-sm p-3 bg-blue-50 text-blue-800 rounded-lg">
                      Tip: You usually need at least 2 node entity blocks defined to create meaningful relationships between them. For example, a `Customer` node mapping and a `Country` node mapping.
                    </div>
                  )}
                  {relationshipMappings.map(rel => {
                    const src = nodeMappings.find(n => n.id === rel.source_node_id);
                    const tgt = nodeMappings.find(n => n.id === rel.target_node_id);
                    return (
                      <div key={rel.id} className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl shadow-sm">
                        <div className="flex items-center gap-4">
                          <div className="flex items-center text-sm font-medium text-gray-800">
                            <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-lg">{src?.node_label}</span>
                            <span className="mx-2 text-gray-400">({rel.source_id_field})</span>
                            <span className="mx-2 text-indigo-400">---[</span>
                            <span className="font-mono text-indigo-600 font-bold">{rel.relationship_type}</span>
                            <span className="mx-2 text-indigo-400">]--&gt;</span>
                            <span className="mx-2 text-gray-400">({rel.foreign_key_field})</span>
                            <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-lg">{tgt?.node_label}</span>
                          </div>
                        </div>
                        <button onClick={() => removeRel(rel.id)} className="p-2 text-red-500 hover:bg-red-50 rounded-lg">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Step 4: Import Review */}
            {step === 4 && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900 text-center">Ready to Synthesize Graph</h3>

                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-white border text-center border-purple-200 rounded-xl p-6 shadow-sm">
                    <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mx-auto mb-3 text-2xl font-bold">
                      {nodeMappings.length}
                    </div>
                    <h4 className="font-semibold text-gray-900">Node Types to Generate</h4>
                    <p className="text-sm text-gray-500 mt-1">Found in every row</p>
                  </div>
                  <div className="bg-white border text-center border-indigo-200 rounded-xl p-6 shadow-sm">
                    <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-3 text-2xl font-bold">
                      {relationshipMappings.length}
                    </div>
                    <h4 className="font-semibold text-gray-900">Relationship Types to Form</h4>
                    <p className="text-sm text-gray-500 mt-1">Connecting the data network</p>
                  </div>
                </div>

                <div className="text-center pt-6">
                  <p className="text-sm text-gray-600 mb-4">
                    Graph mapping will process {preview?.total_count || 0} rows into {graphName}.
                  </p>
                  <button
                    onClick={handleImport}
                    disabled={importing}
                    className="w-full max-w-sm mx-auto px-6 py-4 bg-purple-600 text-white font-medium text-lg rounded-xl hover:bg-purple-700 disabled:bg-gray-400 flex items-center justify-center gap-3 transition-colors shadow-lg"
                  >
                    {importing ? (
                      <><div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" /> Synthesizing Graph...</>
                    ) : (
                      <><svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> Execute Import</>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* Step 5: Success */}
            {step === 5 && importResult && (
              <div className="space-y-6 text-center py-8">
                <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto shadow-sm">
                  <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                </div>

                <div>
                  <h3 className="text-2xl font-bold text-gray-900">Data Network Synthesized!</h3>
                  <p className="text-gray-600 mt-2">Nodes and relationships have been successfully injected into FalkorDB.</p>
                </div>

                <div className="max-w-md mx-auto grid grid-cols-2 gap-4 mt-8">
                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                    <dt className="text-sm font-medium text-gray-500">Nodes Generated</dt>
                    <dd className="text-3xl font-bold text-purple-600 mt-1">{importResult.stats?.nodes_created || 0}</dd>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                    <dt className="text-sm font-medium text-gray-500">Edges Created</dt>
                    <dd className="text-3xl font-bold text-indigo-600 mt-1">{importResult.stats?.relationships_created || 0}</dd>
                  </div>
                  <div className="col-span-2 pt-2 text-xs text-gray-400">
                    Execution time: {importResult.stats?.duration_ms || 0}ms
                  </div>
                </div>

                <div className="pt-8">
                  <button onClick={() => { onSuccess(); onClose(); }} className="px-8 py-3 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700">Go to Graph Dashboard</button>
                </div>
              </div>
            )}
          </div>

          {/* Footer Navigation */}
          {step < 5 && (
            <div className="flex items-center justify-between px-6 py-4 bg-white border-t border-gray-200 rounded-b-xl">
              <button
                onClick={() => {
                  if (step > 1) setStep(step - 1);
                  else onClose();
                }}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
              >
                {step === 1 ? 'Cancel' : 'Back'}
              </button>

              {step < 4 && (
                <button
                  onClick={() => setStep(step + 1)}
                  disabled={
                    (step === 1 && (!graphName)) ||
                    (step === 2 && nodeMappings.length === 0)
                  }
                  className="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-black disabled:opacity-50 font-medium"
                >
                  Continue to {step === 1 ? 'Nodes' : step === 2 ? 'Relationships' : 'Review'} →
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
