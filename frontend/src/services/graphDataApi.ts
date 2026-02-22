import api from './api';
import type { GraphData } from '../types/graph';

export async function getRulesNetwork(): Promise<GraphData> {
  const { data } = await api.get<GraphData>('/graph/rules-network');
  return data;
}

export async function getCountryGroups(): Promise<Record<string, string[]>> {
  const { data } = await api.get<Record<string, string[]>>('/graph/country-groups');
  return data;
}
