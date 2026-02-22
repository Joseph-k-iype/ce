import { useState, useCallback, useEffect } from 'react';
import { useEditorStore } from '../../stores/editorStore';
import { useSchemaStore } from '../../stores/schemaStore';

// Fallback options used when schema hasn't loaded yet
const FALLBACK_NODE_TYPE_OPTIONS = [
  { type: 'Rule', lane: 'rule', label: 'Rule' },
  { type: 'DataCategory', lane: 'dataCategory', label: 'Data Category' },
  { type: 'Purpose', lane: 'purpose', label: 'Purpose' },
  { type: 'Process', lane: 'processes', label: 'Process' },
  { type: 'Duty', lane: 'caseModule', label: 'Duty (TIA/PIA/HRPR)' },
  { type: 'GDC', lane: 'gdc', label: 'GDC' },
  { type: 'Country', lane: 'originCountry', label: 'Country' },
  { type: 'LegalEntity', lane: 'legalEntity', label: 'Legal Entity' },
  { type: 'DataSubject', lane: 'dataSubject', label: 'Data Subject' },
  { type: 'Attribute', lane: 'attribute', label: 'Attribute' },
];

interface AddNodeDialogProps {
  onClose: () => void;
}

export function AddNodeDialog({ onClose }: AddNodeDialogProps) {
  const addNode = useEditorStore((s) => s.addNode);
  const schemaNodeTypeOptions = useSchemaStore((s) => s.nodeTypeOptions);
  const fetchSchema = useSchemaStore((s) => s.fetchSchema);
  const schemaLoaded = useSchemaStore((s) => s.schema !== null);

  // Fetch schema on mount if not yet loaded
  useEffect(() => {
    if (!schemaLoaded) fetchSchema();
  }, [schemaLoaded, fetchSchema]);

  const NODE_TYPE_OPTIONS = schemaNodeTypeOptions.length > 0 ? schemaNodeTypeOptions : FALLBACK_NODE_TYPE_OPTIONS;
  const [selectedType, setSelectedType] = useState(NODE_TYPE_OPTIONS[0]);
  const [label, setLabel] = useState('');
  const [creating, setCreating] = useState(false);

  const handleCreate = useCallback(async () => {
    if (!label.trim()) return;
    setCreating(true);
    try {
      await addNode({
        label: label.trim(),
        type: selectedType.type,
        lane: selectedType.lane,
        properties: { name: label.trim() },
      });
      onClose();
    } finally {
      setCreating(false);
    }
  }, [label, selectedType, addNode, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-xl shadow-2xl w-96 p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Add Node</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Node Type</label>
            <select
              value={selectedType.type}
              onChange={(e) => {
                const opt = NODE_TYPE_OPTIONS.find((o) => o.type === e.target.value);
                if (opt) setSelectedType(opt);
              }}
              className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-blue-400 focus:border-blue-400 outline-none"
            >
              {NODE_TYPE_OPTIONS.map((opt) => (
                <option key={opt.type} value={opt.type}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Label</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Enter node label..."
              className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-blue-400 focus:border-blue-400 outline-none"
              autoFocus
            />
          </div>

          <div className="text-xs text-gray-400">
            Lane: <span className="font-medium text-gray-600">{selectedType.lane}</span>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!label.trim() || creating}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
          >
            {creating ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}
