/**
 * TriggerLogicTab Component
 *
 * Tab for visual logic tree editing using the standardized LogicTreeBuilder
 */

import { LogicTreeBuilder } from '../../shared/LogicTreeBuilder';
import { DIMENSION_CONFIGS } from '../../../services/dimensionConfig';
import type { LogicNode, DropdownDataResponse } from '../../shared/LogicTreeBuilder/types';
import type { RuleFormData } from './types';

interface TriggerLogicTabProps {
  formData: RuleFormData;
  onChange: (updates: Partial<RuleFormData>) => void;
  dropdownData: DropdownDataResponse | null;
}

export function TriggerLogicTab({ formData, onChange, dropdownData }: TriggerLogicTabProps) {
  const handleLogicTreeChange = (tree: LogicNode) => {
    onChange({ logic_tree: tree });
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h3 className="text-base font-semibold text-gray-900">Define Trigger Logic</h3>
        <p className="text-sm text-gray-600 mt-1">
          Build the conditions that determine when this rule applies. Combine multiple conditions using AND/OR logic groups.
        </p>
      </div>

      {/* Info Box */}
      <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-lg">
        <div className="flex items-start gap-2">
          <svg className="w-5 h-5 text-purple-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm text-purple-800 font-medium mb-1">Logic Tree Tips:</p>
            <ul className="text-sm text-purple-700 space-y-1 list-disc list-inside">
              <li><strong>AND groups</strong> (green) require all conditions to match</li>
              <li><strong>OR groups</strong> (purple) require at least one condition to match</li>
              <li>Nest groups to create complex logic (e.g., "Data is Financial OR Health" AND "Country is EU")</li>
              <li>Use Ctrl+Z / Ctrl+Shift+Z for undo/redo</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Logic Tree Builder */}
      <div className="border border-gray-200 rounded-lg bg-gray-50 p-4">
        <LogicTreeBuilder
          initialTree={formData.logic_tree}
          dimensionConfigs={DIMENSION_CONFIGS}
          dropdownData={dropdownData}
          onChange={handleLogicTreeChange}
          mode="full"
        />
      </div>

      {/* Examples */}
      <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <p className="text-sm font-medium text-gray-700 mb-2">Example Logic Patterns:</p>
        <div className="space-y-2 text-sm text-gray-600">
          <div>
            <strong>Simple:</strong> DataCategory = "Health Data"
          </div>
          <div>
            <strong>AND logic:</strong> DataCategory = "Financial" AND OriginCountry = "United Kingdom"
          </div>
          <div>
            <strong>OR logic:</strong> (Regulator = "ICO" OR Regulator = "CNIL")
          </div>
          <div>
            <strong>Complex nested:</strong> (DataCategory = "Health" OR DataCategory = "Financial") AND (OriginCountry = "EU Countries")
          </div>
        </div>
      </div>
    </div>
  );
}
