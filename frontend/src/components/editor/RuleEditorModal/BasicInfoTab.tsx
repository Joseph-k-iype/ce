/**
 * BasicInfoTab Component
 *
 * Tab for editing basic rule information: name, description, outcome, priority, etc.
 */

import type { RuleFormData } from './types';

interface BasicInfoTabProps {
  formData: RuleFormData;
  onChange: (updates: Partial<RuleFormData>) => void;
  errors: Partial<Record<keyof RuleFormData, string>>;
}

export function BasicInfoTab({ formData, onChange, errors }: BasicInfoTabProps) {
  return (
    <div className="space-y-6 p-6">
      {/* Rule Name */}
      <div>
        <label htmlFor="rule-name" className="block text-sm font-medium text-gray-700 mb-2">
          Rule Name <span className="text-red-500">*</span>
        </label>
        <input
          id="rule-name"
          type="text"
          value={formData.name}
          onChange={e => onChange({ name: e.target.value })}
          placeholder="e.g., GDPR Health Data Transfer Rule"
          className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 ${
            errors.name
              ? 'border-red-300 focus:ring-red-500'
              : 'border-gray-300 focus:ring-purple-500'
          }`}
        />
        {errors.name && (
          <p className="mt-1 text-sm text-red-600">{errors.name}</p>
        )}
      </div>

      {/* Description */}
      <div>
        <label htmlFor="rule-description" className="block text-sm font-medium text-gray-700 mb-2">
          Description
        </label>
        <textarea
          id="rule-description"
          value={formData.description}
          onChange={e => onChange({ description: e.target.value })}
          placeholder="Detailed description of when this rule applies and what it requires..."
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>

      {/* Outcome & Priority */}
      <div className="grid grid-cols-2 gap-4">
        {/* Outcome */}
        <div>
          <label htmlFor="rule-outcome" className="block text-sm font-medium text-gray-700 mb-2">
            Outcome <span className="text-red-500">*</span>
          </label>
          <select
            id="rule-outcome"
            value={formData.outcome}
            onChange={e => onChange({ outcome: e.target.value as 'permission' | 'prohibition' })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="permission">Permission</option>
            <option value="prohibition">Prohibition</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            {formData.outcome === 'permission'
              ? 'Rule grants permission when conditions match'
              : 'Rule prohibits action when conditions match'}
          </p>
        </div>

        {/* Priority */}
        <div>
          <label htmlFor="rule-priority" className="block text-sm font-medium text-gray-700 mb-2">
            Priority <span className="text-red-500">*</span>
          </label>
          <select
            id="rule-priority"
            value={formData.priority}
            onChange={e => onChange({ priority: e.target.value as 'high' | 'medium' | 'low' })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            Higher priority rules override lower priority rules
          </p>
        </div>
      </div>

      {/* Toggles */}
      <div className="space-y-4">
        {/* Enabled */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.enabled}
            onChange={e => onChange({ enabled: e.target.checked })}
            className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
          />
          <div className="flex-1">
            <span className="text-sm font-medium text-gray-700">Enabled</span>
            <p className="text-xs text-gray-500">Rule will be evaluated during compliance checks</p>
          </div>
        </label>

        {/* Requires PII */}
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.requires_pii}
            onChange={e => onChange({ requires_pii: e.target.checked })}
            className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
          />
          <div className="flex-1">
            <span className="text-sm font-medium text-gray-700">Requires PII Handling</span>
            <p className="text-xs text-gray-500">This rule involves personally identifiable information</p>
          </div>
        </label>
      </div>

      {/* Valid Until */}
      <div>
        <label htmlFor="rule-valid-until" className="block text-sm font-medium text-gray-700 mb-2">
          Valid Until (Optional)
        </label>
        <input
          id="rule-valid-until"
          type="date"
          value={formData.valid_until || ''}
          onChange={e => onChange({ valid_until: e.target.value || null })}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Rule will expire on this date and no longer be evaluated
        </p>
      </div>

      {/* Info Box */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm text-blue-800">
              After setting basic information, configure the trigger logic in the next tab to define when this rule applies.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
