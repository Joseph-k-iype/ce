/**
 * GraphTriggerMappingPanel (redesigned)
 * ======================================
 * Condition builder for defining when a graph node should trigger a rule.
 * Supports multi-condition groups with AND/OR logic, similar to the rule
 * trigger logic tree builder.
 */

import { useState, useEffect, useCallback } from 'react';
import type { GraphTriggerMapping } from '../../services/wizardApi';

const OPERATORS = [
  { value: 'equals', label: '=' },
  { value: 'not_equals', label: '≠' },
  { value: 'in', label: 'in' },
  { value: 'not_in', label: 'not in' },
  { value: 'contains', label: 'contains' },
] as const;

type Operator = typeof OPERATORS[number]['value'];

interface Condition {
  id: string;
  attribute: string;
  operator: Operator;
  values: string[];
}

interface ConditionGroup {
  id: string;
  node_label: string;
  logic: 'AND' | 'OR';
  conditions: Condition[];
}

interface GraphTriggerMappingPanelProps {
  graphName: string;
  nodeLabels: string[];
  mappings: GraphTriggerMapping[];
  onChange: (mappings: GraphTriggerMapping[]) => void;
}

// Convert flat GraphTriggerMapping[] to ConditionGroup[]
function mappingsToGroups(mappings: GraphTriggerMapping[], graphName: string): ConditionGroup[] {
  // Try to parse structured format from filter_expr
  const groups: ConditionGroup[] = [];
  const seen = new Set<string>();

  for (const m of mappings) {
    if (m.graph_name !== graphName) continue;
    const key = m.node_label;
    if (!seen.has(key)) {
      seen.add(key);
      let conds: Condition[] = [];
      try {
        const parsed = JSON.parse(m.filter_expr || '[]');
        if (Array.isArray(parsed)) conds = parsed;
      } catch {
        // Legacy single condition
        if (m.field) {
          conds = [{
            id: Math.random().toString(36).slice(2),
            attribute: m.field,
            operator: 'equals',
            values: m.filter_expr ? [m.filter_expr] : [],
          }];
        }
      }
      groups.push({
        id: Math.random().toString(36).slice(2),
        node_label: m.node_label,
        logic: 'AND',
        conditions: conds.length > 0 ? conds : [newCondition()],
      });
    }
  }
  return groups;
}

// Convert ConditionGroup[] back to flat GraphTriggerMapping[]
function groupsToMappings(groups: ConditionGroup[], graphName: string): GraphTriggerMapping[] {
  return groups.map(g => ({
    graph_name: graphName,
    node_label: g.node_label,
    field: g.conditions[0]?.attribute ?? '',
    dimension: g.node_label,
    filter_expr: JSON.stringify(g.conditions),
  }));
}

function newCondition(): Condition {
  return { id: Math.random().toString(36).slice(2), attribute: '', operator: 'equals', values: [] };
}

function newGroup(nodeLabel = ''): ConditionGroup {
  return {
    id: Math.random().toString(36).slice(2),
    node_label: nodeLabel,
    logic: 'AND',
    conditions: [newCondition()],
  };
}

export function GraphTriggerMappingPanel({
  graphName,
  nodeLabels,
  mappings,
  onChange,
}: GraphTriggerMappingPanelProps) {
  const [groups, setGroups] = useState<ConditionGroup[]>(() =>
    mappingsToGroups(mappings, graphName)
  );

  useEffect(() => {
    setGroups(mappingsToGroups(mappings, graphName));
  }, [mappings, graphName]);

  const push = useCallback((updated: ConditionGroup[]) => {
    setGroups(updated);
    onChange(groupsToMappings(updated, graphName));
  }, [graphName, onChange]);

  const addGroup = () => push([...groups, newGroup(nodeLabels[0] ?? '')]);
  const removeGroup = (gid: string) => push(groups.filter(g => g.id !== gid));
  const updateGroup = (gid: string, patch: Partial<ConditionGroup>) =>
    push(groups.map(g => g.id === gid ? { ...g, ...patch } : g));

  const addCondition = (gid: string) =>
    updateGroup(gid, { conditions: [...(groups.find(g => g.id === gid)?.conditions ?? []), newCondition()] });
  const removeCondition = (gid: string, cid: string) => {
    const g = groups.find(g => g.id === gid);
    if (!g) return;
    if (g.conditions.length <= 1) { removeGroup(gid); return; }
    updateGroup(gid, { conditions: g.conditions.filter(c => c.id !== cid) });
  };
  const updateCondition = (gid: string, cid: string, patch: Partial<Condition>) => {
    const g = groups.find(g => g.id === gid);
    if (!g) return;
    updateGroup(gid, { conditions: g.conditions.map(c => c.id === cid ? { ...c, ...patch } : c) });
  };

  // Value chip management
  const addValue = (gid: string, cid: string, val: string) => {
    if (!val.trim()) return;
    const g = groups.find(g => g.id === gid);
    const c = g?.conditions.find(c => c.id === cid);
    if (!c) return;
    if (!c.values.includes(val.trim())) {
      updateCondition(gid, cid, { values: [...c.values, val.trim()] });
    }
  };
  const removeValue = (gid: string, cid: string, val: string) => {
    const g = groups.find(g => g.id === gid);
    const c = g?.conditions.find(c => c.id === cid);
    if (!c) return;
    updateCondition(gid, cid, { values: c.values.filter(v => v !== val) });
  };

  return (
    <div className="mt-3 rounded-lg border border-purple-700/40 bg-purple-950/20 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h5 className="text-xs font-semibold text-purple-300 uppercase tracking-wide">
            Trigger Conditions
          </h5>
          <p className="text-[10px] text-gray-500 mt-0.5">
            Define when a node in this graph should trigger the rule. Multiple groups are joined with AND.
          </p>
        </div>
        <button
          onClick={addGroup}
          className="text-xs text-purple-400 hover:text-purple-200 border border-purple-700/50 rounded px-2 py-0.5"
        >
          + Add node group
        </button>
      </div>

      {groups.length === 0 && (
        <p className="text-[10px] text-gray-600 italic">
          No trigger conditions. Click "+ Add node group" to define when this graph should activate the rule.
        </p>
      )}

      {groups.map((group, gi) => (
        <div key={group.id} className="space-y-2">
          {gi > 0 && (
            <div className="flex items-center gap-2 my-1">
              <div className="flex-1 h-px bg-purple-800/30" />
              <span className="text-[10px] text-purple-500 font-semibold px-2">AND</span>
              <div className="flex-1 h-px bg-purple-800/30" />
            </div>
          )}

          <div className="rounded border border-purple-800/30 bg-black/10 p-3 space-y-3">
            {/* Node label + group logic header */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] text-gray-500 font-medium">Node:</span>
              {nodeLabels.length > 0 ? (
                <select
                  value={group.node_label}
                  onChange={e => updateGroup(group.id, { node_label: e.target.value })}
                  className="input-dark text-xs px-2 py-0.5 rounded"
                >
                  <option value="">Select node...</option>
                  {nodeLabels.map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              ) : (
                <input
                  value={group.node_label}
                  onChange={e => updateGroup(group.id, { node_label: e.target.value })}
                  placeholder="Node label (e.g. DataTransfer)"
                  className="input-dark text-xs px-2 py-1 rounded flex-1 min-w-[140px]"
                />
              )}
              <span className="text-[10px] text-gray-500 ml-auto">Conditions joined by:</span>
              <div className="flex rounded overflow-hidden border border-purple-700/40">
                {(['AND', 'OR'] as const).map(op => (
                  <button
                    key={op}
                    onClick={() => updateGroup(group.id, { logic: op })}
                    className={`px-2 py-0.5 text-[10px] font-bold ${group.logic === op ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-gray-200'}`}
                  >
                    {op}
                  </button>
                ))}
              </div>
              <button
                onClick={() => removeGroup(group.id)}
                className="text-red-400 hover:text-red-300 text-xs ml-1"
                title="Remove group"
              >✕</button>
            </div>

            {/* Conditions */}
            {group.conditions.map((cond, ci) => (
              <div key={cond.id} className="space-y-1.5">
                {ci > 0 && (
                  <div className="text-[10px] text-purple-400 font-semibold pl-1">{group.logic}</div>
                )}
                <ConditionRow
                  condition={cond}
                  onUpdate={(patch) => updateCondition(group.id, cond.id, patch)}
                  onRemove={() => removeCondition(group.id, cond.id)}
                  onAddValue={(val) => addValue(group.id, cond.id, val)}
                  onRemoveValue={(val) => removeValue(group.id, cond.id, val)}
                />
              </div>
            ))}

            <button
              onClick={() => addCondition(group.id)}
              className="text-[10px] text-purple-400 hover:text-purple-200 mt-1"
            >
              + Add condition
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── ConditionRow ─────────────────────────────────────────────────────────────

function ConditionRow({
  condition,
  onUpdate,
  onRemove,
  onAddValue,
  onRemoveValue,
}: {
  condition: Condition;
  onUpdate: (patch: Partial<Condition>) => void;
  onRemove: () => void;
  onAddValue: (val: string) => void;
  onRemoveValue: (val: string) => void;
}) {
  const [valueInput, setValueInput] = useState('');
  const multiValue = condition.operator === 'in' || condition.operator === 'not_in';

  const commitValue = () => {
    if (valueInput.trim()) {
      onAddValue(valueInput.trim());
      setValueInput('');
    }
  };

  return (
    <div className="flex flex-wrap items-start gap-2 bg-black/10 rounded p-2">
      {/* Attribute */}
      <input
        value={condition.attribute}
        onChange={e => onUpdate({ attribute: e.target.value })}
        placeholder="attribute"
        className="input-dark text-xs px-2 py-1 rounded w-28 font-mono"
      />

      {/* Operator */}
      <select
        value={condition.operator}
        onChange={e => onUpdate({ operator: e.target.value as Operator, values: [] })}
        className="input-dark text-xs px-2 py-1 rounded"
      >
        {OPERATORS.map(op => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>

      {/* Values */}
      <div className="flex flex-wrap items-center gap-1 flex-1 min-w-[120px]">
        {/* Existing value chips */}
        {condition.values.map(v => (
          <span
            key={v}
            className="flex items-center gap-0.5 bg-purple-600/30 border border-purple-700/40 text-purple-200 text-[10px] px-1.5 py-0.5 rounded"
          >
            {v}
            <button onClick={() => onRemoveValue(v)} className="text-purple-400 hover:text-red-400 ml-0.5">✕</button>
          </span>
        ))}

        {/* Value input */}
        {(multiValue || condition.values.length === 0) && (
          <input
            value={valueInput}
            onChange={e => setValueInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); commitValue(); }
            }}
            onBlur={commitValue}
            placeholder={multiValue ? 'value, Enter to add' : 'value'}
            className="input-dark text-xs px-2 py-0.5 rounded min-w-[100px] flex-1"
          />
        )}
      </div>

      <button onClick={onRemove} className="text-red-400 hover:text-red-300 text-xs">✕</button>
    </div>
  );
}
