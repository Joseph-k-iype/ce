/**
 * GraphTriggerMappingPanel
 * ========================
 * Shown below a selected graph card. Lets the user map graph node fields
 * to trigger dimensions (DataCategory, Purpose, etc.) and set filter expressions.
 */

import { useState, useEffect, useCallback } from 'react';
import type { GraphTriggerMapping } from '../../services/wizardApi';

const TRIGGER_DIMENSIONS = [
  'DataCategory',
  'Purpose',
  'Process',
  'Regulator',
  'Authority',
  'DataSubject',
  'SensitiveDataCategory',
  'GDC',
  'OriginCountry',
  'ReceivingCountry',
];

interface GraphTriggerMappingPanelProps {
  graphName: string;
  /** Node labels detected from the graph preview */
  nodeLabels: string[];
  mappings: GraphTriggerMapping[];
  onChange: (mappings: GraphTriggerMapping[]) => void;
}

function emptyMapping(graphName: string): GraphTriggerMapping {
  return { graph_name: graphName, node_label: '', field: '', dimension: 'DataCategory', filter_expr: '' };
}

export function GraphTriggerMappingPanel({
  graphName,
  nodeLabels,
  mappings,
  onChange,
}: GraphTriggerMappingPanelProps) {
  const [localMappings, setLocalMappings] = useState<GraphTriggerMapping[]>(mappings);

  useEffect(() => {
    setLocalMappings(mappings);
  }, [mappings]);

  const push = useCallback((updated: GraphTriggerMapping[]) => {
    setLocalMappings(updated);
    onChange(updated);
  }, [onChange]);

  const addRow = () => {
    push([...localMappings, emptyMapping(graphName)]);
  };

  const updateRow = (idx: number, patch: Partial<GraphTriggerMapping>) => {
    const updated = localMappings.map((m, i) => i === idx ? { ...m, ...patch } : m);
    push(updated);
  };

  const removeRow = (idx: number) => {
    push(localMappings.filter((_, i) => i !== idx));
  };

  return (
    <div className="mt-3 rounded-lg border border-purple-700/40 bg-purple-950/20 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h5 className="text-xs font-semibold text-purple-300 uppercase tracking-wide">
          Graph Trigger Mapping
        </h5>
        <button
          onClick={addRow}
          className="text-xs text-purple-400 hover:text-purple-200 border border-purple-700/50 rounded px-2 py-0.5"
        >
          + Add mapping
        </button>
      </div>
      <p className="text-[10px] text-gray-500">
        Map fields from this graph's nodes to trigger dimensions. These mappings define how
        data in the graph links to rule conditions.
      </p>

      {localMappings.length === 0 && (
        <p className="text-[10px] text-gray-600 italic">No mappings yet. Click "+ Add mapping" to define one.</p>
      )}

      <div className="space-y-2">
        {localMappings.map((mapping, idx) => (
          <div key={idx} className="grid grid-cols-[1fr_1fr_1fr_1fr_auto] gap-2 items-center">
            {/* Node Label */}
            {nodeLabels.length > 0 ? (
              <select
                value={mapping.node_label}
                onChange={e => updateRow(idx, { node_label: e.target.value })}
                className="input-dark text-xs"
              >
                <option value="">Node label</option>
                {nodeLabels.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            ) : (
              <input
                value={mapping.node_label}
                onChange={e => updateRow(idx, { node_label: e.target.value })}
                placeholder="Node label"
                className="input-dark text-xs"
              />
            )}

            {/* Field */}
            <input
              value={mapping.field}
              onChange={e => updateRow(idx, { field: e.target.value })}
              placeholder="Field name"
              className="input-dark text-xs"
            />

            {/* Dimension */}
            <select
              value={mapping.dimension}
              onChange={e => updateRow(idx, { dimension: e.target.value })}
              className="input-dark text-xs"
            >
              {TRIGGER_DIMENSIONS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>

            {/* Filter expression */}
            <input
              value={mapping.filter_expr}
              onChange={e => updateRow(idx, { filter_expr: e.target.value })}
              placeholder="Filter (e.g. status='active')"
              className="input-dark text-xs"
            />

            <button
              onClick={() => removeRow(idx)}
              className="text-red-400 hover:text-red-300 text-xs px-1"
              title="Remove row"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {localMappings.length > 0 && (
        <p className="text-[10px] text-gray-600">
          Mappings are saved automatically when you save the session.
        </p>
      )}
    </div>
  );
}
