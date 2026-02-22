import { useState, useEffect, useCallback } from 'react';
import { useWizardStore } from '../../../stores/wizardStore';
import { editRule, editTerms } from '../../../services/wizardApi';

export function Step4Review() {
  const {
    editedRuleDefinition,
    editedTermsDictionary,
    dictionaryResult,
    sessionId,
    setEditedRuleDefinition,
    setEditedTermsDictionary,
  } = useWizardStore();

  const rule = editedRuleDefinition as Record<string, unknown> | null;
  const terms = (editedTermsDictionary || dictionaryResult) as Record<string, unknown> | null;

  // Rule fields
  const [ruleId, setRuleId] = useState('');
  const [ruleName, setRuleName] = useState('');
  const [ruleDescription, setRuleDescription] = useState('');
  const [outcome, setOutcome] = useState('permission');
  const [ruleType, setRuleType] = useState('attribute');
  const [caseMatchingModule, setCaseMatchingModule] = useState('');
  const [priority, setPriority] = useState('medium');
  const [actions, setActions] = useState('');
  const [duties, setDuties] = useState('');
  const [originCountries, setOriginCountries] = useState('');
  const [originGroup, setOriginGroup] = useState('');
  const [receivingCountries, setReceivingCountries] = useState('');
  const [receivingGroup, setReceivingGroup] = useState('');
  const [requiresPii, setRequiresPii] = useState(false);
  const [odrlType, setOdrlType] = useState('Permission');
  const [odrlAction, setOdrlAction] = useState('transfer');

  // Dictionary editing state — each entry is a JSON string the user can edit
  const [editableTerms, setEditableTerms] = useState<Record<string, string>>({});

  // UI state
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Initialize rule fields from the rule definition
  useEffect(() => {
    if (!rule) return;
    setRuleId((rule.rule_id as string) || '');
    setRuleName((rule.name as string) || '');
    setRuleDescription((rule.description as string) || '');
    setOutcome((rule.outcome as string) || 'permission');
    setRuleType((rule.rule_type as string) || 'attribute');
    setCaseMatchingModule((rule.case_matching_module as string) || '');
    setPriority((rule.priority as string) || 'medium');
    setOdrlType((rule.odrl_type as string) || 'Permission');
    setOdrlAction((rule.odrl_action as string) || 'transfer');
    setRequiresPii(Boolean(rule.requires_pii));

    // Actions
    const ruleActions = (rule.required_actions as string[]) || [];
    setActions(ruleActions.join(', '));

    // Duties — from permissions[].duties[].name AND top-level duties[]
    const allDuties: string[] = [];
    const perms = rule.permissions as Array<{ duties?: Array<{ name?: string }> }> | undefined;
    (perms || []).forEach(p => {
      (p.duties || []).forEach(d => {
        if (d.name && !allDuties.includes(d.name)) allDuties.push(d.name);
      });
    });
    const topDuties = (rule.duties as string[]) || [];
    topDuties.forEach(d => { if (d && !allDuties.includes(d)) allDuties.push(d); });
    setDuties(allDuties.join(', '));

    // Origin / Receiving
    setOriginGroup((rule.origin_group as string) || '');
    setOriginCountries(((rule.origin_countries as string[]) || []).join(', '));
    setReceivingGroup((rule.receiving_group as string) || '');
    setReceivingCountries(((rule.receiving_countries as string[]) || []).join(', '));
  }, [rule]);

  // Initialize editable dictionary terms
  useEffect(() => {
    if (!terms) return;
    const entries: Record<string, string> = {};
    for (const [key, value] of Object.entries(terms)) {
      if (typeof value === 'object' && value !== null) {
        entries[key] = JSON.stringify(value, null, 2);
      } else if (Array.isArray(value)) {
        entries[key] = (value as string[]).join(', ');
      } else if (value !== undefined && value !== null) {
        entries[key] = String(value);
      }
    }
    setEditableTerms(entries);
  }, [terms]);

  const handleTermChange = useCallback((key: string, value: string) => {
    setEditableTerms(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleSave = async () => {
    if (!sessionId || !rule) return;
    setSaving(true);
    try {
      // Build updated rule from all editable fields
      const updatedRule: Record<string, unknown> = {
        ...rule,
        rule_id: ruleId,
        name: ruleName,
        description: ruleDescription,
        outcome,
        rule_type: ruleType,
        case_matching_module: ruleType === 'case_matching' ? caseMatchingModule : null,
        priority,
        odrl_type: odrlType,
        odrl_action: odrlAction,
        requires_pii: requiresPii,
        required_actions: actions.split(',').map(s => s.trim()).filter(Boolean),
        duties: duties.split(',').map(s => s.trim()).filter(Boolean),
        origin_group: originGroup || null,
        origin_countries: originCountries ? originCountries.split(',').map(s => s.trim()).filter(Boolean) : null,
        receiving_group: receivingGroup || null,
        receiving_countries: receivingCountries ? receivingCountries.split(',').map(s => s.trim()).filter(Boolean) : null,
      };

      await editRule(sessionId, updatedRule);
      setEditedRuleDefinition(updatedRule);

      // Build updated terms dictionary from editable text fields
      if (Object.keys(editableTerms).length > 0) {
        const updatedTerms: Record<string, unknown> = {};
        for (const [key, rawValue] of Object.entries(editableTerms)) {
          const trimmed = rawValue.trim();
          if (!trimmed) continue;
          // Try parsing as JSON first (for objects/arrays)
          try {
            updatedTerms[key] = JSON.parse(trimmed);
          } catch {
            // If not JSON, treat as a simple string value
            updatedTerms[key] = trimmed;
          }
        }
        await editTerms(sessionId, updatedTerms);
        setEditedTermsDictionary(updatedTerms);
      }

      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // handled by parent error
    }
    setSaving(false);
  };

  if (!rule) {
    return (
      <div className="text-center py-12 text-gray-400 text-sm">
        No rule definition available. Go back to Step 3 and submit a rule.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900">Step 4: Review & Edit</h3>
        <button onClick={handleSave} disabled={saving} className="btn-red px-4 py-1.5 text-xs">
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      {/* Rule Definition — Fully Editable */}
      <div className="card-dark p-5 space-y-4">
        <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Rule Definition</h4>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Rule ID</label>
            <input value={ruleId} onChange={e => setRuleId(e.target.value)} className="input-dark text-sm" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Outcome</label>
            <select value={outcome} onChange={e => { setOutcome(e.target.value); setOdrlType(e.target.value === 'prohibition' ? 'Prohibition' : 'Permission'); }} className="input-dark text-sm">
              <option value="permission">Permission</option>
              <option value="prohibition">Prohibition</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Priority</label>
            <select value={priority} onChange={e => setPriority(e.target.value)} className="input-dark text-sm">
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1">Rule Title</label>
          <input value={ruleName} onChange={e => setRuleName(e.target.value)} className="input-dark text-sm" />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1">Rule Description</label>
          <textarea value={ruleDescription} onChange={e => setRuleDescription(e.target.value)} rows={3} className="input-dark text-sm resize-none" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Actions (System)</label>
            <input value={actions} onChange={e => setActions(e.target.value)} placeholder="Comma-separated..." className="input-dark text-sm" />
            <p className="text-[10px] text-gray-500 mt-0.5">Anonymisation, Enhanced Security, Storage Limitation, Services Agreement, Outsourcing Agreement</p>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Duties (User)</label>
            <input value={duties} onChange={e => setDuties(e.target.value)} placeholder="Comma-separated..." className="input-dark text-sm" />
            <p className="text-[10px] text-gray-500 mt-0.5">Consent, Consult/Approve Legal, Consult/Approve Risk, Notification to Regulator, Explicit Consent</p>
          </div>
        </div>
      </div>

      {/* Origin / Receiving — Editable */}
      <div className="card-dark p-5 space-y-4">
        <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Origin & Receiving</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Origin Country Group</label>
            <input value={originGroup} onChange={e => setOriginGroup(e.target.value)} placeholder="e.g. EEA, APAC, or leave empty" className="input-dark text-sm" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Origin Countries</label>
            <input value={originCountries} onChange={e => setOriginCountries(e.target.value)} placeholder="Comma-separated country names" className="input-dark text-sm" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Receiving Country Group</label>
            <input value={receivingGroup} onChange={e => setReceivingGroup(e.target.value)} placeholder="e.g. NON_EEA, or leave empty" className="input-dark text-sm" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Receiving Countries</label>
            <input value={receivingCountries} onChange={e => setReceivingCountries(e.target.value)} placeholder="Comma-separated country names" className="input-dark text-sm" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">Rule Type</label>
            <select value={ruleType} onChange={e => { setRuleType(e.target.value); if (e.target.value !== 'case_matching') setCaseMatchingModule(''); }} className="input-dark text-sm">
              <option value="attribute">Attribute</option>
              <option value="case_matching">Case Matching</option>
            </select>
          </div>
          {ruleType === 'case_matching' && (
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">Assessment Module</label>
              <select value={caseMatchingModule} onChange={e => setCaseMatchingModule(e.target.value)} className="input-dark text-sm">
                <option value="">Select module...</option>
                <option value="PIA">PIA (Privacy Impact Assessment)</option>
                <option value="TIA">TIA (Transfer Impact Assessment)</option>
                <option value="HRPR">HRPR (Human Rights Prior Review)</option>
              </select>
              <p className="text-[10px] text-gray-500 mt-0.5">Required: select which assessment module this rule triggers</p>
            </div>
          )}
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">ODRL Type</label>
            <select value={odrlType} onChange={e => { setOdrlType(e.target.value); setOutcome(e.target.value === 'Prohibition' ? 'prohibition' : 'permission'); }} className="input-dark text-sm">
              <option value="Permission">Permission</option>
              <option value="Prohibition">Prohibition</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">ODRL Action</label>
            <input value={odrlAction} onChange={e => setOdrlAction(e.target.value)} className="input-dark text-sm" />
          </div>
          <div className="flex items-end gap-2 pb-1">
            <label className="flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer">
              <input type="checkbox" checked={requiresPii} onChange={e => setRequiresPii(e.target.checked)} className="rounded" />
              Requires PII
            </label>
          </div>
        </div>
      </div>

      {/* Data Dictionaries — Fully Editable */}
      {Object.keys(editableTerms).length > 0 && (
        <div className="card-dark p-5 space-y-3">
          <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Data Dictionaries</h4>
          <p className="text-[10px] text-gray-500">Edit JSON values directly. Changes are saved when you click "Save Changes".</p>
          <div className="max-h-96 overflow-y-auto space-y-3">
            {Object.entries(editableTerms).map(([key, value]) => {
              // Determine if this is a JSON object/array or a simple value
              const isMultiLine = value.includes('\n') || value.length > 80;
              return (
                <div key={key} className="border border-gray-700 rounded-lg p-3">
                  <label className="block text-xs font-semibold text-gray-300 mb-1 capitalize">
                    {key.replace(/_/g, ' ')}
                  </label>
                  {isMultiLine ? (
                    <textarea
                      value={value}
                      onChange={e => handleTermChange(key, e.target.value)}
                      rows={Math.min(10, value.split('\n').length + 1)}
                      className="input-dark text-xs font-mono resize-y w-full"
                    />
                  ) : (
                    <input
                      value={value}
                      onChange={e => handleTermChange(key, e.target.value)}
                      className="input-dark text-xs w-full"
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
