/**
 * ConditionEditor Component
 *
 * Editor for CONDITION nodes with dimension selector and multi-select value picker.
 */

import React, { useMemo } from 'react';
import CreatableSelect from 'react-select/creatable';
import type { LogicNode, DimensionConfig, DropdownDataResponse, SelectOption } from './types';
import { getDimensionOptions, getDimensionConfig } from '../../../services/dimensionConfig';

interface ConditionEditorProps {
  node: LogicNode;
  dimensionConfigs: DimensionConfig[];
  dropdownData: DropdownDataResponse | null;
  onChange: (node: LogicNode) => void;
  onRemove: () => void;
  readOnly?: boolean;
  path: number[];
  hasErrors?: boolean;
}

export function ConditionEditor({
  node,
  dimensionConfigs,
  dropdownData,
  onChange,
  onRemove,
  readOnly,
  path,
  hasErrors
}: ConditionEditorProps) {
  const dimensionConfig = node.dimension ? getDimensionConfig(node.dimension) : undefined;

  // Get available options for selected dimension
  const valueOptions = useMemo(() => {
    if (!node.dimension) {
      return [];
    }
    return getDimensionOptions(node.dimension, dropdownData);
  }, [node.dimension, dropdownData]);

  // Convert comma-separated values to select options
  const selectedValues = useMemo(() => {
    if (!node.value) {
      return [];
    }
    return node.value.split(',').map(v => v.trim()).filter(v => v !== '').map(v => ({
      value: v,
      label: v
    }));
  }, [node.value]);

  const handleDimensionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange({
      ...node,
      dimension: e.target.value,
      value: ''  // Clear value when dimension changes
    });
  };

  const handleValueChange = (newValues: readonly SelectOption[] | null) => {
    const value = newValues ? newValues.map(v => v.value).join(', ') : '';
    onChange({
      ...node,
      value
    });
  };

  return (
    <div className={`flex items-start gap-3 p-4 rounded-lg border-2 ${hasErrors ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'}`}>
      {/* Path indicator */}
      <div className="flex-shrink-0 text-xs text-gray-400 font-mono mt-2">
        {path.join('.')}
      </div>

      {/* Dimension selector */}
      <div className="flex-1 min-w-0">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Dimension
        </label>
        <select
          value={node.dimension || ''}
          onChange={handleDimensionChange}
          disabled={readOnly}
          className="block w-full px-3 py-2 text-sm border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          <option value="">Select dimension...</option>

          <optgroup label="Geography">
            {dimensionConfigs
              .filter(d => d.category === 'geography')
              .map(d => (
                <option key={d.name} value={d.name}>
                  {d.label}
                </option>
              ))}
          </optgroup>

          <optgroup label="Data">
            {dimensionConfigs
              .filter(d => d.category === 'data')
              .map(d => (
                <option key={d.name} value={d.name}>
                  {d.label}
                </option>
              ))}
          </optgroup>

          <optgroup label="Regulatory">
            {dimensionConfigs
              .filter(d => d.category === 'regulatory')
              .map(d => (
                <option key={d.name} value={d.name}>
                  {d.label}
                </option>
              ))}
          </optgroup>
        </select>
      </div>

      {/* Value selector */}
      <div className="flex-1 min-w-0">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Value(s)
        </label>
        <CreatableSelect
          isMulti
          value={selectedValues}
          options={valueOptions}
          onChange={handleValueChange}
          isDisabled={readOnly || !node.dimension}
          placeholder={node.dimension ? "Select or type values..." : "Select dimension first..."}
          className="text-sm"
          classNamePrefix="react-select"
          styles={{
            control: (base, state) => ({
              ...base,
              minHeight: '38px',
              borderColor: state.isFocused ? '#3b82f6' : '#d1d5db',
              '&:hover': {
                borderColor: state.isFocused ? '#3b82f6' : '#9ca3af'
              }
            }),
            multiValue: (base) => ({
              ...base,
              backgroundColor: '#e0e7ff'
            }),
            multiValueLabel: (base) => ({
              ...base,
              color: '#3730a3',
              fontSize: '0.875rem'
            }),
            multiValueRemove: (base) => ({
              ...base,
              color: '#3730a3',
              ':hover': {
                backgroundColor: '#c7d2fe',
                color: '#1e1b4b'
              }
            })
          }}
          formatCreateLabel={(inputValue) => `Create "${inputValue}"`}
          noOptionsMessage={() => "Type to create new value"}
        />
        {dimensionConfig?.allowCreate && (
          <p className="mt-1 text-xs text-gray-500">
            Type to create new values
          </p>
        )}
      </div>

      {/* Remove button */}
      {!readOnly && (
        <button
          type="button"
          onClick={onRemove}
          className="flex-shrink-0 p-2 mt-6 text-gray-400 hover:text-red-600 rounded-md hover:bg-red-50"
          title="Remove condition"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      )}
    </div>
  );
}
