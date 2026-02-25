import { useState, useCallback } from 'react';
import { useSchemaStore } from '../../stores/schemaStore';

interface SchemaEditorDialogProps {
  onClose: () => void;
}

export function SchemaEditorDialog({ onClose }: SchemaEditorDialogProps) {
  const addNodeType = useSchemaStore((s) => s.addNodeType);
  const addRelationshipType = useSchemaStore((s) => s.addRelationshipType);
  const lanes = useSchemaStore((s) => s.lanes);
  const nodeTypes = useSchemaStore((s) => s.nodeTypes);

  const [tab, setTab] = useState<'nodeType' | 'relType'>('nodeType');

  // Node type form
  const [ntLabel, setNtLabel] = useState('');
  const [ntLaneId, setNtLaneId] = useState('');
  const [ntNewLaneName, setNtNewLaneName] = useState('');
  const [ntPrimary, setNtPrimary] = useState(false);
  const [ntProperties, setNtProperties] = useState('name, description');
  const [creating, setCreating] = useState(false);

  // Relationship type form
  const [rtType, setRtType] = useState('');
  const [rtFrom, setRtFrom] = useState('Rule');
  const [rtTo, setRtTo] = useState('');

  const useNewLane = ntLaneId === '__new__';

  const handleCreateNodeType = useCallback(async () => {
    if (!ntLabel.trim()) return;
    const laneId = useNewLane ? ntLabel.toLowerCase().replace(/\s+/g, '') : ntLaneId;
    if (!laneId) return;

    setCreating(true);
    try {
      await addNodeType({
        label: ntLabel.trim().replace(/\s+/g, ''),
        laneId,
        laneName: useNewLane ? (ntNewLaneName.trim() || ntLabel.trim()) : undefined,
        properties: ntProperties.split(',').map((p) => p.trim()).filter(Boolean),
        primary: ntPrimary,
      });
      onClose();
    } finally {
      setCreating(false);
    }
  }, [ntLabel, ntLaneId, ntNewLaneName, ntPrimary, ntProperties, useNewLane, addNodeType, onClose]);

  const handleCreateRelType = useCallback(async () => {
    if (!rtType.trim() || !rtTo.trim()) return;
    setCreating(true);
    try {
      await addRelationshipType({
        type: rtType.trim().toUpperCase().replace(/\s+/g, '_'),
        fromLabel: rtFrom,
        toLabel: rtTo,
      });
      onClose();
    } finally {
      setCreating(false);
    }
  }, [rtType, rtFrom, rtTo, addRelationshipType, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl shadow-2xl w-[480px] max-h-[90vh] overflow-y-auto">
        <div className="px-6 pt-5 pb-3 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">Schema Editor</h2>
          <p className="text-xs text-gray-500 mt-0.5">Add new entity types or relationships to the graph</p>
        </div>

        {/* Tab toggle */}
        <div className="flex border-b border-gray-100 px-6">
          <button
            onClick={() => setTab('nodeType')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === 'nodeType'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Node Type
          </button>
          <button
            onClick={() => setTab('relType')}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === 'relType'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Relationship Type
          </button>
        </div>

        <div className="px-6 py-4">
          {tab === 'nodeType' ? (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Label (PascalCase)</label>
                <input
                  type="text"
                  value={ntLabel}
                  onChange={(e) => setNtLabel(e.target.value)}
                  placeholder="e.g. RiskCategory"
                  className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-purple-400 focus:border-purple-400 outline-none"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Lane</label>
                <select
                  value={ntLaneId}
                  onChange={(e) => setNtLaneId(e.target.value)}
                  className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-purple-400 focus:border-purple-400 outline-none"
                >
                  <option value="">Select a lane...</option>
                  {lanes.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.label}
                    </option>
                  ))}
                  <option value="__new__">+ Create New Lane</option>
                </select>
              </div>

              {useNewLane && (
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">New Lane Name</label>
                  <input
                    type="text"
                    value={ntNewLaneName}
                    onChange={(e) => setNtNewLaneName(e.target.value)}
                    placeholder="e.g. Risk Categories"
                    className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-purple-400 focus:border-purple-400 outline-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Properties (comma-separated)</label>
                <input
                  type="text"
                  value={ntProperties}
                  onChange={(e) => setNtProperties(e.target.value)}
                  placeholder="name, description"
                  className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-purple-400 focus:border-purple-400 outline-none"
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input
                  type="checkbox"
                  checked={ntPrimary}
                  onChange={(e) => setNtPrimary(e.target.checked)}
                  className="rounded"
                />
                Primary lane (visible by default)
              </label>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Relationship Type</label>
                <input
                  type="text"
                  value={rtType}
                  onChange={(e) => setRtType(e.target.value)}
                  placeholder="e.g. HAS_RISK_CATEGORY"
                  className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-purple-400 focus:border-purple-400 outline-none"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">From (Source)</label>
                <select
                  value={rtFrom}
                  onChange={(e) => setRtFrom(e.target.value)}
                  className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-purple-400 focus:border-purple-400 outline-none"
                >
                  {nodeTypes.map((nt) => (
                    <option key={nt.label} value={nt.label}>
                      {nt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">To (Target)</label>
                <select
                  value={rtTo}
                  onChange={(e) => setRtTo(e.target.value)}
                  className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-purple-400 focus:border-purple-400 outline-none"
                >
                  <option value="">Select target type...</option>
                  {nodeTypes.map((nt) => (
                    <option key={nt.label} value={nt.label}>
                      {nt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-6 pb-5">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={tab === 'nodeType' ? handleCreateNodeType : handleCreateRelType}
            disabled={creating || (tab === 'nodeType' ? !ntLabel.trim() || (!ntLaneId && !useNewLane) : !rtType.trim() || !rtTo)}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-500 rounded-md hover:bg-purple-600 disabled:opacity-50 transition-colors"
          >
            {creating ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}
