import api from './api';

// Rules CRUD
export async function getAdminRules() {
  const { data } = await api.get('/admin/rules');
  return data;
}

export async function getAdminRule(ruleId: string) {
  const { data } = await api.get(`/admin/rules/${ruleId}`);
  return data;
}

export async function updateAdminRule(ruleId: string, update: Record<string, unknown>) {
  const { data } = await api.put(`/admin/rules/${ruleId}`, update);
  return data;
}

export async function createAdminRule(rule: Record<string, unknown>) {
  const { data } = await api.post('/admin/rules', rule);
  return data;
}

export async function deleteAdminRule(ruleId: string) {
  const { data } = await api.delete(`/admin/rules/${ruleId}`);
  return data;
}

// Country Groups CRUD
export async function getCountryGroups() {
  const { data } = await api.get('/admin/country-groups');
  return data;
}

export async function updateCountryGroup(name: string, update: { add_countries?: string[]; remove_countries?: string[] }) {
  const { data } = await api.put(`/admin/country-groups/${name}`, update);
  return data;
}

export async function createCountryGroup(group: { name: string; countries: string[] }) {
  const { data } = await api.post('/admin/country-groups', group);
  return data;
}

export async function deleteCountryGroup(name: string) {
  const { data } = await api.delete(`/admin/country-groups/${name}`);
  return data;
}

// Dictionary CRUD
export type DictType = 'processes' | 'purposes' | 'data_subjects' | 'gdc';

export async function getDictionaryEntries(dictType: DictType) {
  const { data } = await api.get(`/admin/dictionaries/${dictType}`);
  return data;
}

export async function addDictionaryEntry(dictType: DictType, entry: { name: string; category: string }) {
  const { data } = await api.post(`/admin/dictionaries/${dictType}`, entry);
  return data;
}

export async function deleteDictionaryEntry(dictType: DictType, name: string) {
  const { data } = await api.delete(`/admin/dictionaries/${dictType}/${encodeURIComponent(name)}`);
  return data;
}

// Graph operations
export async function rebuildGraph() {
  const { data } = await api.post('/admin/rebuild-graph');
  return data;
}

export async function getGraphStats() {
  const { data } = await api.get('/admin/graph-stats');
  return data;
}
