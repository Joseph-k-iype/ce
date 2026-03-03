import { useState } from 'react';
import { useEditorStore } from '../../stores/editorStore';
import { PRIMARY_LANES, EXTRA_LANES } from '../../types/editor';

interface AddNodeModalProps {
    onClose: () => void;
}

export function AddNodeModal({ onClose }: AddNodeModalProps) {
    const addNode = useEditorStore((s) => s.addNode);

    const [label, setLabel] = useState('');
    const [nodeType, setNodeType] = useState('DataCategory');
    const [lane, setLane] = useState('data');
    const [saving, setSaving] = useState(false);

    // Derive lane from nodeType or allow user to pick
    const allLanes = [...PRIMARY_LANES, ...EXTRA_LANES];

    const handleCreate = async () => {
        if (!label.trim()) {
            alert('Label is required');
            return;
        }
        setSaving(true);
        try {
            await addNode({
                label: label.trim(),
                type: nodeType,
                lane,
                properties: {},
            });
            onClose();
        } catch (err) {
            alert('Failed to create node');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-[1050]" onClick={onClose}>
            <div className="bg-white rounded-xl shadow-2xl p-6 w-96 max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
                <h3 className="text-lg font-bold text-gray-800 mb-4">Add New Entity</h3>

                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-semibold text-gray-600 mb-1">Entity Name / Label</label>
                        <input
                            type="text"
                            value={label}
                            onChange={(e) => setLabel(e.target.value)}
                            placeholder="e.g. Employee Data"
                            className="w-full text-sm border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-purple-400 focus:outline-none"
                            autoFocus
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-600 mb-1">Entity Type</label>
                        <select
                            value={nodeType}
                            onChange={(e) => setNodeType(e.target.value)}
                            className="w-full text-sm border border-gray-300 rounded px-3 py-2 bg-white focus:ring-2 focus:ring-purple-400 focus:outline-none"
                        >
                            <optgroup label="Core">
                                <option value="Rule">Rule</option>
                                <option value="Country">Country</option>
                                <option value="CountryGroup">CountryGroup</option>
                            </optgroup>
                            <optgroup label="Data Dimensions">
                                <option value="DataCategory">Data Category</option>
                                <option value="SensitiveDataCategory">Sensitive Data Category</option>
                                <option value="Purpose">Purpose</option>
                                <option value="Process">Process</option>
                                <option value="GDC">Group Data Category</option>
                                <option value="DataSubject">Data Subject</option>
                            </optgroup>
                            <optgroup label="Organization">
                                <option value="LegalEntity">Legal Entity</option>
                                <option value="Authority">Authority</option>
                                <option value="Regulator">Regulator</option>
                                <option value="GlobalBusinessFunction">Global Business Function</option>
                            </optgroup>
                            <optgroup label="Actions & Duties">
                                <option value="Action">Action</option>
                                <option value="Duty">Duty</option>
                                <option value="Permission">Permission</option>
                                <option value="Prohibition">Prohibition</option>
                            </optgroup>
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-gray-600 mb-1">Visual Lane</label>
                        <select
                            value={lane}
                            onChange={(e) => setLane(e.target.value)}
                            className="w-full text-sm border border-gray-300 rounded px-3 py-2 bg-white focus:ring-2 focus:ring-purple-400 focus:outline-none"
                        >
                            {allLanes.map((l) => (
                                <option key={l.id} value={l.id}>{l.label}</option>
                            ))}
                        </select>
                        <p className="text-[10px] text-gray-500 mt-1">Which column should this appear in?</p>
                    </div>
                </div>

                <div className="mt-6 flex justify-end gap-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={saving || !label.trim()}
                        className="px-4 py-2 text-sm text-white bg-purple-600 hover:bg-purple-700 rounded shadow-sm disabled:opacity-50 transition-colors"
                    >
                        {saving ? 'Creating...' : 'Create Entity'}
                    </button>
                </div>
            </div>
        </div>
    );
}
