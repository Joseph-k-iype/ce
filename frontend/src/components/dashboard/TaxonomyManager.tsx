import { useState, useRef, useEffect } from 'react';
import Select from 'react-select';
import CreatableSelect from 'react-select/creatable';
import api from '../../services/api';
import { useDropdownData } from '../../hooks/useDropdownData';
import { LoadingSpinner } from '../common/LoadingSpinner';

const DICT_OPTIONS = [
    { value: 'countries', label: 'Countries' },
    { value: 'country_groups', label: 'Country Groups' },
    { value: 'legal_entities', label: 'Legal Entities' },
    { value: 'gdc', label: 'GDC (Data Categories Level 3)' },
    { value: 'data_categories', label: 'Data Categories' },
    { value: 'sensitive_data_categories', label: 'Sensitive Data Categories' },
    { value: 'data_subjects', label: 'Data Subjects' },
    { value: 'purposes', label: 'Purpose of Processing' },
    { value: 'processes', label: 'Processes' },
    { value: 'regulators', label: 'Regulators' },
    { value: 'authorities', label: 'Authorities' },
    { value: 'global_business_functions', label: 'Global Business Functions' },
];

export function TaxonomyManager() {
    const [activeTab, setActiveTab] = useState<'upload' | 'mapping' | 'backup'>('upload');

    // Backup State
    const [backupLoading, setBackupLoading] = useState(false);
    const [backupMessage, setBackupMessage] = useState({ text: '', type: '' });

    // Upload State
    const [file, setFile] = useState<File | null>(null);
    const [dictType, setDictType] = useState(DICT_OPTIONS[0]);
    const [uploadLoading, setUploadLoading] = useState(false);
    const [uploadMessage, setUploadMessage] = useState({ text: '', type: '' });
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Mapping State
    const { data: dropdowns, isLoading: loadingDropdowns } = useDropdownData();
    const [mappingType, setMappingType] = useState<'country-group' | 'legal-entity'>('country-group');
    const [selectedDestination, setSelectedDestination] = useState<any>(null);
    const [selectedSources, setSelectedSources] = useState<any[]>([]);
    const [mappingLoading, setMappingLoading] = useState(false);
    const [mappingMessage, setMappingMessage] = useState({ text: '', type: '' });
    const [existingMappings, setExistingMappings] = useState<Record<string, string[]>>({});

    // Fetch mappings when mapping type changes
    useEffect(() => {
        if (activeTab === 'mapping') {
            fetchMappings();
            setSelectedDestination(null);
            setSelectedSources([]);
        }
    }, [activeTab, mappingType]);

    // Update selected sources when destination changes
    useEffect(() => {
        if (selectedDestination) {
            const sources = existingMappings[selectedDestination.value] || [];
            setSelectedSources(sources.map((s: string) => ({ value: s, label: s })));
        } else {
            setSelectedSources([]);
        }
    }, [selectedDestination, existingMappings]);

    const fetchMappings = async () => {
        try {
            const res = await api.get(`/admin/mappings/${mappingType}`);
            const mapObj: Record<string, string[]> = {};
            res.data.mappings.forEach((m: any) => {
                mapObj[m.source] = m.targets;
            });
            setExistingMappings(mapObj);
        } catch (err) {
            console.error("Failed to fetch mappings", err);
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploadLoading(true);
        setUploadMessage({ text: '', type: '' });

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.post(`/admin/dictionaries/${dictType.value}/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setUploadMessage({ text: `Successfully inserted ${res.data.inserted} entities.`, type: 'success' });
            setFile(null);
            if (fileInputRef.current) fileInputRef.current.value = '';
        } catch (err: any) {
            setUploadMessage({
                text: err.response?.data?.detail || err.message || 'Failed to upload dictionary',
                type: 'error'
            });
        } finally {
            setUploadLoading(false);
        }
    };

    const handleDownloadSample = async () => {
        try {
            const res = await api.get(`/admin/dictionaries/${dictType.value}/template`, {
                responseType: 'blob',
            });
            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${dictType.value}_sample.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (err: any) {
            setUploadMessage({
                text: 'Failed to download sample',
                type: 'error'
            });
        }
    };

    const handleSaveMapping = async () => {
        if (!selectedDestination) return;
        setMappingLoading(true);
        setMappingMessage({ text: '', type: '' });

        try {
            await api.post(`/admin/mappings/${mappingType}`, {
                source_id: selectedDestination.value,
                target_ids: selectedSources.map(s => s.value)
            });
            setMappingMessage({ text: 'Mapping saved successfully', type: 'success' });
            await fetchMappings();
        } catch (err: any) {
            setMappingMessage({
                text: err.response?.data?.detail || err.message || 'Failed to save mapping',
                type: 'error'
            });
        } finally {
            setMappingLoading(false);
        }
    };

    const handleCreateBackup = async () => {
        setBackupLoading(true);
        setBackupMessage({ text: '', type: '' });
        try {
            const res = await api.post('/admin/backup/create');
            setBackupMessage({ text: `Backup created: ${res.data.node_count} nodes, ${res.data.edge_count} edges`, type: 'success' });
        } catch (err: any) {
            setBackupMessage({ text: err.response?.data?.detail || 'Failed to create backup', type: 'error' });
        } finally {
            setBackupLoading(false);
        }
    };

    const handleRestoreBackup = async () => {
        if (!window.confirm('Are you sure you want to restore the rule graph? This will overwrite existing data with the latest backup.')) return;
        setBackupLoading(true);
        setBackupMessage({ text: '', type: '' });
        try {
            await api.post('/admin/backup/restore');
            setBackupMessage({ text: 'Backup restored successfully.', type: 'success' });
        } catch (err: any) {
            setBackupMessage({ text: err.response?.data?.detail || 'Failed to restore backup', type: 'error' });
        } finally {
            setBackupLoading(false);
        }
    };

    if (loadingDropdowns) return <LoadingSpinner />;

    // Prepare dropdown options
    const targetOptions = mappingType === 'country-group'
        ? (dropdowns?.country_groups || []).map((g: string) => ({ value: g, label: g }))
        : (dropdowns?.countries || []).map((c: string) => ({ value: c, label: c }));
    const sourceOptions = mappingType === 'country-group'
        ? (dropdowns?.countries || []).map((c: string) => ({ value: c, label: c }))
        : Object.values(dropdowns?.legal_entities || {}).flat().map((l: string) => ({ value: l, label: l }));

    return (
        <div className="h-full flex flex-col space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-lg font-bold text-gray-900 tracking-tight">Taxonomy Manager</h2>
                    <p className="text-sm text-gray-500 mt-1">
                        Bulk load data dictionaries and manage core entity relationships.
                    </p>
                </div>
                <div className="flex bg-slate-100 p-1 rounded-lg">
                    <button
                        onClick={() => setActiveTab('upload')}
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'upload' ? 'bg-white shadow text-red-700' : 'text-slate-600 hover:text-red-600'
                            }`}
                    >
                        Dictionary Upload
                    </button>
                    <button
                        onClick={() => setActiveTab('mapping')}
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'mapping' ? 'bg-white shadow text-red-700' : 'text-slate-600 hover:text-red-600'
                            }`}
                    >
                        Entity Mappings
                    </button>
                    <button
                        onClick={() => setActiveTab('backup')}
                        className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'backup' ? 'bg-white shadow text-red-700' : 'text-slate-600 hover:text-red-600'
                            }`}
                    >
                        Graph Backups
                    </button>
                </div>
            </div>

            {activeTab === 'upload' ? (
                <div className="bg-white border rounded-xl p-6 shadow-sm flex-1">
                    <h3 className="text-md font-semibold text-gray-800 mb-4">Bulk Import CSV</h3>

                    <div className="max-w-xl space-y-5">
                        <div>
                            <div className="flex justify-between items-end mb-1.5">
                                <label className="block text-sm font-medium text-gray-700">
                                    Select Dictionary Domain
                                </label>
                                <button
                                    onClick={handleDownloadSample}
                                    className="text-xs text-red-600 hover:text-red-800 font-medium"
                                >
                                    Download Sample CSV
                                </button>
                            </div>
                            <Select
                                options={DICT_OPTIONS}
                                value={dictType}
                                onChange={(val) => setDictType(val as any)}
                                className="text-sm"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                CSV File
                            </label>
                            <div className="flex items-center gap-3">
                                <input
                                    type="file"
                                    accept=".csv"
                                    ref={fileInputRef}
                                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                                    className="block w-full text-sm text-gray-500
                                        file:mr-4 file:py-2 file:px-4
                                        file:rounded-md file:border-0
                                        file:text-sm file:font-semibold
                                        file:bg-red-50 file:text-red-700
                                        hover:file:bg-red-100 transition-colors cursor-pointer"
                                />
                            </div>
                        </div>

                        {uploadMessage.text && (
                            <div className={`p-3 rounded-lg text-sm ${uploadMessage.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                                {uploadMessage.text}
                            </div>
                        )}

                        <button
                            onClick={handleUpload}
                            disabled={!file || uploadLoading}
                            className="w-full py-2.5 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {uploadLoading ? 'Uploading...' : `Upload to ${dictType.label}`}
                        </button>
                    </div>
                </div>
            ) : activeTab === 'mapping' ? (
                <div className="bg-white border rounded-xl p-6 shadow-sm flex-1">
                    <h3 className="text-md font-semibold text-gray-800 mb-4">Manage Entity Relationships</h3>

                    <div className="max-w-xl space-y-6">
                        <div className="flex gap-4">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    checked={mappingType === 'country-group'}
                                    onChange={() => setMappingType('country-group')}
                                    className="text-red-600 focus:ring-red-500"
                                />
                                <span className="text-sm font-medium text-gray-700">Country → Country Group</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="radio"
                                    checked={mappingType === 'legal-entity'}
                                    onChange={() => setMappingType('legal-entity')}
                                    className="text-red-600 focus:ring-red-500"
                                />
                                <span className="text-sm font-medium text-gray-700">Country → Legal Entity</span>
                            </label>
                        </div>

                        <div className="p-5 border border-red-100 bg-red-50/30 rounded-lg space-y-4">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
                                    Target {mappingType === 'country-group' ? 'Group' : 'Country'}
                                </label>
                                {mappingType === 'country-group' ? (
                                    <CreatableSelect
                                        options={targetOptions}
                                        value={selectedDestination}
                                        onChange={(val) => setSelectedDestination(val)}
                                        placeholder="Select or type to create a target group..."
                                        className="text-sm"
                                        formatCreateLabel={(inputValue) => `Create new group "${inputValue}"`}
                                    />
                                ) : (
                                    <Select
                                        options={targetOptions}
                                        value={selectedDestination}
                                        onChange={(val) => setSelectedDestination(val)}
                                        placeholder="Select target country..."
                                        className="text-sm"
                                    />
                                )}
                            </div>

                            <div className="relative">
                                <div className="absolute left-[1.1rem] -top-2 w-0.5 h-6 bg-red-200"></div>
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
                                    {mappingType === 'country-group' ? 'Source Countries' : 'Legal Entities'}
                                </label>
                                <Select
                                    isMulti
                                    options={sourceOptions}
                                    value={selectedSources}
                                    onChange={(val) => setSelectedSources(val as any)}
                                    placeholder={mappingType === 'country-group' ? "Select multiple source countries to link..." : "Select multiple legal entities to link..."}
                                    className="text-sm"
                                />
                            </div>
                        </div>

                        {mappingMessage.text && (
                            <div className={`p-3 rounded-lg text-sm ${mappingMessage.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                                {mappingMessage.text}
                            </div>
                        )}

                        <button
                            onClick={handleSaveMapping}
                            disabled={!selectedDestination || mappingLoading}
                            className="w-full py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-colors"
                        >
                            {mappingLoading ? 'Saving...' : 'Save Mapping'}
                        </button>
                    </div>
                </div>
            ) : (
                <div className="bg-white border rounded-xl p-6 shadow-sm flex-1">
                    <h3 className="text-md font-semibold text-gray-800 mb-4">Graph Backups</h3>
                    <div className="max-w-xl space-y-5">
                        <p className="text-sm text-gray-600">
                            The system automatically takes complete layout backups of the Rules Graph every 30 minutes in the background.
                            You can also trigger a manual backup off-schedule here, or restore from the latest disk snapshot.
                        </p>

                        <div className="flex gap-4 border-t pt-5">
                            <button
                                onClick={handleCreateBackup}
                                disabled={backupLoading}
                                className="flex-1 py-2.5 bg-gray-800 text-white rounded-lg text-sm font-medium hover:bg-gray-900 disabled:opacity-50 transition-colors"
                            >
                                {backupLoading ? 'Working...' : 'Create Snapshot'}
                            </button>
                            <button
                                onClick={handleRestoreBackup}
                                disabled={backupLoading}
                                className="flex-1 py-2.5 bg-red-50 text-red-600 border border-red-200 rounded-lg text-sm font-medium hover:bg-red-100 disabled:opacity-50 transition-colors"
                            >
                                {backupLoading ? 'Working...' : 'Restore from Disk'}
                            </button>
                        </div>

                        {backupMessage.text && (
                            <div className={`p-3 rounded-lg text-sm ${backupMessage.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                                {backupMessage.text}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
