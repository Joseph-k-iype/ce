/**
 * Dimension Configuration Service
 *
 * Centralized registry of all dimensions that can be used in logic trees.
 * Defines how each dimension maps to graph nodes and relationships.
 */

import type { DimensionConfig, DropdownDataResponse, SelectOption } from '../components/shared/LogicTreeBuilder/types';

/**
 * All available dimension configurations
 */
export const DIMENSION_CONFIGS: DimensionConfig[] = [
  {
    name: 'OriginCountry',
    label: 'Origin Country',
    category: 'geography',
    allowMultiSelect: true,
    allowCreate: false,  // Countries are pre-defined
    nodeLabel: 'Country',
    relationshipType: 'ORIGINATES_FROM'
  },
  {
    name: 'ReceivingCountry',
    label: 'Receiving Country',
    category: 'geography',
    allowMultiSelect: true,
    allowCreate: false,
    nodeLabel: 'Country',
    relationshipType: 'RECEIVED_IN'
  },
  {
    name: 'DataCategory',
    label: 'Data Category',
    category: 'data',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'DataCategory',
    relationshipType: 'HAS_DATA_CATEGORY'
  },
  {
    name: 'Purpose',
    label: 'Purpose of Processing',
    category: 'data',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'PurposeOfProcessing',
    relationshipType: 'HAS_PURPOSE'
  },
  {
    name: 'Process',
    label: 'Process',
    category: 'data',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'Process',
    relationshipType: 'HAS_PROCESS'
  },
  {
    name: 'Regulator',
    label: 'Regulator',
    category: 'regulatory',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'Regulator',
    relationshipType: 'HAS_REGULATOR'
  },
  {
    name: 'Authority',
    label: 'Supervisory Authority',
    category: 'regulatory',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'Authority',
    relationshipType: 'HAS_AUTHORITY'
  },
  {
    name: 'DataSubject',
    label: 'Data Subject',
    category: 'data',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'DataSubject',
    relationshipType: 'HAS_DATA_SUBJECT'
  },
  {
    name: 'GDC',
    label: 'Group Data Category (GDC)',
    category: 'data',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'GDC',
    relationshipType: 'HAS_GDC'
  },
  {
    name: 'SensitiveDataCategory',
    label: 'Sensitive Data Category',
    category: 'data',
    allowMultiSelect: true,
    allowCreate: true,
    createEndpoint: '/metadata/nodes',
    nodeLabel: 'SensitiveDataCategory',
    relationshipType: 'HAS_SENSITIVE_DATA_CATEGORY'
  }
];

/**
 * Get dimension configuration by name
 */
export function getDimensionConfig(name: string): DimensionConfig | undefined {
  return DIMENSION_CONFIGS.find(d => d.name === name);
}

/**
 * Get dimensions by category
 */
export function getDimensionsByCategory(category: 'geography' | 'data' | 'regulatory'): DimensionConfig[] {
  return DIMENSION_CONFIGS.filter(d => d.category === category);
}

/**
 * Get dropdown options for a specific dimension
 */
export function getDimensionOptions(
  dimensionName: string,
  dropdownData: DropdownDataResponse | null
): SelectOption[] {
  if (!dropdownData) {
    return [];
  }

  const config = getDimensionConfig(dimensionName);
  if (!config) {
    return [];
  }

  switch (dimensionName) {
    case 'OriginCountry':
    case 'ReceivingCountry':
      return (dropdownData.countries || []).map((c: string) => ({
        value: c,
        label: c
      }));

    case 'DataCategory':
      return (dropdownData.data_categories || []).map((dc: any) => ({
        value: typeof dc === 'string' ? dc : dc.name,
        label: typeof dc === 'string' ? dc : dc.name
      }));

    case 'Purpose':
      return (dropdownData.purposes || []).map((p: string) => ({
        value: p,
        label: p
      }));

    case 'Process':
      // Combine all process levels
      const allProcs = [
        ...(dropdownData.processes?.l1 || []),
        ...(dropdownData.processes?.l2 || []),
        ...(dropdownData.processes?.l3 || [])
      ];
      return Array.from(new Set(allProcs)).map(p => ({
        value: p,
        label: p
      }));

    case 'Regulator':
      return (dropdownData.regulators || []).map((r: any) => ({
        value: typeof r === 'string' ? r : r.name,
        label: typeof r === 'string' ? r : r.name
      }));

    case 'Authority':
      return (dropdownData.authorities || []).map((a: any) => ({
        value: typeof a === 'string' ? a : a.name,
        label: typeof a === 'string' ? a : a.name
      }));

    case 'DataSubject':
      return (dropdownData.data_subjects || []).map((ds: any) => ({
        value: typeof ds === 'string' ? ds : ds.name,
        label: typeof ds === 'string' ? ds : ds.name
      }));

    case 'GDC':
      return (dropdownData.gdc || []).map((gdc: any) => ({
        value: typeof gdc === 'string' ? gdc : gdc.name,
        label: typeof gdc === 'string' ? gdc : gdc.name
      }));

    case 'SensitiveDataCategory':
      return (dropdownData.sensitive_data_categories || []).map((sdc: any) => ({
        value: typeof sdc === 'string' ? sdc : sdc.name,
        label: typeof sdc === 'string' ? sdc : sdc.name
      }));

    default:
      return [];
  }
}

/**
 * Get all dimensions grouped by category
 */
export function getGroupedDimensions(): Record<string, DimensionConfig[]> {
  return {
    geography: getDimensionsByCategory('geography'),
    data: getDimensionsByCategory('data'),
    regulatory: getDimensionsByCategory('regulatory')
  };
}

/**
 * Validate dimension name
 */
export function isValidDimension(name: string): boolean {
  return DIMENSION_CONFIGS.some(d => d.name === name);
}
