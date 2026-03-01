/**
 * RuleEditorModal Component
 *
 * Comprehensive modal for creating and editing rules with 5 tabs:
 * 1. Basic Info - Name, description, outcome, priority
 * 2. Trigger Logic - Visual logic tree builder
 * 3. Entity Mapping - Link to graph entities
 * 4. Duties - Required assessments and actions
 * 5. Test - Sandbox testing before save
 */

import { useState, useEffect, useCallback, type ReactNode } from 'react';
import api from '../../../services/api';
import { BasicInfoTab } from './BasicInfoTab';
import { TriggerLogicTab } from './TriggerLogicTab';
import { EntityMappingTab } from './EntityMappingTab';
import { DutiesTab } from './DutiesTab';
import { TestTab } from './TestTab';
import type { RuleEditorModalProps, RuleFormData } from './types';
import type { DropdownDataResponse } from '../../shared/LogicTreeBuilder/types';

type TabId = 'basic' | 'logic' | 'entities' | 'duties' | 'test';

const TABS: Array<{ id: TabId; label: string; icon: ReactNode }> = [
  {
    id: 'basic',
    label: 'Basic Info',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    id: 'logic',
    label: 'Trigger Logic',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    id: 'entities',
    label: 'Entity Mapping',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
      </svg>
    ),
  },
  {
    id: 'duties',
    label: 'Duties',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    id: 'test',
    label: 'Test',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

const DEFAULT_FORM_DATA: RuleFormData = {
  name: '',
  description: '',
  outcome: 'permission',
  priority: 'medium',
  enabled: true,
  valid_until: null,
  requires_pii: false,
  logic_tree: { type: 'AND', children: [] },
  data_categories: [],
  purposes: [],
  processes: [],
  regulators: [],
  authorities: [],
  data_subjects: [],
  gdc: [],
  sensitive_data_categories: [],
  required_assessments: [],
  required_actions: [],
};

export function RuleEditorModal({ isOpen, onClose, ruleId, onSave }: RuleEditorModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>('basic');
  const [formData, setFormData] = useState<RuleFormData>(DEFAULT_FORM_DATA);
  const [dropdownData, setDropdownData] = useState<DropdownDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errors, setErrors] = useState<Partial<Record<keyof RuleFormData, string>>>({});

  const isEditMode = Boolean(ruleId);

  // Load dropdown data on mount
  useEffect(() => {
    if (!isOpen) return;

    api.get<DropdownDataResponse>('/graph-data/dropdowns')
      .then(res => setDropdownData(res.data))
      .catch(err => console.error('Failed to load dropdown data:', err));
  }, [isOpen]);

  // Load existing rule in edit mode
  useEffect(() => {
    if (!isOpen || !ruleId) return;

    setLoading(true);
    api.get(`/admin/rules/${ruleId}`)
      .then(res => {
        const rule = res.data;
        setFormData({
          name: rule.name || '',
          description: rule.description || '',
          outcome: rule.outcome || 'permission',
          priority: rule.priority || 'medium',
          enabled: rule.enabled !== false,
          valid_until: rule.valid_until || null,
          requires_pii: rule.requires_pii || false,
          logic_tree: rule.logic_tree || { type: 'AND', children: [] },
          data_categories: rule.data_categories || [],
          purposes: rule.purposes || [],
          processes: rule.processes || [],
          regulators: rule.regulators || [],
          authorities: rule.authorities || [],
          data_subjects: rule.data_subjects || [],
          gdc: rule.gdc || [],
          sensitive_data_categories: rule.sensitive_data_categories || [],
          required_assessments: rule.required_assessments || [],
          required_actions: rule.required_actions || [],
        });
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [isOpen, ruleId]);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setFormData(DEFAULT_FORM_DATA);
      setActiveTab('basic');
      setError(null);
      setErrors({});
    }
  }, [isOpen]);

  const handleFormChange = useCallback((updates: Partial<RuleFormData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
    // Clear errors for updated fields
    setErrors(prev => {
      const newErrors = { ...prev };
      Object.keys(updates).forEach(key => {
        delete newErrors[key as keyof RuleFormData];
      });
      return newErrors;
    });
  }, []);

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof RuleFormData, string>> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Rule name is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      setActiveTab('basic');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (isEditMode) {
        // Update existing rule
        await api.put(`/admin/rules/${ruleId}/full`, formData);
      } else {
        // Create new rule
        const response = await api.post('/admin/rules/create-full', formData);
        if (onSave && response.data.rule_id) {
          onSave(response.data.rule_id);
        }
      }

      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rule');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />

      {/* Modal */}
      <div className="absolute inset-0 flex items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-2xl max-w-5xl w-full max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {isEditMode ? 'Edit Rule' : 'Create New Rule'}
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {isEditMode ? `Editing: ${formData.name || ruleId}` : 'Define a new compliance rule'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200 px-6 bg-gray-50">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-purple-600 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="w-8 h-8 border-4 border-gray-300 border-t-purple-600 rounded-full animate-spin" />
              </div>
            ) : (
              <>
                {activeTab === 'basic' && (
                  <BasicInfoTab formData={formData} onChange={handleFormChange} errors={errors} />
                )}
                {activeTab === 'logic' && (
                  <TriggerLogicTab formData={formData} onChange={handleFormChange} dropdownData={dropdownData} />
                )}
                {activeTab === 'entities' && (
                  <EntityMappingTab formData={formData} onChange={handleFormChange} dropdownData={dropdownData} />
                )}
                {activeTab === 'duties' && <DutiesTab formData={formData} onChange={handleFormChange} />}
                {activeTab === 'test' && <TestTab formData={formData} dropdownData={dropdownData} />}
              </>
            )}
          </div>

          {/* Error Display */}
          {error && (
            <div className="mx-6 mb-4 p-4 bg-red-50 border-l-4 border-red-500 rounded-r-lg">
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Use tabs to configure all aspects of the rule</span>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    {isEditMode ? 'Update Rule' : 'Create Rule'}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
