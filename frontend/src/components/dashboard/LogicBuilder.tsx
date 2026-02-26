import React, { useState, useEffect } from 'react';
import CreatableSelect from 'react-select/creatable';
import api from '../../services/api';

interface LogicNode {
    type: 'AND' | 'OR' | 'CONDITION';
    dimension?: string;
    value?: string;
    children?: LogicNode[];
}

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
    const [dropdownValues, setDropdownValues] = useState<any>(null);
    const [selectedRuleId, setSelectedRuleId] = useState<string>('');
    const [tree, setTree] = useState<LogicNode | null>(null);
    const [ruleName, setRuleName] = useState<string>('');
    const [ruleDescription, setRuleDescription] = useState<string>('');
    const [outcome, setOutcome] = useState<'permission' | 'prohibition'>('permission');
    const [attributes, setAttributes] = useState<string[]>([]);
    const [enabled, setEnabled] = useState<boolean>(true);
    const [requiresPii, setRequiresPii] = useState<boolean>(false);
    const [validUntil, setValidUntil] = useState<string>('');
    const [requiredAssessments, setRequiredAssessments] = useState<string[]>([]);
    const [requiredActions, setRequiredActions] = useState<string[]>([]);

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

    const handleSelectRule = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const id = e.target.value;
        setSelectedRuleId(id);
        const rule = rules.find(r => r.rule_id === id);

        if (rule) {
            setRuleName(rule.name || '');
            setRuleDescription(rule.description || '');
            setOutcome(rule.outcome === 'prohibition' ? 'prohibition' : 'permission');
            setAttributes(rule.linked_attributes || []);
            setEnabled(rule.enabled ?? true);
            setRequiresPii(rule.requires_pii ?? false);
            setValidUntil(rule.valid_until || '');
            setRequiredAssessments(rule.required_assessments || []);
            setRequiredActions(rule.required_actions || []);
        } else {
            setRuleName('');
            setRuleDescription('');
            setOutcome('permission');
            setAttributes([]);
            setEnabled(true);
            setRequiresPii(false);
            setValidUntil('');
            setRequiredAssessments([]);
            setRequiredActions([]);
        }

        if (rule?.logic_tree) {
            try {
                setTree(JSON.parse(rule.logic_tree));
            } catch (e) {
                setTree({ type: 'AND', children: [] });
            }
        } else if (rule && (rule.origin_scopes?.length || rule.receiving_scopes?.length || rule.required_assessments?.length)) {
            // Hydrate a legacy rule into a logic tree structure
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
        setError(null);
        setSuccess(false);
    };

    const saveTree = async () => {
        if (!selectedRuleId || !tree) return;
        setSaving(true);
        setError(null);
        setSuccess(false);
        try {
            await api.put(`/admin/rules/${selectedRuleId}`, {
                name: ruleName,
                description: ruleDescription,
                logic_tree: tree,
                outcome,
                linked_attributes: attributes,
                enabled,
                requires_pii: requiresPii,
                valid_until: validUntil,
                required_assessments: requiredAssessments,
                required_actions: requiredActions
            });
            setSuccess(true);
            // Update local rules cache
            setRules(rules.map(r => r.rule_id === selectedRuleId ? {
                ...r,
                name: ruleName,
                description: ruleDescription,
                logic_tree: JSON.stringify(tree),
                outcome,
                linked_attributes: attributes,
                enabled,
                requires_pii: requiresPii,
                valid_until: validUntil,
                required_assessments: requiredAssessments,
                required_actions: requiredActions
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
            await fetchRules(); // To get the new rule in the list
            setSelectedRuleId(newRuleId); // Auto-select it
            setTree({ type: 'AND', children: [] });
            setRuleName('New Custom Rule');
            setRuleDescription('');
            setOutcome('permission');
            setAttributes([]);
            setEnabled(true);
            setRequiresPii(false);
            setValidUntil('');
            setRequiredAssessments([]);
            setRequiredActions([]);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to create new rule');
        } finally {
            setSaving(false);
        }
    };

    // Extract values dynamically from stringified logic trees
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

    const uniqueCountries = Array.from(new Set(rules.flatMap(r => [...(r.origin_scopes || []), ...(r.receiving_scopes || []), ...extractFromTree(r.logic_tree, 'OriginCountry'), ...extractFromTree(r.logic_tree, 'ReceivingCountry')]))).filter(Boolean).sort();
    const uniqueRegulators = Array.from(new Set(rules.flatMap(r => extractFromTree(r.logic_tree, 'Regulator')))).filter(Boolean).sort();
    const uniqueAuthorities = Array.from(new Set(rules.flatMap(r => extractFromTree(r.logic_tree, 'Authority')))).filter(Boolean).sort();

    const filteredRules = rules.filter(r => {
        let match = true;
        if (filterCountry) {
            const hasCountry = r.origin_scopes?.includes(filterCountry) || r.receiving_scopes?.includes(filterCountry) || extractFromTree(r.logic_tree, 'OriginCountry').includes(filterCountry) || extractFromTree(r.logic_tree, 'ReceivingCountry').includes(filterCountry);
            if (!hasCountry) match = false;
        }
        if (filterRegulator && !extractFromTree(r.logic_tree, 'Regulator').includes(filterRegulator)) match = false;
        if (filterAuthority && !extractFromTree(r.logic_tree, 'Authority').includes(filterAuthority)) match = false;
        return match;
    });

    const updateNode = (path: number[], newNode: LogicNode) => {
        if (!tree) return;
        const newTree = JSON.parse(JSON.stringify(tree));

        let current: any = newTree;
        for (let i = 0; i < path.length; i++) {
            if (i === path.length - 1) {
                current.children[path[i]] = newNode;
            } else {
                current = current.children[path[i]];
            }
        }
        setTree(newTree);
    };

    const removeNode = (path: number[]) => {
        if (!tree || path.length === 0) return;
        const newTree = JSON.parse(JSON.stringify(tree));

        let current: any = newTree;
        for (let i = 0; i < path.length - 1; i++) {
            current = current.children[path[i]];
        }
        current.children.splice(path[path.length - 1], 1);
        setTree(newTree);
    };

    const addChildNode = (path: number[], child: LogicNode) => {
        if (!tree) return;
        // if root
        if (path.length === 0) {
            const newTree = JSON.parse(JSON.stringify(tree));
            if (!newTree.children) newTree.children = [];
            newTree.children.push(child);
            setTree(newTree);
            return;
        }

        const newTree = JSON.parse(JSON.stringify(tree));
        let current: any = newTree;
        for (let i = 0; i < path.length; i++) {
            current = current.children[path[i]];
        }
        if (!current.children) current.children = [];
        current.children.push(child);
        setTree(newTree);
    };

    // Helper to translate dimension into an array of options
    const getOptionsForDimension = (dim: string) => {
        if (!dropdownValues) return [];
        if (dim === 'OriginCountry' || dim === 'ReceivingCountry') {
            return dropdownValues.countries?.map((c: string) => ({ value: c, label: c })) || [];
        }
        if (dim === 'LegalEntity') {
            const le: string[] = [];
            for (const country in dropdownValues.legal_entities) {
                dropdownValues.legal_entities[country].forEach((entity: string) => le.push(entity));
            }
            return Array.from(new Set(le)).map(v => ({ value: v, label: v }));
        }
        if (dim === 'DataCategory') {
            return dropdownValues.data_categories?.map((dc: any) => ({ value: dc.name, label: dc.name })) || [];
        }
        if (dim === 'Purpose') {
            return dropdownValues.purposes?.map((p: string) => ({ value: p, label: p })) || [];
        }
        if (dim === 'Process') {
            const allProcs = [...(dropdownValues.processes?.l1 || []), ...(dropdownValues.processes?.l2 || []), ...(dropdownValues.processes?.l3 || [])];
            return Array.from(new Set(allProcs)).map(p => ({ value: p as string, label: p as string }));
        }
        if (dim === 'DataSubject') {
            return dropdownValues.data_subjects?.map((ds: any) => ({ value: ds.name, label: ds.name })) || [];
        }
        if (dim === 'Regulator') {
            return dropdownValues.regulators?.map((r: any) => ({ value: r.name, label: r.name })) || [];
        }
        if (dim === 'Authority') {
            return dropdownValues.authorities?.map((a: any) => ({ value: a.name, label: a.name })) || [];
        }
        return [];
    };

    const renderNode = (node: LogicNode, path: number[] = []) => {
        if (node.type === 'CONDITION') {
            return (
                <div key={path.join('-')} className="flex items-center gap-2 p-2 bg-white border border-gray-200 rounded-lg shadow-sm w-full max-w-3xl group">
                    <span className="text-xs font-semibold text-gray-400 w-16 text-right">IF</span>
                    <select
                        value={node.dimension || ''}
                        onChange={(e) => updateNode(path, { ...node, dimension: e.target.value })}
                        className="text-sm border border-gray-200 rounded-md px-3 py-1.5 w-48 hover:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-100 transition-colors shadow-sm bg-white"
                    >
                        <option value="">Dimension...</option>
                        <optgroup label="Core Geography">
                            <option value="OriginCountry">Origin Country</option>
                            <option value="ReceivingCountry">Receiving Country</option>
                            <option value="LegalEntity">Legal Entity</option>
                        </optgroup>
                        <optgroup label="Data Types">
                            <option value="DataCategory">Data Category</option>
                            <option value="Purpose">Purpose of Processing</option>
                            <option value="Process">Process</option>
                            <option value="DataSubject">Data Subject</option>
                        </optgroup>
                        <optgroup label="Regulatory">
                            <option value="Regulator">Regulator</option>
                            <option value="Authority">Authority</option>
                        </optgroup>
                    </select>
                    <span className="text-xs text-gray-500 font-mono px-2">IN</span>
                    <div className="flex-1 min-w-[300px] relative z-20">
                        {node.dimension ? (
                            <CreatableSelect
                                isMulti
                                options={getOptionsForDimension(node.dimension)}
                                value={node.value ? node.value.split(',').map(v => ({ value: v.trim(), label: v.trim() })).filter(v => v.value) : []}
                                onChange={(newValue: any) => {
                                    const strValue = newValue ? newValue.map((item: any) => item.value).join(', ') : '';
                                    updateNode(path, { ...node, value: strValue });
                                }}
                                onCreateOption={async (val) => {
                                    // Optimistic UI update
                                    const strValue = node.value ? `${node.value}, ${val}` : val;
                                    updateNode(path, { ...node, value: strValue });
                                    try {
                                        await api.post('/metadata/nodes', { dimension: node.dimension, value: val });
                                        fetchDropdowns(); // Refresh list to include new creation
                                    } catch (e) {
                                        console.error('Failed to create metadata node', e);
                                    }
                                }}
                                styles={{
                                    control: (base) => ({
                                        ...base,
                                        borderColor: '#e5e7eb',
                                        boxShadow: 'none',
                                        minHeight: '34px',
                                        '&:hover': { borderColor: '#60a5fa' }
                                    }),
                                    multiValue: (base) => ({
                                        ...base,
                                        backgroundColor: '#eff6ff',
                                        borderRadius: '0.375rem',
                                    }),
                                    multiValueRemove: (base) => ({
                                        ...base,
                                        color: '#3b82f6',
                                        '&:hover': {
                                            backgroundColor: '#dbeafe',
                                            color: '#1d4ed8'
                                        }
                                    }),
                                    menu: (base) => ({
                                        ...base,
                                        zIndex: 50
                                    })
                                }}
                                placeholder="Select or type to create..."
                            />
                        ) : (
                            <input
                                type="text"
                                disabled
                                placeholder="Select a dimension first..."
                                className="text-sm border border-gray-200 rounded-md px-3 py-1.5 w-full bg-gray-50 text-gray-400 shadow-sm"
                            />
                        )}
                    </div>
                    <button onClick={() => removeNode(path)} className="text-gray-300 hover:text-red-500 p-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 rounded-full hover:bg-red-50" title="Remove Condition">
                        &times;
                    </button>
                </div>
            );
        }

        // Group node (AND/OR)
        return (
            <div key={path.join('-')} className={`p-5 rounded-xl border w-full transition-all duration-300 ease-in-out shadow-sm
                ${path.length === 0 ? 'bg-gradient-to-br from-purple-50/50 to-purple-50/30 border-purple-100' : 'bg-white border-dashed border-gray-200'} mb-4`}>
                <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-3">
                        <select
                            value={node.type}
                            onChange={(e) => {
                                if (path.length === 0) {
                                    setTree({ ...tree!, type: e.target.value as 'AND' | 'OR' });
                                } else {
                                    updateNode(path, { ...node, type: e.target.value as 'AND' | 'OR' });
                                }
                            }}
                            className={`font-semibold text-sm rounded-lg px-3 py-1.5 border shadow-sm transition-colors cursor-pointer outline-none focus:ring-2 
                                ${node.type === 'AND' ? 'bg-purple-600 text-white border-purple-700 hover:bg-purple-700 focus:ring-purple-200' : 'bg-amber-500 text-white border-amber-600 hover:bg-amber-600 focus:ring-amber-200'}`}
                        >
                            <option value="AND">ALL of the following (AND)</option>
                            <option value="OR">ANY of the following (OR)</option>
                        </select>
                    </div>
                    {path.length > 0 && (
                        <button onClick={() => removeNode(path)} className="text-sm text-red-500 font-medium hover:text-red-700 transition-colors bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-lg border border-red-100">
                            Delete Group
                        </button>
                    )}
                </div>

                <div className="pl-6 border-l-[3px] border-purple-100/60 ml-2 space-y-4">
                    {node.children && node.children.map((child, idx) => <React.Fragment key={idx}>{renderNode(child, [...path, idx])}</React.Fragment>)}

                    <div className="flex gap-3 pt-3">
                        <button
                            onClick={() => addChildNode(path, { type: 'CONDITION', dimension: 'OriginCountry', value: '' })}
                            className="text-xs bg-white border border-gray-200 shadow-sm px-4 py-2 rounded-lg font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all flex items-center gap-1.5"
                        >
                            <span className="text-purple-500 font-bold">+</span> Add Condition
                        </button>
                        <button
                            onClick={() => addChildNode(path, { type: 'AND', children: [] })}
                            className="text-xs bg-white border border-gray-200 shadow-sm px-4 py-2 rounded-lg font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all flex items-center gap-1.5"
                        >
                            <span className="text-green-500 font-bold">+</span> Add Sub-Group
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="h-full flex flex-col w-full max-w-7xl mx-auto">
            <div className="flex justify-between items-start bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-6 shrink-0">
                <div className="flex-1">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Rule Logic Selection</h2>

                    <div className="flex flex-wrap gap-4 mb-4">
                        <select
                            value={filterCountry}
                            onChange={(e) => { setFilterCountry(e.target.value); setSelectedRuleId(''); setTree(null); }}
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-purple-500 focus:border-purple-500 block p-2 transition-colors w-48 hover:bg-white"
                        >
                            <option value="">All Countries</option>
                            {uniqueCountries.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>

                        <select
                            value={filterRegulator}
                            onChange={(e) => { setFilterRegulator(e.target.value); setSelectedRuleId(''); setTree(null); }}
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-purple-500 focus:border-purple-500 block p-2 transition-colors w-48 hover:bg-white"
                        >
                            <option value="">All Regulators</option>
                            {uniqueRegulators.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>

                        <select
                            value={filterAuthority}
                            onChange={(e) => { setFilterAuthority(e.target.value); setSelectedRuleId(''); setTree(null); }}
                            className="bg-gray-50 border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-purple-500 focus:border-purple-500 block p-2 transition-colors w-48 hover:bg-white"
                        >
                            <option value="">All Authorities</option>
                            {uniqueAuthorities.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                    </div>

                    <select
                        value={selectedRuleId}
                        onChange={handleSelectRule}
                        className="w-full max-w-2xl rounded-lg border-2 border-purple-100 bg-purple-50/30 px-4 py-2.5 text-sm font-medium text-gray-800 focus:ring-purple-500 focus:border-purple-500 transition-colors shadow-sm"
                    >
                        <option value="">-- Select a Rule to Edit --</option>
                        {filteredRules.map(r => (
                            <option key={r.rule_id} value={r.rule_id}>
                                {r.name} ({r.rule_id}) [{r.outcome?.toUpperCase()}]
                            </option>
                        ))}
                    </select>
                    {loading && <span className="ml-3 text-sm text-gray-500">Loading rules...</span>}
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={handleCreateRule}
                        disabled={saving}
                        className="px-6 py-2 bg-white text-purple-700 border border-purple-200 rounded-lg text-sm font-medium hover:bg-purple-50 disabled:opacity-50 transition-colors whitespace-nowrap"
                    >
                        {saving ? 'Wait...' : '+ Create New Rule'}
                    </button>
                    <button
                        onClick={saveTree}
                        disabled={!selectedRuleId || saving}
                        className="px-6 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 min-w-[120px]"
                    >
                        {saving ? 'Saving...' : 'Save Logic to Graph'}
                    </button>
                </div>
            </div>

            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
            {success && <p className="mt-2 text-sm text-green-600">Successfully updated logic tree.</p>}

            {selectedRuleId && tree && (
                <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
                    {/* Left: Main Logic Tree Editor component */}
                    <div className="mt-2 bg-white rounded-xl border border-gray-200 p-6 shadow-sm overflow-hidden flex-1 min-h-0 flex flex-col">
                        <p className="text-xs text-gray-500 mb-4 pb-2 border-b border-gray-100 flex-shrink-0">
                            Use this visual builder to define complex trigger conditions. This overrides basic Excel imports.
                        </p>
                        <div className="overflow-y-auto flex-1 pb-12 pr-2">
                            {renderNode(tree)}
                        </div>
                    </div>

                    {/* Right: Rule Configuration Side Panel */}
                    <div className="w-96 flex-shrink-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-100 p-6 flex flex-col gap-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] ring-1 ring-gray-900/5 overflow-y-auto min-h-0">
                        <div className="pb-4 border-b border-gray-100 flex-shrink-0">
                            <h3 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 flex items-center gap-2">
                                <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                                Configuration
                            </h3>
                            <p className="text-xs text-gray-500 mt-1">Properties linked to this rule execution lifecycle.</p>
                        </div>

                        <div className="space-y-4">
                            <label className="block text-sm font-semibold text-gray-800">Rule Name</label>
                            <input
                                type="text"
                                value={ruleName}
                                onChange={(e) => setRuleName(e.target.value)}
                                className="w-full text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm px-3 py-2 outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                            />
                        </div>

                        <div className="space-y-4 pt-4 border-t border-gray-100">
                            <label className="block text-sm font-semibold text-gray-800">Rule Description</label>
                            <textarea
                                value={ruleDescription}
                                onChange={(e) => setRuleDescription(e.target.value)}
                                rows={2}
                                className="w-full text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm px-3 py-2 outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                            />
                        </div>

                        <div className="space-y-4 pt-4 border-t border-gray-100">
                            <label className="block text-sm font-semibold text-gray-800">Rule Outcome</label>
                            <div className="flex bg-gray-100 p-1 rounded-lg">
                                <button
                                    onClick={() => setOutcome('permission')}
                                    className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${outcome === 'permission' ? 'bg-white text-green-700 shadow-sm ring-1 ring-black/5' : 'text-gray-500 hover:text-gray-700'}`}
                                >
                                    Permission
                                </button>
                                <button
                                    onClick={() => setOutcome('prohibition')}
                                    className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${outcome === 'prohibition' ? 'bg-white text-red-600 shadow-sm ring-1 ring-black/5' : 'text-gray-500 hover:text-gray-700'}`}
                                >
                                    Prohibition
                                </button>
                            </div>
                            <p className="text-xs text-gray-400">Determines if this rule contributes to allowing or denying the workflow.</p>
                        </div>

                        <div className="space-y-4 pt-4 border-t border-gray-100">
                            <label className="block text-sm font-semibold text-gray-800">Rule Attributes</label>
                            <CreatableSelect
                                isMulti
                                options={dropdownValues?.attributes?.map((a: string) => ({ value: a, label: a })) || []}
                                value={attributes.map(a => ({ value: a, label: a }))}
                                onChange={(newVal) => {
                                    setAttributes(newVal ? newVal.map((n: any) => n.value) : []);
                                }}
                                styles={{
                                    control: (base) => ({
                                        ...base,
                                        borderColor: '#e5e7eb',
                                        boxShadow: 'none',
                                        '&:hover': { borderColor: '#a78bfa' },
                                        minHeight: '42px'
                                    }),
                                    multiValue: (base) => ({
                                        ...base,
                                        backgroundColor: '#f3e8ff',
                                        borderRadius: '0.375rem',
                                    }),
                                    multiValueRemove: (base) => ({
                                        ...base,
                                        color: '#9333ea',
                                        '&:hover': { backgroundColor: '#e9d5ff', color: '#7e22ce' }
                                    }),
                                    menu: (base) => ({ ...base, zIndex: 50 })
                                }}
                                placeholder="E.g. SensitiveData, VIP..."
                                className="text-sm"
                            />
                            <p className="text-xs text-gray-400">Dynamically add categorical markers or attributes to this rule using JSON keys.</p>
                        </div>

                        <div className="space-y-4 pt-4 border-t border-gray-100">
                            <label className="block text-sm font-semibold text-gray-800">Required Duties (PIA/TIA/HRPR)</label>
                            <CreatableSelect
                                isMulti
                                options={['PIA', 'TIA', 'HRPR'].map((a: string) => ({ value: a, label: a }))}
                                value={requiredAssessments.map(a => ({ value: a, label: a }))}
                                onChange={(newVal) => {
                                    setRequiredAssessments(newVal ? newVal.map((n: any) => n.value.toUpperCase()) : []);
                                }}
                                styles={{
                                    control: (base) => ({
                                        ...base,
                                        borderColor: '#E5E7EB',
                                        borderRadius: '0.5rem',
                                        minHeight: '42px'
                                    })
                                }}
                                placeholder="Add Module (e.g., PIA)..."
                            />

                            <label className="block text-sm font-semibold text-gray-800 mt-3">Required Actions</label>
                            <CreatableSelect
                                isMulti
                                options={dropdownValues?.actions?.map((a: string) => ({ value: a, label: a })) || []}
                                value={requiredActions.map(a => ({ value: a, label: a }))}
                                onChange={(newVal) => {
                                    setRequiredActions(newVal ? newVal.map((n: any) => n.value) : []);
                                }}
                                styles={{
                                    control: (base) => ({
                                        ...base,
                                        borderColor: '#E5E7EB',
                                        borderRadius: '0.5rem',
                                        minHeight: '42px'
                                    })
                                }}
                                placeholder="Add Security Duty..."
                            />
                        </div>

                        <div className="space-y-4 pt-4 border-t border-gray-100 mb-8">
                            <label className="flex items-center space-x-3 bg-gray-50 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors shadow-sm">
                                <input
                                    type="checkbox"
                                    checked={requiresPii}
                                    onChange={(e) => setRequiresPii(e.target.checked)}
                                    className="w-4 h-4 text-purple-600 bg-white border-gray-300 rounded focus:ring-purple-500 outline-none"
                                />
                                <span className="text-sm font-medium text-gray-800">Requires Personal Data (PII)</span>
                            </label>

                            <label className="flex items-center space-x-3 bg-gray-50 p-3 rounded-lg border border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors shadow-sm">
                                <input
                                    type="checkbox"
                                    checked={enabled}
                                    onChange={(e) => setEnabled(e.target.checked)}
                                    className="w-4 h-4 text-green-600 bg-white border-gray-300 rounded focus:ring-green-500 outline-none"
                                />
                                <span className="text-sm font-medium text-gray-800">Rule is Active / Enabled</span>
                            </label>

                            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 shadow-sm">
                                <label className="block text-sm font-medium text-gray-800 mb-2">Valid Until Date</label>
                                <input
                                    type="date"
                                    value={validUntil}
                                    onChange={(e) => setValidUntil(e.target.value)}
                                    className="w-full text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm px-3 py-2 outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
                                />
                                <p className="text-xs text-gray-400 mt-2">Leave blank for permanent enforcement.</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
