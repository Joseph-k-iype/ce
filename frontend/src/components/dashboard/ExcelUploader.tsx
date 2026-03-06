import { useState, useRef } from 'react';
import api from '../../services/api';

// Types
interface LogicNode {
    type: 'AND' | 'OR' | 'CONDITION';
    dimension?: string;
    value?: string;
    children?: LogicNode[];
}

interface ParsedRule {
    rule_id: string;
    name: string;
    rule_type: string;
    outcome: string;
    priority: string;
    required_actions: string[];
    logic_tree: LogicNode | null;
    origin_countries?: string[];
    receiving_countries?: string[];
    valid_until?: string | null;
    requires_pii?: boolean;
    required_assessments?: string[];
    linked_attributes?: string[];
}

/** Download a file from an authenticated endpoint by fetching as a blob. */
async function downloadAuthenticatedFile(url: string, filename: string) {
    const res = await api.get(url, { responseType: 'blob' });
    const blobUrl = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(blobUrl);
}

export function ExcelUploader() {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [downloadingTemplate, setDownloadingTemplate] = useState(false);
    const [downloadingExport, setDownloadingExport] = useState(false);
    const [downloadingJson, setDownloadingJson] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [parsedRules, setParsedRules] = useState<ParsedRule[]>([]);
    const [success, setSuccess] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setParsedRules([]);
            setError(null);
            setSuccess(false);
        }
    };

    const handleParse = async () => {
        if (!file) return;
        setLoading(true);
        setError(null);
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await api.post('/admin/rules/parse-excel', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            // parse-excel returns {rules, upserted, parsed, total}
            setParsedRules(res.data.rules || []);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Failed to parse file');
        } finally {
            setLoading(false);
        }
    };

    const handlePush = async () => {
        if (!parsedRules.length) return;
        setLoading(true);
        setError(null);
        try {
            await api.post('/admin/rules/bulk-insert', parsedRules);
            setSuccess(true);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Failed to push rules');
        } finally {
            setLoading(false);
        }
    };

    const clearState = () => {
        setFile(null);
        setParsedRules([]);
        setSuccess(false);
        setError(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const summarizeLogic = (node: LogicNode | null): string => {
        if (!node) return 'None';
        if (node.type === 'CONDITION') return `${node.dimension}: ${node.value}`;
        if (node.children) {
            const sub = node.children.map(summarizeLogic).join(` ${node.type} `);
            return `(${sub})`;
        }
        return '';
    };

    return (
        <div className="h-full flex flex-col space-y-6">
            {/* Upload Section */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Step 1: Upload Excel/CSV Template</h2>
                <div className="flex items-center gap-4">
                    <input
                        type="file"
                        accept=".csv, .xlsx, .xls"
                        onChange={handleFileChange}
                        ref={fileInputRef}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-medium file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
                    />
                    <button
                        onClick={handleParse}
                        disabled={!file || loading}
                        className="px-6 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 min-w-[120px]"
                    >
                        {loading && !parsedRules.length ? 'Parsing...' : 'Parse File'}
                    </button>

                    <span className="text-gray-300 font-light mx-2">|</span>

                    <button
                        onClick={async () => {
                            setDownloadingTemplate(true);
                            try {
                                await downloadAuthenticatedFile('/admin/rules/template', 'rules_template.xlsx');
                            } catch {
                                setError('Failed to download template');
                            } finally {
                                setDownloadingTemplate(false);
                            }
                        }}
                        disabled={downloadingTemplate}
                        className="px-6 py-2 bg-purple-50 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-100 border border-purple-100 shadow-sm disabled:opacity-50"
                    >
                        {downloadingTemplate ? 'Downloading…' : 'Download Template'}
                    </button>
                    <button
                        onClick={async () => {
                            setDownloadingExport(true);
                            try {
                                await downloadAuthenticatedFile('/admin/rules/export', 'rules_export.xlsx');
                            } catch {
                                setError('Failed to export rules');
                            } finally {
                                setDownloadingExport(false);
                            }
                        }}
                        disabled={downloadingExport}
                        className="px-6 py-2 bg-white text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 border border-gray-200 shadow-sm disabled:opacity-50"
                    >
                        {downloadingExport ? 'Exporting…' : 'Export Excel'}
                    </button>
                    <button
                        onClick={async () => {
                            setDownloadingJson(true);
                            try {
                                await downloadAuthenticatedFile('/admin/export/full', 'compliance_export.json');
                            } catch {
                                setError('Failed to export JSON');
                            } finally {
                                setDownloadingJson(false);
                            }
                        }}
                        disabled={downloadingJson}
                        className="px-6 py-2 bg-white text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 border border-gray-200 shadow-sm disabled:opacity-50"
                    >
                        {downloadingJson ? 'Exporting…' : 'Export JSON'}
                    </button>
                </div>
                {error && <p className="mt-3 text-sm text-red-600 font-medium">{error}</p>}
            </div>

            {/* Review Section */}
            {parsedRules.length > 0 && !success && (
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm flex-1 flex flex-col overflow-hidden">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-medium text-gray-900">Step 2: Review Generated Logic Trees</h2>
                        <button
                            onClick={handlePush}
                            disabled={loading}
                            className="px-6 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                        >
                            {loading ? 'Pushing...' : `Push ${parsedRules.length} Rules to Graph`}
                        </button>
                    </div>

                    <div className="overflow-auto border border-gray-200 rounded-lg">
                        <table className="min-w-full divide-y divide-gray-200 text-sm">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left font-medium text-gray-500">Rule ID</th>
                                    <th className="px-4 py-3 text-left font-medium text-gray-500">Name</th>
                                    <th className="px-4 py-3 text-left font-medium text-gray-500">Outcome</th>
                                    <th className="px-4 py-3 text-left font-medium text-gray-500">Generated Logic Tree (Condition)</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {parsedRules.map((rule, idx) => (
                                    <tr key={idx} className="hover:bg-gray-50">
                                        <td className="px-4 py-3 font-mono text-xs text-gray-600 truncate max-w-[120px]" title={rule.rule_id}>
                                            {rule.rule_id}
                                        </td>
                                        <td className="px-4 py-3 font-medium text-gray-900">{rule.name}</td>
                                        <td className="px-4 py-3 text-gray-500">
                                            <span className={`px-2 py-1 rounded text-xs font-semibold ${rule.outcome.toLowerCase() === 'permission' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                                {rule.outcome}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 font-mono text-xs text-purple-600 bg-purple-50/50 rounded break-words max-w-md">
                                            {summarizeLogic(rule.logic_tree)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <p className="text-xs text-gray-500 mt-3 flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-purple-500">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
                        </svg>
                        Review the deterministic AND trees generated from your CSV columns. You can refine them to use OR logic in the Visual Builder later.
                    </p>
                </div>
            )}

            {/* Success Banner */}
            {success && (
                <div className="bg-green-50 rounded-xl border border-green-200 p-8 shadow-sm flex flex-col items-center justify-center text-center">
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-8 h-8 text-green-600">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                    </div>
                    <h2 className="text-2xl font-semibold text-green-900 mb-2">Rules Successfully Added!</h2>
                    <p className="text-green-700 mb-6">The logic trees have been committed to the active database.</p>
                    <button
                        onClick={clearState}
                        className="px-6 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                    >
                        Upload Another File
                    </button>
                </div>
            )}
        </div>
    );
}
