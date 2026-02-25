import { useEffect } from 'react';
import { useDropdownData } from '../../../hooks/useDropdownData';
import { useWizardStore } from '../../../stores/wizardStore';
import { LoadingSpinner } from '../../common/LoadingSpinner';

export function Step2Metadata() {
  const { data: dropdowns, isLoading } = useDropdownData();
  const {
    dataCategories, purposesOfProcessing, processL1, processL2, processL3,
    groupDataCategories, sensitiveDataCategories, regulators, authorities, dataSubjects,
    validUntil, editedRuleDefinition,
    setDataCategories, setPurposesOfProcessing, setProcessL1, setProcessL2, setProcessL3,
    setGroupDataCategories, setSensitiveDataCategories, setRegulators, setAuthorities,
    setDataSubjects, setValidUntil,
  } = useWizardStore();

  // Pre-populate all AI-suggested fields from the rule definition when it becomes available
  useEffect(() => {
    if (!editedRuleDefinition) return;
    const ruleDef = editedRuleDefinition as Record<string, unknown>;

    // data_categories — cross-reference with dropdown to filter valid values
    if ((ruleDef.data_categories as string[])?.length && dataCategories.length === 0) {
      const aiCats = ruleDef.data_categories as string[];
      const validCats = dropdowns?.data_categories
        ? aiCats.filter(v => dropdowns.data_categories!.some(d => d.name === v || (d as unknown as string) === v))
        : aiCats;
      if (validCats.length > 0) setDataCategories(validCats);
      else if (aiCats.length > 0) setDataCategories(aiCats);
    }

    // purposes_of_processing
    if ((ruleDef.purposes_of_processing as string[])?.length && purposesOfProcessing.length === 0) {
      setPurposesOfProcessing(ruleDef.purposes_of_processing as string[]);
    }

    // processes — split into L1/L2/L3 by cross-referencing dropdowns
    if ((ruleDef.processes as string[])?.length) {
      const aiProcs = ruleDef.processes as string[];
      if (dropdowns?.processes) {
        const l1Items = aiProcs.filter(p => dropdowns.processes.l1?.includes(p));
        const l2Items = aiProcs.filter(p => dropdowns.processes.l2?.includes(p));
        const l3Items = aiProcs.filter(p => dropdowns.processes.l3?.includes(p));
        const unmatched = aiProcs.filter(
          p => !l1Items.includes(p) && !l2Items.includes(p) && !l3Items.includes(p)
        );
        if (l1Items.length > 0 && processL1.length === 0) setProcessL1(l1Items);
        if (l2Items.length > 0 && processL2.length === 0) setProcessL2(l2Items);
        if (l3Items.length > 0 && processL3.length === 0) setProcessL3(l3Items);
        // Unmatched items go to L1 as fallback
        if (unmatched.length > 0 && processL1.length === 0 && l1Items.length === 0) setProcessL1(unmatched);
      } else if (processL1.length === 0) {
        setProcessL1(aiProcs);
      }
    }

    // group_data_categories (GDC)
    if ((ruleDef.gdc as string[])?.length && groupDataCategories.length === 0) {
      setGroupDataCategories(ruleDef.gdc as string[]);
    }

    // sensitive_data_categories
    if ((ruleDef.sensitive_data_categories as string[])?.length && sensitiveDataCategories.length === 0) {
      setSensitiveDataCategories(ruleDef.sensitive_data_categories as string[]);
    }

    // regulators
    if ((ruleDef.regulators as string[])?.length && regulators.length === 0) {
      setRegulators(ruleDef.regulators as string[]);
    }

    // authorities
    if ((ruleDef.authorities as string[])?.length && authorities.length === 0) {
      setAuthorities(ruleDef.authorities as string[]);
    }

    // data_subjects
    if ((ruleDef.data_subjects as string[])?.length && dataSubjects.length === 0) {
      setDataSubjects(ruleDef.data_subjects as string[]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editedRuleDefinition, dropdowns]);

  if (isLoading) return <LoadingSpinner />;

  const purposes = dropdowns?.purpose_of_processing?.length
    ? dropdowns.purpose_of_processing
    : (dropdowns?.purposes || []);

  const dataCatOptions = dropdowns?.data_categories || [];
  const gdcOptions = dropdowns?.group_data_categories || [];
  const dataSubjectOptions = dropdowns?.data_subjects || [];

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900">Step 3: Metadata</h3>

      <div className="card-dark p-5 space-y-5">
        {/* Data Categories — multiselect with AI pre-fill */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">
            Data Categories <span className="text-red-400">*</span>
            {dataCategories.length > 0 && editedRuleDefinition && (
              <span className="ml-2 text-xs text-purple-400 font-normal">(AI suggested)</span>
            )}
          </label>
          <select
            multiple
            value={dataCategories}
            onChange={(e) => setDataCategories(Array.from(e.target.selectedOptions, o => o.value))}
            className="input-dark h-24"
          >
            {dataCatOptions.map((c: any) => {
              const val = typeof c === 'string' ? c : c.name;
              return <option key={val} value={val}>{val}</option>;
            })}
          </select>
          <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
        </div>

        {/* Purpose of Processing */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">
            Purpose of Processing
            {purposesOfProcessing.length > 0 && editedRuleDefinition && (
              <span className="ml-2 text-xs text-purple-400 font-normal">(AI suggested)</span>
            )}
          </label>
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
          <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
        </div>

        {/* Processes L1, L2, L3 */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-semibold text-white mb-2">
              Process L1
              {processL1.length > 0 && editedRuleDefinition && (
                <span className="ml-1 text-xs text-purple-400 font-normal">(AI)</span>
              )}
            </label>
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
            <label className="block text-sm font-semibold text-white mb-2">
              Process L2
              {processL2.length > 0 && editedRuleDefinition && (
                <span className="ml-1 text-xs text-purple-400 font-normal">(AI)</span>
              )}
            </label>
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
            <label className="block text-sm font-semibold text-white mb-2">
              Process L3
              {processL3.length > 0 && editedRuleDefinition && (
                <span className="ml-1 text-xs text-purple-400 font-normal">(AI)</span>
              )}
            </label>
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

        {/* Group Data Categories (GDC) — multiselect */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">
            Group Data Categories
            {groupDataCategories.length > 0 && editedRuleDefinition && (
              <span className="ml-2 text-xs text-purple-400 font-normal">(AI suggested)</span>
            )}
          </label>
          <select
            multiple
            value={groupDataCategories}
            onChange={(e) => setGroupDataCategories(Array.from(e.target.selectedOptions, o => o.value))}
            className="input-dark h-20"
          >
            {gdcOptions.map((g: any) => {
              const val = typeof g === 'string' ? g : g.name;
              return <option key={val} value={val}>{val}</option>;
            })}
          </select>
          <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple. (Optional)</p>
        </div>

        {/* Sensitive Data Categories — AI-suggested, user-confirmable */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">
            Sensitive Data Categories
            <span className="ml-2 text-xs text-purple-400 font-normal">(AI suggested)</span>
          </label>
          <select
            multiple
            value={sensitiveDataCategories}
            onChange={(e) => setSensitiveDataCategories(Array.from(e.target.selectedOptions, o => o.value))}
            className="input-dark h-24"
          >
            {(dropdowns?.sensitive_data_categories || []).map((s: any) => {
              const val = typeof s === 'string' ? s : s.name;
              return <option key={val} value={val}>{val}</option>;
            })}
          </select>
          <p className="text-xs text-gray-400 mt-1">Pre-filled from AI analysis. Hold Ctrl/Cmd to adjust.</p>
        </div>

        {/* Regulator, Authority & Data Subjects — AI-suggested, user-confirmable */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-white mb-2">
              Regulator
              <span className="ml-2 text-xs text-purple-400 font-normal">(AI suggested)</span>
            </label>
            <select
              multiple
              value={regulators}
              onChange={(e) => setRegulators(Array.from(e.target.selectedOptions, o => o.value))}
              className="input-dark h-24"
            >
              {(dropdowns?.regulators || []).map((r: any) => {
                const val = typeof r === 'string' ? r : r.name;
                return <option key={val} value={val}>{val}</option>;
              })}
            </select>
            <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-white mb-2">
              Authority
              <span className="ml-2 text-xs text-purple-400 font-normal">(AI suggested)</span>
            </label>
            <select
              multiple
              value={authorities}
              onChange={(e) => setAuthorities(Array.from(e.target.selectedOptions, o => o.value))}
              className="input-dark h-24"
            >
              {(dropdowns?.authorities || []).map((a: any) => {
                const val = typeof a === 'string' ? a : a.name;
                return <option key={val} value={val}>{val}</option>;
              })}
            </select>
            <p className="text-xs text-gray-400 mt-1">Hold Ctrl/Cmd to select multiple.</p>
          </div>
        </div>

        {/* Data Subjects — AI-suggested */}
        <div>
          <label className="block text-sm font-semibold text-white mb-2">
            Data Subjects
            <span className="ml-2 text-xs text-purple-400 font-normal">(AI suggested)</span>
          </label>
          <select
            multiple
            value={dataSubjects}
            onChange={(e) => setDataSubjects(Array.from(e.target.selectedOptions, o => o.value))}
            className="input-dark h-24"
          >
            {dataSubjectOptions.map((ds: any) => {
              const val = typeof ds === 'string' ? ds : ds.name;
              return <option key={val} value={val}>{val}</option>;
            })}
          </select>
          <p className="text-xs text-gray-400 mt-1">Pre-filled from AI analysis. Hold Ctrl/Cmd to adjust.</p>
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
