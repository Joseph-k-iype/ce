import { useState, useEffect, useCallback } from 'react';
import { useWizardStore } from '../../../stores/wizardStore';
import { useDropdownData } from '../../../hooks/useDropdownData';
import { DataDictionaryEditor } from '../DataDictionaryEditor';
import { editRule, editTerms, getTriggerLogic, getLogicTree, updateLogicTree, getGraphTriggerMappings } from '../../../services/wizardApi';
import type { GraphTriggerMapping } from '../../../services/wizardApi';
import { LogicTreeBuilder } from '../../shared/LogicTreeBuilder';
import { DIMENSION_CONFIGS } from '../../../services/dimensionConfig';
import type { TriggerLogicResponse } from '../../../types/wizard';
import type { LogicNode } from '../../shared/LogicTreeBuilder/types';

export function Step4Review() {
  const { data: dropdowns, isLoading: dropdownsLoading, error: dropdownsError } = useDropdownData();
  const {
    editedRuleDefinition,
    editedTermsDictionary,
    dictionaryResult,
    sessionId,
    dataCategories, purposesOfProcessing, processL1, processL2, processL3,
    groupDataCategories, sensitiveDataCategories, regulators, authorities, dataSubjects,
    setDataCategories, setPurposesOfProcessing, setProcessL1, setProcessL2, setProcessL3,
    setGroupDataCategories, setSensitiveDataCategories, setRegulators, setAuthorities, setDataSubjects,
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

  // Trigger logic state
  const [triggerLogic, setTriggerLogic] = useState<TriggerLogicResponse | null>(null);

  // Graph trigger mappings from Step 3
  const [graphMappings, setGraphMappings] = useState<GraphTriggerMapping[]>([]);

  // Logic tree state (visual editor)
  const [logicTree, setLogicTree] = useState<LogicNode>({ type: 'AND', children: [] });
  const [editingLogicTree, setEditingLogicTree] = useState(false);

  // Entity editing state
  const [editingEntities, setEditingEntities] = useState(false);

  // UI state
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Fetch trigger logic, logic tree, and graph trigger mappings in parallel
  useEffect(() => {
    if (!sessionId) return;
    Promise.all([
      getTriggerLogic(sessionId).catch(() => null),
      getLogicTree(sessionId).catch(() => null),
      getGraphTriggerMappings(sessionId).catch(() => null),
    ]).then(([triggerResult, treeResult, mappingsResult]) => {
      if (triggerResult) setTriggerLogic(triggerResult);
      if (treeResult) setLogicTree(treeResult);
      if (mappingsResult?.mappings) setGraphMappings(mappingsResult.mappings);
    });
  }, [sessionId]);

  const handleLogicTreeChange = useCallback(async (tree: LogicNode) => {
    setLogicTree(tree);
    // Auto-save logic tree changes
    if (sessionId) {
      try {
        await updateLogicTree(sessionId, tree);
      } catch (err) {
        console.error('Failed to save logic tree:', err);
      }
    }
  }, [sessionId]);

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


  const handleSave = async () => {
    if (!sessionId || !rule) return;
    setSaving(true);
    try {
      // Build updated rule from all editable fields — include entity dimension changes
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
        // Sync confirmed entity dimensions back into the rule definition
        data_categories: dataCategories,
        purposes_of_processing: purposesOfProcessing,
        processes: [...processL1, ...processL2, ...processL3].filter(Boolean),
        gdc: groupDataCategories,
        sensitive_data_categories: sensitiveDataCategories,
        regulators,
        authorities,
        data_subjects: dataSubjects,
        // Include visual logic tree
        logic_tree: logicTree,
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

      {/* Editable Entity Dimensions — always visible compact summary + expand-to-edit */}
      <div className="card-dark p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Entity Trigger Conditions</h4>
          <button
            onClick={() => setEditingEntities(prev => !prev)}
            className="text-xs text-purple-400 hover:text-purple-300 underline"
          >
            {editingEntities ? 'Collapse' : 'Edit conditions'}
          </button>
        </div>
        <p className="text-[10px] text-gray-500">
          These are the entity dimensions that will trigger this rule. Editing here updates your confirmed selections.
        </p>

        {/* Compact read-only summary — always visible */}
        {!editingEntities && (
          <div className="grid grid-cols-2 gap-2 text-xs">
            {[
              { label: 'Data Categories', values: dataCategories },
              { label: 'Purposes', values: purposesOfProcessing },
              { label: 'Process L1', values: processL1 },
              { label: 'Process L2', values: processL2 },
              { label: 'Process L3', values: processL3 },
              { label: 'GDC', values: groupDataCategories },
              { label: 'Sensitive Data', values: sensitiveDataCategories },
              { label: 'Regulators', values: regulators },
              { label: 'Authorities', values: authorities },
              { label: 'Data Subjects', values: dataSubjects },
            ].map(({ label, values }) => (
              <div key={label} className="flex items-start gap-2">
                <span className="text-gray-500 shrink-0 w-28">{label}:</span>
                {values.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {values.map(v => (
                      <span key={v} className="px-1.5 py-0.5 bg-purple-900/40 text-purple-300 rounded text-[10px]">{v}</span>
                    ))}
                  </div>
                ) : (
                  <span className="text-gray-600 italic">—</span>
                )}
              </div>
            ))}
          </div>
        )}

        {editingEntities && (
          <div className="space-y-4 pt-2">
            {/* Dropdown loading/error states */}
            {dropdownsLoading && (
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <div className="w-3 h-3 border border-purple-400 border-t-transparent rounded-full animate-spin" />
                Loading entity options from graph...
              </div>
            )}
            {dropdownsError && (
              <div className="px-3 py-2 bg-red-900/30 border border-red-700/50 rounded-lg text-xs text-red-300">
                Failed to load dropdown options. The graph may have no entity data yet.
                You can still type values manually after saving.
              </div>
            )}
            {!dropdownsLoading && !dropdownsError && !dropdowns && (
              <div className="px-3 py-2 bg-yellow-900/20 border border-yellow-700/30 rounded-lg text-xs text-yellow-300">
                No entity data found in the connected graph. Select a graph in Step 3 to populate options.
              </div>
            )}

            {/* Data Categories */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Data Categories</label>
                <select multiple value={dataCategories}
                  onChange={e => setDataCategories(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-20">
                  {(dropdowns?.data_categories || []).map((c: any) => {
                    const v = typeof c === 'string' ? c : c.name;
                    return <option key={v} value={v}>{v}</option>;
                  })}
                </select>
                {!dropdownsLoading && (dropdowns?.data_categories || []).length === 0 && (
                  <p className="text-[10px] text-gray-600 mt-0.5">No options — graph has no DataCategory nodes</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Purposes of Processing</label>
                <select multiple value={purposesOfProcessing}
                  onChange={e => setPurposesOfProcessing(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-20">
                  {(dropdowns?.purpose_of_processing || dropdowns?.purposes || []).map((p: any) => {
                    const v = typeof p === 'string' ? p : p.name;
                    return <option key={v} value={v}>{v}</option>;
                  })}
                </select>
                {!dropdownsLoading && (dropdowns?.purpose_of_processing || dropdowns?.purposes || []).length === 0 && (
                  <p className="text-[10px] text-gray-600 mt-0.5">No options — graph has no Purpose nodes</p>
                )}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Process L1</label>
                <select multiple value={processL1}
                  onChange={e => setProcessL1(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.processes?.l1 || []).map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Process L2</label>
                <select multiple value={processL2}
                  onChange={e => setProcessL2(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.processes?.l2 || []).map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Process L3</label>
                <select multiple value={processL3}
                  onChange={e => setProcessL3(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.processes?.l3 || []).map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Group Data Categories (GDC)</label>
                <select multiple value={groupDataCategories}
                  onChange={e => setGroupDataCategories(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.group_data_categories || []).map((g: any) => {
                    const v = typeof g === 'string' ? g : g.name;
                    return <option key={v} value={v}>{v}</option>;
                  })}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Sensitive Data Categories</label>
                <select multiple value={sensitiveDataCategories}
                  onChange={e => setSensitiveDataCategories(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.sensitive_data_categories || []).map((s: any) => {
                    const v = typeof s === 'string' ? s : s.name;
                    return <option key={v} value={v}>{v}</option>;
                  })}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Regulators</label>
                <select multiple value={regulators}
                  onChange={e => setRegulators(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.regulators || []).map((r: any) => {
                    const v = typeof r === 'string' ? r : r.name;
                    return <option key={v} value={v}>{v}</option>;
                  })}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Authorities</label>
                <select multiple value={authorities}
                  onChange={e => setAuthorities(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.authorities || []).map((a: any) => {
                    const v = typeof a === 'string' ? a : a.name;
                    return <option key={v} value={v}>{v}</option>;
                  })}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Data Subjects</label>
                <select multiple value={dataSubjects}
                  onChange={e => setDataSubjects(Array.from(e.target.selectedOptions, o => o.value))}
                  className="input-dark text-xs h-16">
                  {(dropdowns?.data_subjects || []).map((ds: any) => {
                    const v = typeof ds === 'string' ? ds : ds.name;
                    return <option key={v} value={v}>{v}</option>;
                  })}
                </select>
              </div>
            </div>
            <p className="text-[10px] text-gray-500">Changes take effect when you click "Save Changes" above.</p>
          </div>
        )}
      </div>

      {/* Entity Mapping Grid — AI suggestions vs. user confirmed */}
      <div className="card-dark p-5 space-y-3">
        <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Entity Mapping Review</h4>
        <p className="text-[10px] text-gray-500">AI-suggested entity mappings compared to your confirmed selections from Step 3.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-2 pr-4 text-gray-400 font-semibold w-36">Dimension</th>
                <th className="text-left py-2 pr-4 text-gray-400 font-semibold">AI Suggested</th>
                <th className="text-left py-2 text-gray-300 font-semibold">User Confirmed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {[
                { label: 'Data Categories', ai: (rule?.data_categories as string[]) || [], confirmed: dataCategories },
                { label: 'Purposes', ai: (rule?.purposes_of_processing as string[]) || [], confirmed: purposesOfProcessing },
                { label: 'Process L1', ai: (rule?.processes as string[]) || [], confirmed: processL1 },
                { label: 'Process L2', ai: [], confirmed: processL2 },
                { label: 'Process L3', ai: [], confirmed: processL3 },
                { label: 'GDC', ai: (rule?.gdc as string[]) || [], confirmed: groupDataCategories },
                { label: 'Regulators', ai: (rule?.regulators as string[]) || [], confirmed: regulators },
                { label: 'Authorities', ai: (rule?.authorities as string[]) || [], confirmed: authorities },
                { label: 'Data Subjects', ai: (rule?.data_subjects as string[]) || [], confirmed: dataSubjects },
                { label: 'Sensitive Data', ai: (rule?.sensitive_data_categories as string[]) || [], confirmed: sensitiveDataCategories },
              ].map(({ label, ai, confirmed }) => (
                <tr key={label} className="hover:bg-gray-800/30">
                  <td className="py-2 pr-4 text-gray-400 font-medium">{label}</td>
                  <td className="py-2 pr-4 text-gray-500">
                    {ai.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {ai.map(v => (
                          <span key={v} className="px-1.5 py-0.5 bg-purple-900/40 text-purple-300 rounded text-[10px]">{v}</span>
                        ))}
                      </div>
                    ) : <span className="text-gray-600 italic">—</span>}
                  </td>
                  <td className="py-2">
                    {confirmed.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {confirmed.map(v => (
                          <span key={v} className="px-1.5 py-0.5 bg-green-900/40 text-green-300 rounded text-[10px]">{v}</span>
                        ))}
                      </div>
                    ) : <span className="text-gray-600 italic">not selected</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Graph Trigger Conditions — from Step 3 data source configuration */}
      {graphMappings.length > 0 && (
        <div className="card-dark p-5 space-y-3">
          <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Graph Trigger Conditions</h4>
          <p className="text-[10px] text-gray-500">
            Conditions configured in Step 3 (data sources) that determine when this rule fires based on graph data.
          </p>
          <div className="space-y-3">
            {(() => {
              // Group mappings by graph_name
              const byGraph = graphMappings.reduce<Record<string, GraphTriggerMapping[]>>((acc, m) => {
                if (!acc[m.graph_name]) acc[m.graph_name] = [];
                acc[m.graph_name].push(m);
                return acc;
              }, {});
              return Object.entries(byGraph).map(([graphName, mappings]) => (
                <div key={graphName} className="bg-gray-900 border border-gray-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <svg className="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 3 8 3s8-.79 8-3V7M4 7c0 2.21 3.582 3 8 3s8-.79 8-3M4 7c0-2.21 3.582 3-8 3s8 .79 8 3" />
                    </svg>
                    <span className="text-xs font-semibold text-purple-300">{graphName}</span>
                  </div>
                  <div className="space-y-1.5">
                    {mappings.map((m, idx) => {
                      let conditions: Array<{ attribute: string; operator: string; values: string[] }> = [];
                      try {
                        const parsed = JSON.parse(m.filter_expr || '[]');
                        conditions = Array.isArray(parsed) ? parsed : [];
                      } catch {
                        conditions = m.filter_expr ? [{ attribute: m.field, operator: '=', values: [m.filter_expr] }] : [];
                      }
                      return (
                        <div key={idx} className="pl-3 border-l-2 border-gray-700">
                          <div className="flex items-center gap-1.5 mb-1">
                            <span className="text-[10px] text-gray-500">Node:</span>
                            <span className="text-[10px] font-medium text-gray-300 bg-gray-800 px-1.5 py-0.5 rounded">{m.node_label}</span>
                            {m.dimension && (
                              <>
                                <span className="text-[10px] text-gray-600">→</span>
                                <span className="text-[10px] text-blue-400">maps to: {m.dimension}</span>
                              </>
                            )}
                          </div>
                          {conditions.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {conditions.map((cond, ci) => (
                                <span key={ci} className="text-[10px] bg-purple-900/40 text-purple-200 px-2 py-0.5 rounded font-mono">
                                  {cond.attribute} {cond.operator} [{cond.values.join(', ')}]
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-[10px] text-gray-600 italic">No conditions — matches all {m.node_label} nodes</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ));
            })()}
          </div>
        </div>
      )}

      {/* Visual Logic Tree Builder — NEW! */}
      <div className="card-dark p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Rule Trigger Logic (Visual Editor)</h4>
            <p className="text-[10px] text-gray-500 mt-1">
              AI-generated logic tree showing when this rule triggers. Edit visually using AND/OR groups and conditions.
            </p>
          </div>
          <button
            onClick={() => setEditingLogicTree(prev => !prev)}
            className="text-xs text-purple-400 hover:text-purple-300 underline"
          >
            {editingLogicTree ? 'Collapse' : 'Edit logic tree'}
          </button>
        </div>

        {editingLogicTree && (
          <div className="pt-3">
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
              <LogicTreeBuilder
                initialTree={logicTree}
                dimensionConfigs={DIMENSION_CONFIGS}
                dropdownData={dropdowns || null}
                onChange={handleLogicTreeChange}
                mode="full"
              />
            </div>

            {/* Info box */}
            <div className="mt-4 p-3 bg-purple-900/20 border border-purple-700/30 rounded-lg">
              <div className="flex items-start gap-2">
                <svg className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="flex-1">
                  <p className="text-xs text-purple-200">
                    <strong>Visual Logic Editor:</strong> This logic tree was automatically generated from AI-extracted entity dimensions.
                    You can add, remove, or reorganize conditions using AND/OR groups to create complex matching rules.
                    Changes are saved automatically.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Trigger Logic — deterministic conditions display */}
      {triggerLogic && (
        <div className="card-dark p-5 space-y-3">
          <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Rule Trigger Logic (Text View)</h4>
          <p className="text-[10px] text-gray-500">
            This rule will fire when all geographic conditions match AND any one of the following entity dimensions matches.
          </p>
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 font-mono text-xs space-y-1.5">
            {/* Geography */}
            <div className="text-gray-300">
              <span className="text-yellow-400 font-semibold">WHEN</span>
              {' '}Origin:
              {triggerLogic.origin_countries.length > 0
                ? <span className="text-white ml-1">[{triggerLogic.origin_countries.join(', ')}]</span>
                : <span className="text-gray-500 ml-1">any</span>}
              {triggerLogic.origin_group && (
                <span className="text-gray-400 ml-1">(group: {triggerLogic.origin_group})</span>
              )}
            </div>
            <div className="text-gray-300 pl-4">
              <span className="text-yellow-400 font-semibold">AND</span>
              {' '}Receiving:
              {triggerLogic.receiving_countries.length > 0
                ? <span className="text-white ml-1">[{triggerLogic.receiving_countries.join(', ')}]</span>
                : <span className="text-gray-500 ml-1">any</span>}
              {triggerLogic.receiving_group && (
                <span className="text-gray-400 ml-1">(group: {triggerLogic.receiving_group})</span>
              )}
            </div>
            {/* Entity dimensions — OR logic */}
            <div className="text-gray-300 pl-4">
              <span className="text-yellow-400 font-semibold">AND ANY OF:</span>
            </div>
            {Object.entries(triggerLogic.dimensions).map(([key, values]) =>
              values.length > 0 ? (
                <div key={key} className="pl-8 text-gray-400">
                  <span className="text-purple-400">●</span>
                  {' '}<span className="text-gray-300">{key.replace(/_/g, ' ')}</span>
                  {' '}<span className="text-gray-500">is one of:</span>
                  {' '}<span className="text-green-300">[{values.join(', ')}]</span>
                </div>
              ) : null
            )}
            {triggerLogic.attribute_keywords_count > 0 && (
              <div className="pl-8 text-gray-400">
                <span className="text-purple-400">●</span>
                {' '}<span className="text-gray-300">attribute keywords</span>
                {' '}<span className="text-gray-500">matched</span>
                {' '}<span className="text-green-300">({triggerLogic.attribute_keywords_count} keywords)</span>
              </div>
            )}
            {/* PII requirement */}
            <div className="text-gray-400 pl-4">
              <span className="text-yellow-400 font-semibold">PII required:</span>
              {' '}<span className={triggerLogic.requires_pii ? 'text-orange-300' : 'text-gray-500'}>
                {triggerLogic.requires_pii ? 'yes' : 'no'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Data Dictionaries — Structured UI */}
      {Object.keys(editableTerms).length > 0 && (
        <DataDictionaryEditor
          terms={editableTerms}
          onChange={setEditableTerms}
        />
      )}
    </div>
  );
}
