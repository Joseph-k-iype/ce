import { useState } from 'react';
import { useDropdownData } from '../../../hooks/useDropdownData';
import { useWizardStore } from '../../../stores/wizardStore';
import { LoadingSpinner } from '../../common/LoadingSpinner';

export function Step2Metadata() {
  const { data: dropdowns, isLoading } = useDropdownData();
  const {
    dataCategories, purposesOfProcessing, processL1, processL2, processL3,
    groupDataCategories, validUntil,
    setDataCategories, setPurposesOfProcessing, setProcessL1, setProcessL2, setProcessL3,
    setGroupDataCategories, setValidUntil,
  } = useWizardStore();

  const [dataCatInput, setDataCatInput] = useState(dataCategories.join(', '));
  const [gdcInput, setGdcInput] = useState(groupDataCategories.join(', '));

  if (isLoading) return <LoadingSpinner />;

  const purposes = dropdowns?.purpose_of_processing?.length
    ? dropdowns.purpose_of_processing
    : (dropdowns?.purposes || []);

  const handleDataCatBlur = () => {
    const cats = dataCatInput.split(',').map(s => s.trim()).filter(Boolean);
    setDataCategories(cats);
  };

  const handleGdcBlur = () => {
    const gdc = gdcInput.split(',').map(s => s.trim()).filter(Boolean);
    setGroupDataCategories(gdc);
  };

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900">Step 3: Metadata</h3>

      <div className="card-dark p-5 space-y-5">
        {/* Data Categories - REQUIRED */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">
            Data Categories <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={dataCatInput}
            onChange={(e) => setDataCatInput(e.target.value)}
            onBlur={handleDataCatBlur}
            placeholder="e.g., Financial Data, Customer PII, Transaction Records"
            className="input-dark"
          />
          <p className="text-xs text-gray-400 mt-1">Comma-separated list of data categories</p>
        </div>

        {/* Purpose of Processing */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Purpose of Processing</label>
          <select
            multiple
            value={purposesOfProcessing}
            onChange={(e) => setPurposesOfProcessing(Array.from(e.target.selectedOptions, o => o.value))}
            className="input-dark h-24"
          >
            {purposes.map((p: any) => {
              const val = typeof p === 'string' ? p : p.name;
              return <option key={val} value={val}>{val}</option>;
            })}
          </select>
        </div>

        {/* Processes L1, L2, L3 */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Process L1</label>
            <select
              multiple
              value={processL1}
              onChange={(e) => setProcessL1(Array.from(e.target.selectedOptions, o => o.value))}
              className="input-dark h-20"
            >
              {(dropdowns?.processes?.l1 || []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Process L2</label>
            <select
              multiple
              value={processL2}
              onChange={(e) => setProcessL2(Array.from(e.target.selectedOptions, o => o.value))}
              className="input-dark h-20"
            >
              {(dropdowns?.processes?.l2 || []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">Process L3</label>
            <select
              multiple
              value={processL3}
              onChange={(e) => setProcessL3(Array.from(e.target.selectedOptions, o => o.value))}
              className="input-dark h-20"
            >
              {(dropdowns?.processes?.l3 || []).map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        </div>

        {/* Group Data Categories */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Group Data Categories</label>
          <input
            type="text"
            value={gdcInput}
            onChange={(e) => setGdcInput(e.target.value)}
            onBlur={handleGdcBlur}
            placeholder="e.g., Sensitive, Non-Sensitive"
            className="input-dark"
          />
          <p className="text-xs text-gray-400 mt-1">Comma-separated (optional)</p>
        </div>

        {/* Valid Until */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">Valid Until</label>
          <input
            type="date"
            value={validUntil}
            onChange={(e) => setValidUntil(e.target.value)}
            className="input-dark"
          />
          <p className="text-xs text-gray-400 mt-1">Leave empty for no expiration</p>
        </div>
      </div>
    </div>
  );
}
