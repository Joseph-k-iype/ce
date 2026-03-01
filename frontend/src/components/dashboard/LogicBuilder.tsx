/**
 * LogicBuilder Component (Refactored)
 *
 * Dashboard interface for editing rule logic trees.
 * Now uses the standardized LogicTreeBuilder component.
 */

import { useState, useEffect } from 'react';
import CreatableSelect from 'react-select/creatable';
import api from '../../services/api';
import { LogicTreeBuilder } from '../shared/LogicTreeBuilder';
import { DIMENSION_CONFIGS } from '../../services/dimensionConfig';
import type { LogicNode, DropdownDataResponse } from '../shared/LogicTreeBuilder/types';

interface Rule {
    rule_id: string;
    name: string;
    description: string;
    logic_tree?: string; // from backend it comes as JSON string
    origin_scopes?: string[];
    receiving_scopes?: string[];
    required_assessments?: string[];
    required_actions?: string[];
    outcome?: string;
    linked_attributes?: string[];
    enabled?: boolean;
    requires_pii?: boolean;
    valid_until?: string;
}

export function LogicBuilder() {
    const [rules, setRules] = useState<Rule[]>([]);
    const [dropdownValues, setDropdownValues] = useState<DropdownDataResponse | null>(null);
    const [selectedRuleId, setSelectedRuleId] = useState<string>('');
    const [currentRule, setCurrentRule] = useState<Rule | null>(null);
    const [tree, setTree] = useState<LogicNode>({ type: 'AND', children: [] });

    const [filterCountry, setFilterCountry] = useState<string>('');
    const [filterRegulator, setFilterRegulator] = useState<string>('');
    const [filterAuthority, setFilterAuthority] = useState<string>('');

    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        fetchRules();
        fetchDropdowns();
    }, []);

    const fetchDropdowns = async () => {
        try {
            const res = await api.get('/all-dropdown-values');
            setDropdownValues(res.data);
        } catch (err) {
            console.error('Failed to load dropdown values:', err);
        }
    };

    const fetchRules = async () => {
        try {
            setLoading(true);
            const res = await api.get('/admin/rules');
            setRules(res.data);
        } catch (err: any) {
            setError('Failed to fetch rules');
        } finally {
            setLoading(false);
        }
    };

    const handleSelectRule = (ruleId: string) => {
        setSelectedRuleId(ruleId);
        const rule = rules.find(r => r.rule_id === ruleId);

        if (rule) {
            setCurrentRule(rule);

            // Parse logic tree
            if (rule.logic_tree) {
                try {
                    setTree(JSON.parse(rule.logic_tree));
                } catch (e) {
                    setTree({ type: 'AND', children: [] });
                }
            } else if (rule.origin_scopes?.length || rule.receiving_scopes?.length) {
                // Hydrate legacy rule
                const newTree: LogicNode = { type: 'AND', children: [] };

                if (rule.origin_scopes && rule.origin_scopes.length > 0) {
                    const originGroup: LogicNode = { type: 'OR', children: [] };
                    rule.origin_scopes.forEach(country => {
                        originGroup.children!.push({ type: 'CONDITION', dimension: 'OriginCountry', value: country });
                    });
                    newTree.children!.push(originGroup);
                }

                if (rule.receiving_scopes && rule.receiving_scopes.length > 0) {
                    const receivingGroup: LogicNode = { type: 'OR', children: [] };
                    rule.receiving_scopes.forEach(country => {
                        receivingGroup.children!.push({ type: 'CONDITION', dimension: 'ReceivingCountry', value: country });
                    });
                    newTree.children!.push(receivingGroup);
                }

                setTree(newTree.children!.length ? newTree : { type: 'AND', children: [] });
            } else {
                setTree({ type: 'AND', children: [] });
            }
        } else {
            setCurrentRule(null);
            setTree({ type: 'AND', children: [] });
        }

        setError(null);
        setSuccess(false);
    };

    const handleSaveRule = async () => {
        if (!selectedRuleId || !currentRule) return;

        setSaving(true);
        setError(null);
        setSuccess(false);

        try {
            await api.put(`/admin/rules/${selectedRuleId}`, {
                name: currentRule.name,
                description: currentRule.description,
                logic_tree: tree,
                outcome: currentRule.outcome,
                linked_attributes: currentRule.linked_attributes || [],
                enabled: currentRule.enabled ?? true,
                requires_pii: currentRule.requires_pii ?? false,
                valid_until: currentRule.valid_until || '',
                required_assessments: currentRule.required_assessments || [],
                required_actions: currentRule.required_actions || []
            });

            setSuccess(true);

            // Update local cache
            setRules(rules.map(r => r.rule_id === selectedRuleId ? {
                ...r,
                ...currentRule,
                logic_tree: JSON.stringify(tree)
            } : r));
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save logic tree');
        } finally {
            setSaving(false);
        }
    };

    const handleCreateRule = async () => {
        setSaving(true);
        setError(null);
        setSuccess(false);

        try {
            const res = await api.post('/admin/rules/create');
            const newRuleId = res.data.rule_id;

            await fetchRules();

            const newRule: Rule = {
                rule_id: newRuleId,
                name: 'New Custom Rule',
                description: '',
                outcome: 'permission',
                linked_attributes: [],
                enabled: true,
                requires_pii: false,
                valid_until: '',
                required_assessments: [],
                required_actions: []
            };

            setCurrentRule(newRule);
            setSelectedRuleId(newRuleId);
            setTree({ type: 'AND', children: [] });
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create new rule');
        } finally {
            setSaving(false);
        }
    };

    // Extract values from logic tree for filtering
    const extractFromTree = (treeStr: string | undefined, dim: string): string[] => {
        if (!treeStr) return [];
        const regex = new RegExp(`"dimension":"${dim}","value":"([^"]+)"`, 'g');
        const matches: string[] = [];
        let match;
        while ((match = regex.exec(treeStr)) !== null) {
            matches.push(...match[1].split(',').map(s => s.trim()));
        }
        return matches;
    };

    const uniqueCountries = Array.from(new Set(
        rules.flatMap(r => [
            ...(r.origin_scopes || []),
            ...(r.receiving_scopes || []),
            ...extractFromTree(r.logic_tree, 'OriginCountry'),
            ...extractFromTree(r.logic_tree, 'ReceivingCountry')
        ])
    )).filter(Boolean).sort();

    const uniqueRegulators = Array.from(new Set(
        rules.flatMap(r => extractFromTree(r.logic_tree, 'Regulator'))
    )).filter(Boolean).sort();

    const uniqueAuthorities = Array.from(new Set(
        rules.flatMap(r => extractFromTree(r.logic_tree, 'Authority'))
    )).filter(Boolean).sort();

    const filteredRules = rules.filter(r => {
        let match = true;

        if (filterCountry) {
            const hasCountry =
                r.origin_scopes?.includes(filterCountry) ||
                r.receiving_scopes?.includes(filterCountry) ||
                extractFromTree(r.logic_tree, 'OriginCountry').includes(filterCountry) ||
                extractFromTree(r.logic_tree, 'ReceivingCountry').includes(filterCountry);
            if (!hasCountry) match = false;
        }

        if (filterRegulator && !extractFromTree(r.logic_tree, 'Regulator').includes(filterRegulator)) {
            match = false;
        }

        if (filterAuthority && !extractFromTree(r.logic_tree, 'Authority').includes(filterAuthority)) {
            match = false;
        }

        return match;
    });

    return (
        <div className="flex h-screen bg-gray-50">
            {/* Left Panel: Rule Selection */}
            <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto">
                <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-indigo-50">
                    <h2 className="text-lg font-bold text-gray-900 mb-3">Logic Builder</h2>

                    <button
                        onClick={handleCreateRule}
                        disabled={saving}
                        className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium shadow-sm"
                    >
                        + Create New Rule
                    </button>
                </div>

                {/* Filters */}
                <div className="p-4 space-y-3 border-b border-gray-200 bg-gray-50">
                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Filter by Country</label>
                        <select
                            value={filterCountry}
                            onChange={(e) => setFilterCountry(e.target.value)}
                            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2"
                        >
                            <option value="">All Countries</option>
                            {uniqueCountries.map(c => (
                                <option key={c} value={c}>{c}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Filter by Regulator</label>
                        <select
                            value={filterRegulator}
                            onChange={(e) => setFilterRegulator(e.target.value)}
                            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2"
                        >
                            <option value="">All Regulators</option>
                            {uniqueRegulators.map(r => (
                                <option key={r} value={r}>{r}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">Filter by Authority</label>
                        <select
                            value={filterAuthority}
                            onChange={(e) => setFilterAuthority(e.target.value)}
                            className="w-full text-sm border border-gray-300 rounded-md px-3 py-2"
                        >
                            <option value="">All Authorities</option>
                            {uniqueAuthorities.map(a => (
                                <option key={a} value={a}>{a}</option>
                            ))}
                        </select>
                    </div>

                    {(filterCountry || filterRegulator || filterAuthority) && (
                        <button
                            onClick={() => {
                                setFilterCountry('');
                                setFilterRegulator('');
                                setFilterAuthority('');
                            }}
                            className="text-xs text-purple-600 hover:text-purple-700"
                        >
                            Clear Filters
                        </button>
                    )}
                </div>

                {/* Rule List */}
                <div className="p-2">
                    {loading ? (
                        <p className="text-sm text-gray-500 text-center py-4">Loading rules...</p>
                    ) : filteredRules.length === 0 ? (
                        <p className="text-sm text-gray-500 text-center py-4">No rules found</p>
                    ) : (
                        <div className="space-y-2">
                            {filteredRules.map(rule => (
                                <button
                                    key={rule.rule_id}
                                    onClick={() => handleSelectRule(rule.rule_id)}
                                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                                        selectedRuleId === rule.rule_id
                                            ? 'bg-purple-100 border-2 border-purple-500 text-purple-900'
                                            : 'bg-white border border-gray-200 hover:bg-gray-50 text-gray-700'
                                    }`}
                                >
                                    <div className="font-medium truncate">{rule.name}</div>
                                    <div className="text-xs text-gray-500 truncate mt-1">
                                        {rule.rule_id}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Middle Panel: Logic Tree Editor */}
            {currentRule ? (
                <div className="flex-1 flex flex-col overflow-hidden">
                    {/* Status Bar */}
                    <div className="bg-white border-b border-gray-200 px-6 py-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900">{currentRule.name}</h3>
                                <p className="text-sm text-gray-500">Edit trigger logic using visual builder</p>
                            </div>

                            <div className="flex items-center gap-3">
                                {success && (
                                    <span className="text-sm text-green-600 flex items-center gap-1">
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        Saved!
                                    </span>
                                )}

                                {error && (
                                    <span className="text-sm text-red-600">{error}</span>
                                )}

                                <button
                                    onClick={handleSaveRule}
                                    disabled={saving}
                                    className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium shadow-sm"
                                >
                                    {saving ? 'Saving...' : 'Save Rule'}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Logic Tree Builder */}
                    <div className="flex-1 overflow-y-auto p-6">
                        <LogicTreeBuilder
                            initialTree={tree}
                            dimensionConfigs={DIMENSION_CONFIGS}
                            dropdownData={dropdownValues}
                            onChange={setTree}
                            mode="full"
                        />
                    </div>
                </div>
            ) : (
                <div className="flex-1 flex items-center justify-center bg-gray-50">
                    <div className="text-center text-gray-500">
                        <svg className="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <p className="text-lg font-medium">No rule selected</p>
                        <p className="text-sm mt-2">Select a rule from the list or create a new one</p>
                    </div>
                </div>
            )}

            {/* Right Panel: Metadata */}
            {currentRule && (
                <div className="w-96 bg-white border-l border-gray-200 overflow-y-auto">
                    <div className="p-6 space-y-6">
                        <h3 className="text-lg font-bold text-gray-900">Rule Metadata</h3>

                        {/* Basic Info */}
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-semibold text-gray-800 mb-2">Rule Name</label>
                                <input
                                    type="text"
                                    value={currentRule.name}
                                    onChange={(e) => setCurrentRule({ ...currentRule, name: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-semibold text-gray-800 mb-2">Description</label>
                                <textarea
                                    value={currentRule.description}
                                    onChange={(e) => setCurrentRule({ ...currentRule, description: e.target.value })}
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-semibold text-gray-800 mb-2">Outcome</label>
                                <select
                                    value={currentRule.outcome || 'permission'}
                                    onChange={(e) => setCurrentRule({ ...currentRule, outcome: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                                >
                                    <option value="permission">Permission</option>
                                    <option value="prohibition">Prohibition</option>
                                </select>
                            </div>
                        </div>

                        {/* Linked Attributes */}
                        <div className="pt-4 border-t border-gray-100">
                            <label className="block text-sm font-semibold text-gray-800 mb-2">Linked Attributes</label>
                            <CreatableSelect
                                isMulti
                                value={(currentRule.linked_attributes || []).map(a => ({ value: a, label: a }))}
                                onChange={(newVal) => {
                                    setCurrentRule({
                                        ...currentRule,
                                        linked_attributes: newVal ? newVal.map((n: any) => n.value) : []
                                    });
                                }}
                                placeholder="E.g. SensitiveData, VIP..."
                                className="text-sm"
                            />
                        </div>

                        {/* Duties */}
                        <div className="pt-4 border-t border-gray-100 space-y-4">
                            <div>
                                <label className="block text-sm font-semibold text-gray-800 mb-2">Required Assessments (PIA/TIA/HRPR)</label>
                                <CreatableSelect
                                    isMulti
                                    options={['PIA', 'TIA', 'HRPR'].map(a => ({ value: a, label: a }))}
                                    value={(currentRule.required_assessments || []).map(a => ({ value: a, label: a }))}
                                    onChange={(newVal) => {
                                        setCurrentRule({
                                            ...currentRule,
                                            required_assessments: newVal ? newVal.map((n: any) => n.value.toUpperCase()) : []
                                        });
                                    }}
                                    placeholder="Add Module (e.g., PIA)..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-semibold text-gray-800 mb-2">Required Actions</label>
                                <CreatableSelect
                                    isMulti
                                    options={dropdownValues?.actions?.map((a: string) => ({ value: a, label: a })) || []}
                                    value={(currentRule.required_actions || []).map(a => ({ value: a, label: a }))}
                                    onChange={(newVal) => {
                                        setCurrentRule({
                                            ...currentRule,
                                            required_actions: newVal ? newVal.map((n: any) => n.value) : []
                                        });
                                    }}
                                    placeholder="Add Security Duty..."
                                />
                            </div>
                        </div>

                        {/* Flags */}
                        <div className="pt-4 border-t border-gray-100 space-y-3">
                            <label className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-100">
                                <input
                                    type="checkbox"
                                    checked={currentRule.requires_pii ?? false}
                                    onChange={(e) => setCurrentRule({ ...currentRule, requires_pii: e.target.checked })}
                                    className="w-4 h-4 text-purple-600"
                                />
                                <span className="text-sm font-medium text-gray-800">Requires Personal Data (PII)</span>
                            </label>

                            <label className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-100">
                                <input
                                    type="checkbox"
                                    checked={currentRule.enabled ?? true}
                                    onChange={(e) => setCurrentRule({ ...currentRule, enabled: e.target.checked })}
                                    className="w-4 h-4 text-green-600"
                                />
                                <span className="text-sm font-medium text-gray-800">Rule is Active / Enabled</span>
                            </label>

                            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                                <label className="block text-sm font-medium text-gray-800 mb-2">Valid Until Date</label>
                                <input
                                    type="date"
                                    value={currentRule.valid_until || ''}
                                    onChange={(e) => setCurrentRule({ ...currentRule, valid_until: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                                />
                                <p className="text-xs text-gray-500 mt-1">Leave blank for permanent enforcement</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
