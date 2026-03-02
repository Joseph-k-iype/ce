import { useEffect } from 'react';
import { useDropdownData } from '../../../hooks/useDropdownData';
import { useWizardStore } from '../../../stores/wizardStore';
import { LoadingSpinner } from '../../common/LoadingSpinner';
import { AccessibleSelect } from '../../common/AccessibleSelect';

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
        <AccessibleSelect
          id="metadata-data-categories"
          label={`Data Categories ${dataCategories.length > 0 && editedRuleDefinition ? '(AI suggested)' : ''}`}
          value={dataCategories}
          options={dataCatOptions.map((c: any) => {
            const val = typeof c === 'string' ? c : c.name;
            return { value: val, label: val };
          })}
          onChange={setDataCategories}
          helpText="Select all applicable data categories"
          required={true}
          placeholder="Select data categories..."
        />

        {/* Purpose of Processing */}
        <AccessibleSelect
          id="metadata-purposes"
          label={`Purpose of Processing ${purposesOfProcessing.length > 0 && editedRuleDefinition ? '(AI suggested)' : ''}`}
          value={purposesOfProcessing}
          options={purposes.map((p: any) => {
            const val = typeof p === 'string' ? p : p.name;
            return { value: val, label: val };
          })}
          onChange={setPurposesOfProcessing}
          helpText="Select all purposes for data processing"
          placeholder="Select purposes..."
        />

        {/* Processes L1, L2, L3 */}
        <div className="grid grid-cols-3 gap-4">
          <AccessibleSelect
            id="metadata-process-l1"
            label={`Process L1 ${processL1.length > 0 && editedRuleDefinition ? '(AI)' : ''}`}
            value={processL1}
            options={(dropdowns?.processes?.l1 || []).map(p => ({ value: p, label: p }))}
            onChange={setProcessL1}
            helpText="Level 1 processes"
            placeholder="Select L1..."
          />
          <AccessibleSelect
            id="metadata-process-l2"
            label={`Process L2 ${processL2.length > 0 && editedRuleDefinition ? '(AI)' : ''}`}
            value={processL2}
            options={(dropdowns?.processes?.l2 || []).map(p => ({ value: p, label: p }))}
            onChange={setProcessL2}
            helpText="Level 2 processes"
            placeholder="Select L2..."
          />
          <AccessibleSelect
            id="metadata-process-l3"
            label={`Process L3 ${processL3.length > 0 && editedRuleDefinition ? '(AI)' : ''}`}
            value={processL3}
            options={(dropdowns?.processes?.l3 || []).map(p => ({ value: p, label: p }))}
            onChange={setProcessL3}
            helpText="Level 3 processes"
            placeholder="Select L3..."
          />
        </div>

        {/* Group Data Categories (GDC) — multiselect */}
        <AccessibleSelect
          id="metadata-gdc"
          label={`Group Data Categories ${groupDataCategories.length > 0 && editedRuleDefinition ? '(AI suggested)' : ''}`}
          value={groupDataCategories}
          options={gdcOptions.map((g: any) => {
            const val = typeof g === 'string' ? g : g.name;
            return { value: val, label: val };
          })}
          onChange={setGroupDataCategories}
          helpText="Grouped categories (optional)"
          placeholder="Select group data categories..."
        />

        {/* Sensitive Data Categories — AI-suggested, user-confirmable */}
        <AccessibleSelect
          id="metadata-sensitive"
          label="Sensitive Data Categories (AI suggested)"
          value={sensitiveDataCategories}
          options={(dropdowns?.sensitive_data_categories || []).map((s: any) => {
            const val = typeof s === 'string' ? s : s.name;
            return { value: val, label: val };
          })}
          onChange={setSensitiveDataCategories}
          helpText="Pre-filled from AI analysis"
          placeholder="Select sensitive data categories..."
        />

        {/* Regulator & Authority — AI-suggested, user-confirmable */}
        <div className="grid grid-cols-2 gap-4">
          <AccessibleSelect
            id="metadata-regulators"
            label="Regulator (AI suggested)"
            value={regulators}
            options={(dropdowns?.regulators || []).map((r: any) => {
              const val = typeof r === 'string' ? r : r.name;
              return { value: val, label: val };
            })}
            onChange={setRegulators}
            helpText="Select applicable regulators"
            placeholder="Select regulators..."
          />
          <AccessibleSelect
            id="metadata-authorities"
            label="Authority (AI suggested)"
            value={authorities}
            options={(dropdowns?.authorities || []).map((a: any) => {
              const val = typeof a === 'string' ? a : a.name;
              return { value: val, label: val };
            })}
            onChange={setAuthorities}
            helpText="Select applicable authorities"
            placeholder="Select authorities..."
          />
        </div>

        {/* Data Subjects — AI-suggested */}
        <AccessibleSelect
          id="metadata-data-subjects"
          label="Data Subjects (AI suggested)"
          value={dataSubjects}
          options={dataSubjectOptions.map((ds: any) => {
            const val = typeof ds === 'string' ? ds : ds.name;
            return { value: val, label: val };
          })}
          onChange={setDataSubjects}
          helpText="Pre-filled from AI analysis"
          placeholder="Select data subjects..."
        />

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
