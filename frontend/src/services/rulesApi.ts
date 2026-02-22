import api from './api';
import type { RulesOverviewResponse, RulesOverviewTableResponse, DropdownValues } from '../types/api';

export async function getRulesOverview(): Promise<RulesOverviewResponse> {
  const { data } = await api.get<RulesOverviewResponse>('/rules-overview');
  return data;
}

export async function getRulesOverviewTable(params?: Record<string, string>): Promise<RulesOverviewTableResponse> {
  const { data } = await api.get<RulesOverviewTableResponse>('/rules-overview-table', { params });
  return data;
}

export async function getDropdownValues(): Promise<DropdownValues> {
  const { data } = await api.get<DropdownValues>('/all-dropdown-values');
  return data;
}

export async function getCountries(): Promise<string[]> {
  const { data } = await api.get<string[]>('/countries');
  return data;
}

export async function getPurposes(): Promise<string[]> {
  const { data } = await api.get<string[]>('/purposes');
  return data;
}

export async function getLegalEntities(): Promise<Record<string, string[]>> {
  const { data } = await api.get<Record<string, string[]>>('/legal-entities');
  return data;
}

export async function getLegalEntitiesForCountry(country: string): Promise<string[]> {
  const { data } = await api.get<string[]>(`/legal-entities/${encodeURIComponent(country)}`);
  return data;
}

export async function getPurposeOfProcessing(): Promise<string[]> {
  const { data } = await api.get<string[]>('/purpose-of-processing');
  return data;
}
