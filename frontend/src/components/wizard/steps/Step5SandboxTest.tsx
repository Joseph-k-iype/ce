import { useState } from 'react';
import { useWizardStore } from '../../../stores/wizardStore';
import { useDropdownData } from '../../../hooks/useDropdownData';
import { sandboxEvaluate } from '../../../services/wizardApi';
import { LoadingSpinner } from '../../common/LoadingSpinner';
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
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
          <p className="text-sm text-blue-800 font-medium">Ready to Load</p>
          <p className="text-sm text-blue-700 mt-1">
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
            <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
              {/* Transfer Status Banner */}
              <div className={`rounded-lg p-3 ${latestResult.transfer_status === 'ALLOWED' ? 'bg-green-50 border border-green-200' :
                latestResult.transfer_status === 'PROHIBITED' ? 'bg-red-50 border border-red-200' :
                  'bg-yellow-50 border border-yellow-200'
                }`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-gray-900">Transfer Status</span>
                  <span className={`text-sm font-bold ${latestResult.transfer_status === 'ALLOWED' ? 'text-green-600' :
                    latestResult.transfer_status === 'PROHIBITED' ? 'text-red-600' :
                      'text-yellow-600'
                    }`}>
                    {latestResult.transfer_status}
                  </span>
                </div>
                {latestResult.message && (
                  <p className="text-xs text-gray-600 mt-1">{latestResult.message}</p>
                )}
              </div>

              {/* Triggered Rules */}
              {(latestResult.triggered_rules || []).length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Triggered Rules ({latestResult.triggered_rules.length})</span>
                  <div className="mt-2 space-y-2">
                    {latestResult.triggered_rules.map((rule, i) => (
                      <div key={`${rule.rule_id}-${i}`} className="border border-gray-200 rounded-lg p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-gray-400">{rule.rule_id} ({rule.rule_type})</span>
                          <span className={rule.outcome === 'permission'
                            ? 'bg-green-100 text-green-700 px-2 py-0.5 rounded text-[10px] font-semibold'
                            : 'bg-red-100 text-red-700 px-2 py-0.5 rounded text-[10px] font-semibold'}>
                            {rule.outcome === 'permission' ? 'Permission' : 'Prohibition'}
                          </span>
                        </div>
                        <p className="text-sm font-medium text-gray-800">{rule.rule_name}</p>
                        {rule.description && <p className="text-xs text-gray-500">{rule.description}</p>}

                        {/* Required Assessments */}
                        {rule.required_assessments && rule.required_assessments.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {rule.required_assessments.map(a => (
                              <span key={a} className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[10px] font-semibold">{a}</span>
                            ))}
                          </div>
                        )}

                        {/* Required Actions (e.g. "contact legal") */}
                        {rule.required_actions && rule.required_actions.length > 0 && (
                          <div>
                            <span className="text-[10px] font-semibold text-gray-400 uppercase">Actions</span>
                            <div className="flex flex-wrap gap-1 mt-0.5">
                              {rule.required_actions.map((action, ai) => (
                                <span key={ai} className="bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-[10px] font-medium">{action}</span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Duties from permissions — with overflow protection */}
                        {rule.permissions?.flatMap(p => p.duties || []).filter(d => d.name).length > 0 && (() => {
                          const allDuties = rule.permissions.flatMap(p => p.duties || []).filter(d => d.name);
                          return (
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-semibold text-gray-400 uppercase">Duties</span>
                                <span className="bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full text-[10px] font-medium">{allDuties.length}</span>
                              </div>
                              <div className={`mt-0.5 space-y-1 ${allDuties.length > 6 ? 'max-h-[200px] overflow-y-auto pr-1' : ''}`}>
                                {allDuties.map((duty, di) => (
                                  <div key={di}>
                                    <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded text-[10px] font-medium break-words inline-block" style={{ overflowWrap: 'break-word' }}>
                                      {duty.module && duty.module !== 'action' ? `[${duty.module}] ` : ''}{duty.name}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        })()}

                        {/* Prohibition details */}
                        {rule.prohibitions && rule.prohibitions.length > 0 && (
                          <div>
                            <span className="text-[10px] font-semibold text-red-400 uppercase">Prohibition</span>
                            {rule.prohibitions.map((p, pi) => (
                              <p key={pi} className="text-xs text-red-600 mt-0.5">{p.description || p.name}</p>
                            ))}
                          </div>
                        )}

                        {/* Matched Entities — shows WHY this rule triggered */}
                        {rule.matched_entities && Object.keys(rule.matched_entities).length > 0 && (
                          <div>
                            <span className="text-[10px] font-semibold text-gray-400 uppercase">Matched Entities</span>
                            <div className="mt-0.5 space-y-1">
                              {Object.entries(rule.matched_entities).map(([dimension, values]) => (
                                <div key={dimension} className="flex items-start gap-1.5">
                                  <span className="text-[10px] text-gray-500 font-medium min-w-[80px] shrink-0">{dimension}:</span>
                                  <div className="flex flex-wrap gap-1">
                                    {values.map((val, vi) => (
                                      <span key={vi} className="bg-teal-100 text-teal-700 px-1.5 py-0.5 rounded text-[10px] font-medium">{val}</span>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Assessment Compliance */}
              {latestResult.assessment_compliance && (
                <div className="border-t pt-3">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Required Assessments</span>
                  <div className="mt-1.5 flex flex-wrap gap-2">
                    {(['pia', 'tia', 'hrpr'] as const).map(key => {
                      const ac = latestResult.assessment_compliance!;
                      const required = ac[`${key}_required`];
                      const compliant = ac[`${key}_compliant`];
                      if (!required) return null;
                      return (
                        <span key={key} className={`px-2 py-1 rounded text-xs font-semibold ${compliant ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                          }`}>
                          {key.toUpperCase()}: {compliant ? 'Compliant' : 'Required'}
                        </span>
                      );
                    })}
                  </div>
                  {latestResult.assessment_compliance.missing_assessments &&
                    latestResult.assessment_compliance.missing_assessments.length > 0 && (
                      <p className="text-xs text-red-600 mt-1">
                        Missing: {latestResult.assessment_compliance.missing_assessments.join(', ')}
                      </p>
                    )}
                </div>
              )}

              {/* Consolidated Duties — with overflow protection */}
              {latestResult.consolidated_duties && latestResult.consolidated_duties.length > 0 && (
                <div className="border-t pt-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Consolidated Duties</span>
                    <span className="bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full text-[10px] font-medium">{latestResult.consolidated_duties.length}</span>
                  </div>
                  <div className={`mt-1.5 space-y-1 ${latestResult.consolidated_duties.length > 6 ? 'max-h-[200px] overflow-y-auto pr-1' : ''}`}>
                    {latestResult.consolidated_duties.map((d, i) => (
                      <div key={i}>
                        <span className="bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded text-[10px] font-medium break-words inline-block" style={{ overflowWrap: 'break-word' }}>{d}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detected Attributes */}
              {latestResult.detected_attributes && latestResult.detected_attributes.length > 0 && (
                <div className="border-t pt-3">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Detected Attributes</span>
                  <div className="mt-1 space-y-1">
                    {latestResult.detected_attributes.map((attr, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">
                          {attr.attribute_name}
                        </span>
                        {attr.detection_method && (
                          <span className="text-gray-400">{attr.detection_method}</span>
                        )}
                        {attr.confidence != null && (
                          <span className="text-gray-400">({(attr.confidence * 100).toFixed(0)}%)</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Prohibition Reasons */}
              {latestResult.prohibition_reasons && latestResult.prohibition_reasons.length > 0 && (
                <div className="border-t pt-3">
                  <span className="text-xs font-semibold text-red-500 uppercase tracking-wide">Prohibition Reasons</span>
                  <ul className="mt-1 space-y-1">
                    {latestResult.prohibition_reasons.map((r, i) => (
                      <li key={i} className="text-xs text-red-700">{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Precedent Validation */}
              {latestResult.precedent_validation && (
                <div className="border-t pt-3">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Precedent Cases</span>
                  <div className="mt-1 text-xs text-gray-600">
                    <p>{latestResult.precedent_validation.total_matches} total match(es), {latestResult.precedent_validation.compliant_matches} compliant</p>
                    {latestResult.precedent_validation.evidence_summary?.evidence_narrative && (
                      <p className="mt-1 text-gray-500">{latestResult.precedent_validation.evidence_summary.evidence_narrative}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Evaluation Time */}
              {latestResult.evaluation_time_ms != null && (
                <div className="text-right">
                  <span className="text-[10px] text-gray-400">{latestResult.evaluation_time_ms.toFixed(0)}ms</span>
                </div>
              )}
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
