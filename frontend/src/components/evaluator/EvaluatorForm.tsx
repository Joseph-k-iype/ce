import { useState, useEffect } from 'react';
import { useDropdownData } from '../../hooks/useDropdownData';
import { useEvaluation } from '../../hooks/useEvaluation';
import { useEvaluationStore } from '../../stores/evaluationStore';
import type { RulesEvaluationRequest } from '../../types/api';
import { LoadingSpinner } from '../common/LoadingSpinner';

interface MetadataEntry { key: string; value: string; }

export function EvaluatorForm() {
  const { data: dropdowns, isLoading: loadingDropdowns } = useDropdownData();
  const evaluate = useEvaluation();
  const { setResult, setScenarioInput, setLoading, setError } = useEvaluationStore();

  const [formData, setFormData] = useState<RulesEvaluationRequest>({
    origin_country: '',
    receiving_country: [],
    pii: false,
    purpose_of_processing: [],
    data_categories: [],
    processes: [],
    personal_data_names: [],
    purposes: [],
    process_l1: [],
    process_l2: [],
    process_l3: [],
    origin_legal_entity: '',
    receiving_legal_entity: [],
    data_subjects: [],
    gdc: [],
    regulator: [],
    authority: [],
  });

  const [metadataEntries, setMetadataEntries] = useState<MetadataEntry[]>([]);
  const [personalDataInput, setPersonalDataInput] = useState('');
  const [originLEs, setOriginLEs] = useState<string[]>([]);
  const [receivingLEs, setReceivingLEs] = useState<string[]>([]);

  // Update legal entities when country changes
  useEffect(() => {
    if (dropdowns?.legal_entities && formData.origin_country) {
      setOriginLEs(dropdowns.legal_entities[formData.origin_country] || []);
    } else {
      setOriginLEs([]);
    }
  }, [formData.origin_country, dropdowns]);

  useEffect(() => {
    if (dropdowns?.legal_entities) {
      const receivingCountries = formData.receiving_country;
      const countries = (Array.isArray(receivingCountries) ? receivingCountries : [receivingCountries]).filter((c): c is string => !!c);
      const allLEs: string[] = [];
      countries.forEach(c => {
        const les = dropdowns.legal_entities[c] || [];
        allLEs.push(...les);
      });
      setReceivingLEs(allLEs);
    } else {
      setReceivingLEs([]);
    }
  }, [formData.receiving_country, dropdowns]);

  if (loadingDropdowns) return <LoadingSpinner message="Loading..." />;

  const addMetadataEntry = () => setMetadataEntries(prev => [...prev, { key: '', value: '' }]);
  const removeMetadataEntry = (i: number) => setMetadataEntries(prev => prev.filter((_, idx) => idx !== i));
  const updateMetadataEntry = (i: number, field: 'key' | 'value', val: string) =>
    setMetadataEntries(prev => prev.map((e, idx) => idx === i ? { ...e, [field]: val } : e));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const metadata: Record<string, unknown> = {};
      metadataEntries.filter(e => e.key.trim()).forEach(e => { metadata[e.key.trim()] = e.value; });
      const payload = {
        ...formData,
        ...(Object.keys(metadata).length > 0 ? { metadata } : {}),
      };
      setScenarioInput(payload);
      const result = await evaluate.mutateAsync(payload);
      setResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed');
    }
  };

  const purposes = (dropdowns?.purpose_of_processing?.length ? dropdowns.purpose_of_processing : (dropdowns?.purposes || []))
    .map((p: string | { name: string }) => typeof p === 'string' ? p : p.name);

  return (
    <form onSubmit={handleSubmit} className="card-dark space-y-6">
      <div className="grid grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Origin Country</label>
            <select
              value={formData.origin_country || ''}
              onChange={(e) => setFormData(f => ({ ...f, origin_country: e.target.value, origin_legal_entity: '' as string }))}
              className="input-dark" required
            >
              <option value="">Select...</option>
              {(dropdowns?.countries || []).map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Receiving Country</label>
            <select
              multiple
              value={Array.isArray(formData.receiving_country) ? formData.receiving_country : (formData.receiving_country ? [formData.receiving_country] : [])}
              onChange={(e) => setFormData(f => ({ ...f, receiving_country: Array.from(e.target.selectedOptions, o => o.value) }))}
              className="input-dark h-20"
            >
              {(dropdowns?.countries || []).map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Originating Legal Entity</label>
            <select
              multiple
              value={Array.isArray(formData.origin_legal_entity) ? formData.origin_legal_entity : (formData.origin_legal_entity ? [formData.origin_legal_entity] : [])}
              onChange={(e) => setFormData(f => ({ ...f, origin_legal_entity: Array.from(e.target.selectedOptions, o => o.value).join(',') }))}
              className="input-dark h-20"
            >
              {originLEs.map(le => <option key={le} value={le}>{le}</option>)}
            </select>
            <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Receiving Legal Entity</label>
            <select
              multiple
              value={formData.receiving_legal_entity || []}
              onChange={(e) => setFormData(f => ({ ...f, receiving_legal_entity: Array.from(e.target.selectedOptions, o => o.value) }))}
              className="input-dark h-20"
            >
              {receivingLEs.map(le => <option key={le} value={le}>{le}</option>)}
            </select>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Purpose Of Processing</label>
            <select
              multiple
              value={formData.purposes || []}
              onChange={(e) => setFormData(f => ({ ...f, purposes: Array.from(e.target.selectedOptions, o => o.value) }))}
              className="input-dark h-20"
            >
              {purposes.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Process L1</label>
            <select
              multiple
              value={formData.process_l1 || []}
              onChange={(e) => setFormData(f => ({ ...f, process_l1: Array.from(e.target.selectedOptions, o => o.value) }))}
              className="input-dark h-16"
            >
              {(dropdowns?.processes?.l1 || []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Process L2</label>
            <select
              multiple
              value={formData.process_l2 || []}
              onChange={(e) => setFormData(f => ({ ...f, process_l2: Array.from(e.target.selectedOptions, o => o.value) }))}
              className="input-dark h-16"
            >
              {(dropdowns?.processes?.l2 || []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Process L3</label>
            <select
              multiple
              value={formData.process_l3 || []}
              onChange={(e) => setFormData(f => ({ ...f, process_l3: Array.from(e.target.selectedOptions, o => o.value) }))}
              className="input-dark h-16"
            >
              {(dropdowns?.processes?.l3 || []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Data Categories & Personal Data */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Data Categories</label>
          <select
            multiple
            value={Array.isArray(formData.data_categories) ? formData.data_categories : []}
            onChange={(e) => setFormData(f => ({ ...f, data_categories: Array.from(e.target.selectedOptions, o => o.value) }))}
            className="input-dark h-20"
          >
            {(dropdowns?.data_categories || []).map(dc => <option key={dc.name} value={dc.name}>{dc.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Personal Data Names</label>
          <input
            type="text"
            value={personalDataInput}
            onChange={(e) => {
              setPersonalDataInput(e.target.value);
              const names = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
              setFormData(f => ({ ...f, personal_data_names: names }));
            }}
            placeholder="e.g., Credit Card Number, Medical Records"
            className="input-dark"
          />
          <p className="text-xs text-gray-400 mt-1">Comma-separated list</p>
        </div>
      </div>

      {/* Data Subjects, GDC, Regulator, Authority */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Data Subjects</label>
          <select
            multiple
            value={Array.isArray(formData.data_subjects) ? formData.data_subjects : []}
            onChange={(e) => setFormData(f => ({ ...f, data_subjects: Array.from(e.target.selectedOptions, o => o.value) }))}
            className="input-dark h-20"
          >
            {(dropdowns?.data_subjects || []).map((ds: { name: string }) => <option key={ds.name} value={ds.name}>{ds.name}</option>)}
          </select>
          <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
        </div>
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Group Data Categories (GDC)</label>
          <select
            multiple
            value={Array.isArray(formData.gdc) ? formData.gdc : []}
            onChange={(e) => setFormData(f => ({ ...f, gdc: Array.from(e.target.selectedOptions, o => o.value) }))}
            className="input-dark h-20"
          >
            {(dropdowns?.gdc || []).map((g: { name: string }) => <option key={g.name} value={g.name}>{g.name}</option>)}
          </select>
          <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Regulator</label>
          <select
            multiple
            value={Array.isArray(formData.regulator) ? formData.regulator : []}
            onChange={(e) => setFormData(f => ({ ...f, regulator: Array.from(e.target.selectedOptions, o => o.value) }))}
            className="input-dark h-20"
          >
            {(dropdowns?.regulators || []).map((r: { name: string }) => <option key={r.name} value={r.name}>{r.name}</option>)}
          </select>
          <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
        </div>
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Authority</label>
          <select
            multiple
            value={Array.isArray(formData.authority) ? formData.authority : []}
            onChange={(e) => setFormData(f => ({ ...f, authority: Array.from(e.target.selectedOptions, o => o.value) }))}
            className="input-dark h-20"
          >
            {(dropdowns?.authorities || []).map((a: { name: string }) => <option key={a.name} value={a.name}>{a.name}</option>)}
          </select>
          <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
        </div>
      </div>

      {/* PII toggle */}
      <label className="flex items-center gap-2 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={formData.pii || false}
          onChange={(e) => setFormData(f => ({ ...f, pii: e.target.checked }))}
          className="w-4 h-4 rounded border-gray-500"
        />
        <span className="text-sm text-gray-300">Transfer involves PII</span>
      </label>

      {/* Other metadata */}
      <div>
        <label className="block text-sm font-semibold text-white mb-2">Other metadata</label>
        <div className="space-y-2">
          {metadataEntries.map((entry, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input value={entry.key} onChange={(e) => updateMetadataEntry(i, 'key', e.target.value)} placeholder="Key" className="input-dark flex-1" />
              <input value={entry.value} onChange={(e) => updateMetadataEntry(i, 'value', e.target.value)} placeholder="Column" className="input-dark flex-1" />
              <button type="button" onClick={() => removeMetadataEntry(i)} className="text-red-400 hover:text-red-300 text-lg">&times;</button>
            </div>
          ))}
          <button type="button" onClick={addMetadataEntry} className="w-8 h-8 rounded-full border border-gray-500 text-gray-400 hover:text-white hover:border-white flex items-center justify-center text-lg">+</button>
        </div>
      </div>

      <button type="submit" disabled={evaluate.isPending} className="btn-red w-full">
        {evaluate.isPending ? 'Evaluating...' : 'Evaluate Compliance'}
      </button>
    </form>
  );
}
