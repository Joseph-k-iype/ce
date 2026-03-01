/**
 * DutiesTab Component
 *
 * Tab for defining required assessments (PIA/TIA/HRPR) and required actions
 */

import { useState } from 'react';
import type { RuleFormData } from './types';

interface DutiesTabProps {
  formData: RuleFormData;
  onChange: (updates: Partial<RuleFormData>) => void;
}

export function DutiesTab({ formData, onChange }: DutiesTabProps) {
  const [newAction, setNewAction] = useState('');

  const handleAddAction = () => {
    if (!newAction.trim()) return;
    onChange({ required_actions: [...formData.required_actions, newAction.trim()] });
    setNewAction('');
  };

  const handleRemoveAction = (index: number) => {
    const updated = [...formData.required_actions];
    updated.splice(index, 1);
    onChange({ required_actions: updated });
  };

  const handleToggleAssessment = (assessment: string) => {
    const updated = formData.required_assessments.includes(assessment)
      ? formData.required_assessments.filter(a => a !== assessment)
      : [...formData.required_assessments, assessment];
    onChange({ required_assessments: updated });
  };

  return (
    <div className="space-y-8 p-6">
      {/* Header */}
      <div>
        <h3 className="text-base font-semibold text-gray-900">Define Required Duties</h3>
        <p className="text-sm text-gray-600 mt-1">
          Specify compliance assessments and actions required when this rule is triggered.
        </p>
      </div>

      {/* Required Assessments */}
      <div>
        <h4 className="text-sm font-medium text-gray-900 mb-3">Required Assessments</h4>
        <p className="text-xs text-gray-600 mb-4">
          Select which impact assessments must be completed when this rule applies.
        </p>

        <div className="space-y-3">
          {/* PIA */}
          <label className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="checkbox"
              checked={formData.required_assessments.includes('PIA')}
              onChange={() => handleToggleAssessment('PIA')}
              className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mt-0.5"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">Privacy Impact Assessment (PIA)</span>
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">Assessment</span>
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Systematic evaluation of privacy risks and impact on data subjects
              </p>
            </div>
          </label>

          {/* TIA */}
          <label className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="checkbox"
              checked={formData.required_assessments.includes('TIA')}
              onChange={() => handleToggleAssessment('TIA')}
              className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mt-0.5"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">Transfer Impact Assessment (TIA)</span>
                <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded">Assessment</span>
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Assessment of risks associated with cross-border data transfers
              </p>
            </div>
          </label>

          {/* HRPR */}
          <label className="flex items-start gap-3 p-4 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="checkbox"
              checked={formData.required_assessments.includes('HRPR')}
              onChange={() => handleToggleAssessment('HRPR')}
              className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mt-0.5"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">High-Risk Processing Review (HRPR)</span>
                <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded">Assessment</span>
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Review required for processing activities involving high risks to individuals
              </p>
            </div>
          </label>
        </div>
      </div>

      {/* Required Actions */}
      <div>
        <h4 className="text-sm font-medium text-gray-900 mb-3">Required Actions</h4>
        <p className="text-xs text-gray-600 mb-4">
          Define specific actions that must be taken when this rule is triggered.
        </p>

        {/* Add Action Input */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newAction}
            onChange={e => setNewAction(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleAddAction();
              }
            }}
            placeholder="e.g., Obtain explicit consent, Implement encryption, Notify DPO..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          />
          <button
            type="button"
            onClick={handleAddAction}
            className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
          >
            Add
          </button>
        </div>

        {/* Actions List */}
        {formData.required_actions.length > 0 ? (
          <ul className="space-y-2">
            {formData.required_actions.map((action, index) => (
              <li
                key={index}
                className="flex items-start gap-3 p-3 bg-gray-50 border border-gray-200 rounded-lg"
              >
                <svg className="w-5 h-5 text-purple-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="flex-1 text-sm text-gray-900">{action}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveAction(index)}
                  className="text-gray-400 hover:text-red-600 transition-colors"
                  title="Remove action"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-8 text-center border-2 border-dashed border-gray-200 rounded-lg">
            <svg className="w-8 h-8 text-gray-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            <p className="text-sm text-gray-500">No required actions defined</p>
            <p className="text-xs text-gray-400 mt-1">Add actions using the input above</p>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
        <div className="flex items-start gap-2">
          <svg className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm text-amber-800">
              Duties are stored as graph nodes linked to this rule. When the rule matches, these duties will appear in the compliance report
              and must be completed before data processing can proceed.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
