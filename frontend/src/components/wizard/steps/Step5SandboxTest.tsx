import { useState } from 'react';
import { useWizardStore } from '../../../stores/wizardStore';
import { useDropdownData } from '../../../hooks/useDropdownData';
import { sandboxEvaluate } from '../../../services/wizardApi';
import { LoadingSpinner } from '../../common/LoadingSpinner';
import { ResultsTable } from '../../common/ResultsTable';
import type { RulesEvaluationResponse } from '../../../types/api';

export function Step5SandboxTest() {
  const { sandboxGraphName, sessionId, isProcessing, sandboxTestResults, addSandboxTestResult, clearSandboxTestResults } = useWizardStore();
  const { data: dropdowns } = useDropdownData();

  const [evalForm, setEvalForm] = useState({
    origin_country: '',
    receiving_country: [] as string[],
    pii: false,
    purposes: [] as string[],
    data_categories: [] as string[],
    process_l1: [] as string[],
    process_l2: [] as string[],
    process_l3: [] as string[],
    data_subjects: [] as string[],
    regulators: [] as string[],
    authorities: [] as string[],
    sensitive_data_categories: [] as string[],
    personal_data_names: '' as string,
    metadata_json: '' as string,
  });
  const [evaluating, setEvaluating] = useState(false);
  const [metadataError, setMetadataError] = useState('');
  const [latestResult, setLatestResult] = useState<RulesEvaluationResponse | null>(null);

  if (isProcessing && !sandboxGraphName) {
    return <LoadingSpinner message="Loading rule into sandbox..." />;
  }

  if (!sandboxGraphName) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900">Step 5: Sandbox Test</h3>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-5">
          <p className="text-sm text-purple-800 font-medium">Ready to Load</p>
          <p className="text-sm text-purple-700 mt-1">
            Click "Load Sandbox" to create a temporary sandbox graph and load the rule for testing.
          </p>
        </div>
      </div>
    );
  }

  const purposes = dropdowns?.purpose_of_processing?.length
    ? dropdowns.purpose_of_processing
    : (dropdowns?.purposes || []);

  const handleEvaluate = async () => {
    if (!sessionId) return;
    setMetadataError('');
    setEvaluating(true);
    clearSandboxTestResults();
    setLatestResult(null);
    try {
      // Parse personal_data_names from comma-separated string
      const personalDataNames = evalForm.personal_data_names
        .split(',')
        .map(s => s.trim())
        .filter(Boolean);

      // Parse metadata JSON
      let metadata: Record<string, unknown> = {};
      if (evalForm.metadata_json.trim()) {
        try {
          metadata = JSON.parse(evalForm.metadata_json);
        } catch {
          setMetadataError('Invalid JSON');
          setEvaluating(false);
          return;
        }
      }

      const payload = {
        ...evalForm,
        personal_data_names: personalDataNames,
        metadata,
      };
      delete (payload as Record<string, unknown>).metadata_json;

      const response = await sandboxEvaluate(sessionId, payload);
      // Backend returns { result: RulesEvaluationResponse, results: [...], test_number }
      const evalResult = (response?.result ?? response) as RulesEvaluationResponse;
      setLatestResult(evalResult);
      addSandboxTestResult(response);
    } catch {
      // handled by parent
    }
    setEvaluating(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900">Step 5: Sandbox Test</h3>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full" />
          <span className="text-xs text-green-700 font-medium">Sandbox Ready</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Evaluation Form */}
        <div className="lg:col-span-3 card-dark p-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Origin Country</label>
              <select
                value={evalForm.origin_country}
                onChange={(e) => setEvalForm(f => ({ ...f, origin_country: e.target.value }))}
                className="input-dark text-sm"
              >
                <option value="">Select...</option>
                {(dropdowns?.countries || []).map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Receiving Country</label>
              <select
                multiple
                value={evalForm.receiving_country}
                onChange={(e) => setEvalForm(f => ({ ...f, receiving_country: Array.from(e.target.selectedOptions, o => o.value) }))}
                className="input-dark text-sm h-20"
              >
                {(dropdowns?.countries || []).map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-xs font-semibold text-white cursor-pointer">
              <input
                type="checkbox"
                checked={evalForm.pii}
                onChange={(e) => setEvalForm(f => ({ ...f, pii: e.target.checked }))}
                className="rounded border-gray-600"
              />
              Contains PII
            </label>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Purpose Of Processing</label>
              <select
                multiple
                value={evalForm.purposes}
                onChange={(e) => setEvalForm(f => ({ ...f, purposes: Array.from(e.target.selectedOptions, o => o.value) }))}
                className="input-dark text-sm h-16"
              >
                {purposes.map((p: any) => {
                  const val = typeof p === 'string' ? p : p.name;
                  return <option key={val} value={val}>{val}</option>;
                })}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Data Categories</label>
              <select
                multiple
                value={evalForm.data_categories}
                onChange={(e) => setEvalForm(f => ({ ...f, data_categories: Array.from(e.target.selectedOptions, o => o.value) }))}
                className="input-dark text-sm h-16"
              >
                {(dropdowns?.group_data_categories || []).map(c => {
                  const name = typeof c === 'string' ? c : c.name;
                  const label = typeof c === 'string' ? c : (c.category ? `${c.name} (${c.category})` : c.name);
                  return <option key={name} value={name}>{label}</option>;
                })}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Process L1</label>
              <select multiple value={evalForm.process_l1} onChange={(e) => setEvalForm(f => ({ ...f, process_l1: Array.from(e.target.selectedOptions, o => o.value) }))} className="input-dark text-sm h-14">
                {(dropdowns?.processes?.l1 || []).map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Process L2</label>
              <select multiple value={evalForm.process_l2} onChange={(e) => setEvalForm(f => ({ ...f, process_l2: Array.from(e.target.selectedOptions, o => o.value) }))} className="input-dark text-sm h-14">
                {(dropdowns?.processes?.l2 || []).map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Process L3</label>
              <select multiple value={evalForm.process_l3} onChange={(e) => setEvalForm(f => ({ ...f, process_l3: Array.from(e.target.selectedOptions, o => o.value) }))} className="input-dark text-sm h-14">
                {(dropdowns?.processes?.l3 || []).map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Data Subjects</label>
              <select
                multiple
                value={evalForm.data_subjects}
                onChange={(e) => setEvalForm(f => ({ ...f, data_subjects: Array.from(e.target.selectedOptions, o => o.value) }))}
                className="input-dark text-sm h-16"
              >
                {(dropdowns?.data_subjects || []).map((ds: any) => {
                  const val = typeof ds === 'string' ? ds : ds.name;
                  return <option key={val} value={val}>{val}</option>;
                })}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Sensitive Data Categories</label>
              <select
                multiple
                value={evalForm.sensitive_data_categories}
                onChange={(e) => setEvalForm(f => ({ ...f, sensitive_data_categories: Array.from(e.target.selectedOptions, o => o.value) }))}
                className="input-dark text-sm h-16"
              >
                {(dropdowns?.sensitive_data_categories || []).map((sdc: any) => {
                  const val = typeof sdc === 'string' ? sdc : sdc.name;
                  return <option key={val} value={val}>{val}</option>;
                })}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Regulators</label>
              <select
                multiple
                value={evalForm.regulators}
                onChange={(e) => setEvalForm(f => ({ ...f, regulators: Array.from(e.target.selectedOptions, o => o.value) }))}
                className="input-dark text-sm h-16"
              >
                {(dropdowns?.regulators || []).map((reg: any) => {
                  const val = typeof reg === 'string' ? reg : reg.name;
                  return <option key={val} value={val}>{val}</option>;
                })}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-white mb-1">Authorities</label>
              <select
                multiple
                value={evalForm.authorities}
                onChange={(e) => setEvalForm(f => ({ ...f, authorities: Array.from(e.target.selectedOptions, o => o.value) }))}
                className="input-dark text-sm h-16"
              >
                {(dropdowns?.authorities || []).map((auth: any) => {
                  const val = typeof auth === 'string' ? auth : auth.name;
                  return <option key={val} value={val}>{val}</option>;
                })}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-white mb-1">Personal Data Names</label>
            <input
              value={evalForm.personal_data_names}
              onChange={(e) => setEvalForm(f => ({ ...f, personal_data_names: e.target.value }))}
              placeholder="e.g. medical records, health data, biometric"
              className="input-dark text-sm"
            />
            <p className="text-[10px] text-gray-500 mt-0.5">Comma-separated. Used for attribute keyword matching.</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-white mb-1">Metadata (JSON)</label>
            <textarea
              value={evalForm.metadata_json}
              onChange={(e) => { setEvalForm(f => ({ ...f, metadata_json: e.target.value })); setMetadataError(''); }}
              placeholder='{"data_type": "financial", "sensitivity": "high"}'
              rows={3}
              className={`input-dark text-sm font-mono resize-y ${metadataError ? 'border-red-500' : ''}`}
            />
            {metadataError && <p className="text-[10px] text-red-400 mt-0.5">{metadataError}</p>}
            <p className="text-[10px] text-gray-500 mt-0.5">Free-form JSON metadata for attribute detection.</p>
          </div>

          <button
            type="button"
            onClick={handleEvaluate}
            disabled={evaluating || !evalForm.origin_country}
            className="btn-red w-full"
          >
            {evaluating ? 'Evaluating...' : 'Evaluate Compliance'}
          </button>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 space-y-4">
          {!latestResult && sandboxTestResults.length === 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 text-sm">
              Run an evaluation to see results
            </div>
          )}

          {latestResult && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <ResultsTable result={latestResult} />
            </div>
          )}

          {sandboxTestResults.length > 0 && (
            <div className="text-xs text-gray-500 text-center">
              {sandboxTestResults.length} test(s) run
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
