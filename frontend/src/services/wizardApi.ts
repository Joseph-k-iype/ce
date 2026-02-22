import api from './api';
import type { WizardSession, WizardStepData, SavedSession } from '../types/wizard';

export async function startWizardSession(userId = 'anonymous'): Promise<{ session_id: string }> {
  const { data } = await api.post('/wizard/start-session', { user_id: userId });
  return data;
}

export async function submitWizardStep(sessionId: string, stepData: WizardStepData) {
  const { data } = await api.post(`/wizard/submit-step?session_id=${sessionId}`, stepData);
  return data;
}

export async function getWizardSession(sessionId: string): Promise<WizardSession> {
  const { data } = await api.get<WizardSession>(`/wizard/session/${sessionId}`);
  return data;
}

export async function editRule(sessionId: string, ruleDefinition: Record<string, unknown>) {
  const { data } = await api.put(`/wizard/session/${sessionId}/edit-rule`, { rule_definition: ruleDefinition });
  return data;
}

export async function editTerms(sessionId: string, termsDictionary: Record<string, unknown>) {
  const { data } = await api.put(`/wizard/session/${sessionId}/edit-terms`, { terms_dictionary: termsDictionary });
  return data;
}

export async function loadSandbox(sessionId: string) {
  const { data } = await api.post(`/wizard/session/${sessionId}/load-sandbox`);
  return data;
}

export async function sandboxEvaluate(sessionId: string, evalRequest: Record<string, unknown>) {
  const { data } = await api.post(`/wizard/session/${sessionId}/sandbox-evaluate`, evalRequest);
  return data;
}

export async function approveWizard(sessionId: string, approvedBy = 'admin') {
  const { data } = await api.post(`/wizard/session/${sessionId}/approve`, { approved_by: approvedBy });
  return data;
}

export async function cancelWizard(sessionId: string) {
  const { data } = await api.delete(`/wizard/session/${sessionId}`);
  return data;
}

export async function saveWizardSession(sessionId: string) {
  const { data } = await api.post(`/wizard/save-session?session_id=${sessionId}`);
  return data;
}

export async function listSavedSessions(userId?: string): Promise<SavedSession[]> {
  const params = userId ? { user_id: userId } : {};
  const { data } = await api.get<SavedSession[]>('/wizard/saved-sessions', { params });
  return data;
}

export async function resumeWizardSession(sessionId: string): Promise<WizardSession> {
  const { data } = await api.get<WizardSession>(`/wizard/resume-session/${sessionId}`);
  return data;
}

export async function deleteSavedSession(sessionId: string) {
  const { data } = await api.delete(`/wizard/saved-session/${sessionId}`);
  return data;
}
