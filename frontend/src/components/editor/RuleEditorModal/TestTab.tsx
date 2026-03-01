/**
 * TestTab Component
 *
 * Tab for testing rule against sample scenarios before saving
 */

import { useState } from 'react';
import Select from 'react-select';
import api from '../../../services/api';
import type { RuleFormData, TestScenario, TestResult } from './types';
import type { DropdownDataResponse } from '../../shared/LogicTreeBuilder/types';

interface TestTabProps {
  formData: RuleFormData;
  dropdownData: DropdownDataResponse | null;
}

export function TestTab({ formData, dropdownData }: TestTabProps) {
  const [scenario, setScenario] = useState<TestScenario>({});
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const countryOptions = (dropdownData?.countries || []).map(c => ({ value: c, label: c }));

  const dataCategoryOptions = (dropdownData?.data_categories || []).map(dc => ({
    value: typeof dc === 'string' ? dc : dc.name,
    label: typeof dc === 'string' ? dc : dc.name,
  }));

  const purposeOptions = (dropdownData?.purposes || []).map(p => ({ value: p, label: p }));

  const handleRunTest = async () => {
    setTesting(true);
    setError(null);
    setResult(null);

    try {
      // Build rule definition from current form data
      const ruleDef = {
        name: formData.name,
        description: formData.description,
        outcome: formData.outcome,
        priority: formData.priority,
        logic_tree: formData.logic_tree,
        enabled: formData.enabled,
        requires_pii: formData.requires_pii,
        valid_until: formData.valid_until,
        data_categories: formData.data_categories,
        purposes: formData.purposes,
        processes: formData.processes,
        regulators: formData.regulators,
        authorities: formData.authorities,
        data_subjects: formData.data_subjects,
        gdc: formData.gdc,
        sensitive_data_categories: formData.sensitive_data_categories,
        required_assessments: formData.required_assessments,
        required_actions: formData.required_actions,
      };

      // Call test endpoint
      const response = await api.post<TestResult>('/admin/rules/test', {
        rule_def: ruleDef,
        test_scenario: scenario,
      });

      setResult(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test failed');
    } finally {
      setTesting(false);
    }
  };

  const selectStyles = {
    control: (base: any, state: any) => ({
      ...base,
      minHeight: '38px',
      borderColor: state.isFocused ? '#9333ea' : '#d1d5db',
      '&:hover': { borderColor: '#9333ea' },
      boxShadow: state.isFocused ? '0 0 0 1px #9333ea' : 'none',
    }),
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h3 className="text-base font-semibold text-gray-900">Test Rule</h3>
        <p className="text-sm text-gray-600 mt-1">
          Test your rule against a sample scenario before saving. This creates a temporary sandbox graph to safely evaluate the rule.
        </p>
      </div>

      {/* Test Scenario Form */}
      <div className="p-5 border border-gray-200 rounded-lg bg-gray-50">
        <h4 className="text-sm font-medium text-gray-900 mb-4">Define Test Scenario</h4>

        <div className="space-y-4">
          {/* Origin Country */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Origin Country</label>
            <Select
              options={countryOptions}
              value={scenario.origin_country ? { value: scenario.origin_country, label: scenario.origin_country } : null}
              onChange={selected => setScenario({ ...scenario, origin_country: selected?.value })}
              placeholder="Select origin country..."
              isClearable
              styles={selectStyles}
            />
          </div>

          {/* Receiving Country */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Receiving Country</label>
            <Select
              options={countryOptions}
              value={scenario.receiving_country ? { value: scenario.receiving_country, label: scenario.receiving_country } : null}
              onChange={selected => setScenario({ ...scenario, receiving_country: selected?.value })}
              placeholder="Select receiving country..."
              isClearable
              styles={selectStyles}
            />
          </div>

          {/* Data Categories */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data Categories</label>
            <Select
              isMulti
              options={dataCategoryOptions}
              value={(scenario.data_categories || []).map(dc => ({ value: dc, label: dc }))}
              onChange={selected => setScenario({ ...scenario, data_categories: (selected || []).map(s => s.value) })}
              placeholder="Select data categories..."
              styles={selectStyles}
            />
          </div>

          {/* Purposes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Purposes</label>
            <Select
              isMulti
              options={purposeOptions}
              value={(scenario.purposes || []).map(p => ({ value: p, label: p }))}
              onChange={selected => setScenario({ ...scenario, purposes: (selected || []).map(s => s.value) })}
              placeholder="Select purposes..."
              styles={selectStyles}
            />
          </div>

          {/* Run Test Button */}
          <button
            type="button"
            onClick={handleRunTest}
            disabled={testing}
            className="w-full px-4 py-3 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {testing ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Run Test
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-800 mb-1">Test Failed</h4>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Test Results */}
      {result && (
        <div className={`p-5 border-2 rounded-lg ${result.matched ? 'border-green-300 bg-green-50' : 'border-gray-300 bg-gray-50'}`}>
          <div className="flex items-center gap-3 mb-4">
            {result.matched ? (
              <>
                <div className="flex-shrink-0 w-10 h-10 bg-green-500 text-white rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-base font-semibold text-green-900">Rule Matched!</h4>
                  <p className="text-sm text-green-700">The rule successfully matched the test scenario</p>
                </div>
              </>
            ) : (
              <>
                <div className="flex-shrink-0 w-10 h-10 bg-gray-400 text-white rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-base font-semibold text-gray-900">No Match</h4>
                  <p className="text-sm text-gray-700">The rule did not match the test scenario</p>
                </div>
              </>
            )}
          </div>

          {/* Evaluation Details */}
          <div className="mt-4 pt-4 border-t border-green-200 space-y-3">
            <div>
              <span className="text-xs font-medium text-gray-600">Outcome:</span>
              <span className={`ml-2 text-sm font-medium ${result.evaluation_result.allowed ? 'text-green-700' : 'text-red-700'}`}>
                {result.evaluation_result.allowed ? 'Allowed' : 'Prohibited'}
              </span>
            </div>

            <div>
              <span className="text-xs font-medium text-gray-600">Reason:</span>
              <p className="text-sm text-gray-900 mt-1">{result.evaluation_result.reason}</p>
            </div>

            {result.evaluation_result.matched_rules.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-600">Matched Rules:</span>
                <ul className="mt-2 space-y-1">
                  {result.evaluation_result.matched_rules.map((ruleId, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-center gap-2">
                      <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {ruleId}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.evaluation_result.required_duties.length > 0 && (
              <div>
                <span className="text-xs font-medium text-gray-600">Required Duties:</span>
                <ul className="mt-2 space-y-1">
                  {result.evaluation_result.required_duties.map((duty, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-center gap-2">
                      <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      {duty}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-2">
          <svg className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm text-blue-800">
              Testing creates a temporary sandbox graph that is automatically cleaned up after evaluation.
              No changes are made to the production graph until you click "Save Rule".
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
