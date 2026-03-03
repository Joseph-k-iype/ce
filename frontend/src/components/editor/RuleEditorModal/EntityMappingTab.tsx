/**
 * EntityMappingTab Component
 *
 * Tab for mapping rule to graph entities via multi-select dropdowns
 */

import { useMemo } from 'react';
import Select from 'react-select';
import type { RuleFormData } from './types';
import type { DropdownDataResponse } from '../../shared/LogicTreeBuilder/types';
import { reactSelectStyles, reactSelectTheme } from '../../../styles/reactSelectTheme';

interface EntityMappingTabProps {
  formData: RuleFormData;
  onChange: (updates: Partial<RuleFormData>) => void;
  dropdownData: DropdownDataResponse | null;
}

export function EntityMappingTab({ formData, onChange, dropdownData }: EntityMappingTabProps) {
  // Convert dropdown data to react-select options
  const dataCategoryOptions = useMemo(
    () =>
      (dropdownData?.data_categories || []).map(dc => ({
        value: typeof dc === 'string' ? dc : dc.name,
        label: typeof dc === 'string' ? dc : dc.name,
      })),
    [dropdownData]
  );

  const purposeOptions = useMemo(
    () => (dropdownData?.purposes || []).map(p => ({ value: p, label: p })),
    [dropdownData]
  );

  const processOptions = useMemo(() => {
    const allProcesses = [
      ...(dropdownData?.processes?.l1 || []),
      ...(dropdownData?.processes?.l2 || []),
      ...(dropdownData?.processes?.l3 || []),
    ];
    return allProcesses.map(p => ({ value: p, label: p }));
  }, [dropdownData]);

  const regulatorOptions = useMemo(
    () => (dropdownData?.regulators || []).map(r => ({ value: r.name, label: r.name })),
    [dropdownData]
  );

  const authorityOptions = useMemo(
    () => (dropdownData?.authorities || []).map(a => ({ value: a.name, label: a.name })),
    [dropdownData]
  );

  const dataSubjectOptions = useMemo(
    () => (dropdownData?.data_subjects || []).map(ds => ({ value: ds.name, label: ds.name })),
    [dropdownData]
  );

  const gdcOptions = useMemo(
    () => (dropdownData?.gdc || []).map(g => ({ value: g.name, label: g.name })),
    [dropdownData]
  );

  const sensitiveDataOptions = useMemo(
    () => (dropdownData?.sensitive_data_categories || []).map(sdc => ({ value: sdc.name, label: sdc.name })),
    [dropdownData]
  );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h3 className="text-base font-semibold text-gray-900">Map Rule to Entities</h3>
        <p className="text-sm text-gray-600 mt-1">
          Select the graph entities this rule should be linked to. These mappings enable graph-driven querying and precedent search.
        </p>
      </div>

      {/* Data Categories */}
      <div>
        <label htmlFor="entity-data-categories" className="block text-sm font-medium text-gray-700 mb-2">
          Data Categories
        </label>
        <Select
          isMulti
          inputId="entity-data-categories"
          options={dataCategoryOptions}
          value={formData.data_categories.map(dc => ({ value: dc, label: dc }))}
          onChange={selected => onChange({ data_categories: (selected || []).map((s: any) => s.value) })}
          placeholder="Select data categories..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Data categories"
          aria-describedby="data-categories-help"
        />
        <p id="data-categories-help" className="mt-1 text-xs text-gray-500">
          Link to data category nodes (e.g., Health Data, Financial Data)
        </p>
      </div>

      {/* Purposes */}
      <div>
        <label htmlFor="entity-purposes" className="block text-sm font-medium text-gray-700 mb-2">
          Purposes
        </label>
        <Select
          isMulti
          inputId="entity-purposes"
          options={purposeOptions}
          value={formData.purposes.map(p => ({ value: p, label: p }))}
          onChange={selected => onChange({ purposes: (selected || []).map((s: any) => s.value) })}
          placeholder="Select purposes..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Purposes"
          aria-describedby="purposes-help"
        />
        <p id="purposes-help" className="mt-1 text-xs text-gray-500">
          Link to purpose nodes (e.g., Marketing, Analytics)
        </p>
      </div>

      {/* Processes */}
      <div>
        <label htmlFor="entity-processes" className="block text-sm font-medium text-gray-700 mb-2">
          Processes
        </label>
        <Select
          isMulti
          inputId="entity-processes"
          options={processOptions}
          value={formData.processes.map(p => ({ value: p, label: p }))}
          onChange={selected => onChange({ processes: (selected || []).map((s: any) => s.value) })}
          placeholder="Select processes..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Processes"
          aria-describedby="processes-help"
        />
        <p id="processes-help" className="mt-1 text-xs text-gray-500">
          Link to process nodes (L1, L2, L3)
        </p>
      </div>

      {/* Regulators */}
      <div>
        <label htmlFor="entity-regulators" className="block text-sm font-medium text-gray-700 mb-2">
          Regulators
        </label>
        <Select
          isMulti
          inputId="entity-regulators"
          options={regulatorOptions}
          value={formData.regulators.map(r => ({ value: r, label: r }))}
          onChange={selected => onChange({ regulators: (selected || []).map((s: any) => s.value) })}
          placeholder="Select regulators..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Regulators"
          aria-describedby="regulators-help"
        />
        <p id="regulators-help" className="mt-1 text-xs text-gray-500">
          Link to regulator nodes (e.g., ICO, CNIL)
        </p>
      </div>

      {/* Authorities */}
      <div>
        <label htmlFor="entity-authorities" className="block text-sm font-medium text-gray-700 mb-2">
          Authorities
        </label>
        <Select
          isMulti
          inputId="entity-authorities"
          options={authorityOptions}
          value={formData.authorities.map(a => ({ value: a, label: a }))}
          onChange={selected => onChange({ authorities: (selected || []).map((s: any) => s.value) })}
          placeholder="Select authorities..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Authorities"
          aria-describedby="authorities-help"
        />
        <p id="authorities-help" className="mt-1 text-xs text-gray-500">
          Link to authority nodes
        </p>
      </div>

      {/* Data Subjects */}
      <div>
        <label htmlFor="entity-data-subjects" className="block text-sm font-medium text-gray-700 mb-2">
          Data Subjects
        </label>
        <Select
          isMulti
          inputId="entity-data-subjects"
          options={dataSubjectOptions}
          value={formData.data_subjects.map(ds => ({ value: ds, label: ds }))}
          onChange={selected => onChange({ data_subjects: (selected || []).map((s: any) => s.value) })}
          placeholder="Select data subjects..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Data subjects"
          aria-describedby="data-subjects-help"
        />
        <p id="data-subjects-help" className="mt-1 text-xs text-gray-500">
          Link to data subject nodes (e.g., Employee, Customer)
        </p>
      </div>

      {/* GDC */}
      <div>
        <label htmlFor="entity-gdc" className="block text-sm font-medium text-gray-700 mb-2">
          Global Data Categories (GDC)
        </label>
        <Select
          isMulti
          inputId="entity-gdc"
          options={gdcOptions}
          value={formData.gdc.map(g => ({ value: g, label: g }))}
          onChange={selected => onChange({ gdc: (selected || []).map((s: any) => s.value) })}
          placeholder="Select GDC..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Global Data Categories"
          aria-describedby="gdc-help"
        />
        <p id="gdc-help" className="mt-1 text-xs text-gray-500">
          Link to global data category nodes
        </p>
      </div>

      {/* Sensitive Data Categories */}
      <div>
        <label htmlFor="entity-sensitive" className="block text-sm font-medium text-gray-700 mb-2">
          Sensitive Data Categories
        </label>
        <Select
          isMulti
          inputId="entity-sensitive"
          options={sensitiveDataOptions}
          value={formData.sensitive_data_categories.map(sdc => ({ value: sdc, label: sdc }))}
          onChange={selected => onChange({ sensitive_data_categories: (selected || []).map((s: any) => s.value) })}
          placeholder="Select sensitive data categories..."
          styles={reactSelectStyles}
          theme={reactSelectTheme}
          aria-label="Sensitive Data Categories"
          aria-describedby="sensitive-help"
        />
        <p id="sensitive-help" className="mt-1 text-xs text-gray-500">
          Link to sensitive data category nodes (e.g., Biometric, Genetic)
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
              Entity mappings create graph relationships (e.g., <code className="bg-blue-100 px-1 rounded">Rule -[:HAS_DATA_CATEGORY]→ DataCategory</code>).
              These enable semantic search and precedent case matching.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
