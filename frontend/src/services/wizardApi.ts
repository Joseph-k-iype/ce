import api from './api';
import type { WizardSession, WizardStepData, SavedSession, TriggerLogicResponse } from '../types/wizard';
import type { LogicNode } from '../components/shared/LogicTreeBuilder/types';

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

export async function getTriggerLogic(sessionId: string): Promise<TriggerLogicResponse> {
  const { data } = await api.get<TriggerLogicResponse>(`/wizard/session/${sessionId}/trigger-logic`);
  return data;
}

export async function getLogicTree(sessionId: string): Promise<LogicNode> {
  const { data } = await api.get<LogicNode>(`/wizard/session/${sessionId}/logic-tree`);
  return data;
}

export async function updateLogicTree(sessionId: string, logicTree: LogicNode): Promise<{ status: string; logic_tree: LogicNode }> {
  const { data } = await api.put(`/wizard/session/${sessionId}/logic-tree`, logicTree);
  return data;
}

// ===== Graph Selection Functions =====

/**
 * Get a preview of a graph's schema and sample data.
 * Uses the authenticated axios instance to include JWT token.
 */
export async function getGraphPreview(graphName: string): Promise<{
  graph_name: string;
  graph_type: string;
  node_labels: string[];
  relationship_types: string[];
  sample_nodes: any[];
  description: string;
  node_count: number;
}> {
  const { data } = await api.get(`/graphs/${encodeURIComponent(graphName)}/preview`);
  return data;
}

/**
 * Get entity values from selected graphs for use in the logic builder.
 */
export async function getGraphEntities(sessionId: string): Promise<{
  dimension_options: Record<string, string[]>;
}> {
  const { data } = await api.get(`/wizard/session/${sessionId}/graph-entities`);
  return data;
}



/**
 * Get AI-suggested graphs for precedent search
 */
export async function getGraphSuggestions(sessionId: string): Promise<{
  relevant_graphs: Array<{
    graph_name: string;
    relevance_score: number;
    reasoning: string;
    matched_entities: Record<string, string[]>;
    sample_data: any[];
    node_count: number;
  }>;
  confidence: number;
  recommendation: string;
}> {
  const { data } = await api.get(`/wizard/session/${sessionId}/graph-suggestions`);
  return data;
}

/**
 * Get list of available graphs for precedent search
 */
export async function getAvailableGraphs(sessionId: string): Promise<{
  available_graphs: Array<{
    name: string;
    graph_type: string;
    description: string;
    node_labels: string[];
    relationship_types: string[];
    enabled: boolean;
  }>;
  current_selection: string[];
}> {
  const { data } = await api.get(`/wizard/session/${sessionId}/available-graphs`);
  return data;
}

/**
 * Configure which graphs to query for precedent search
 */
export async function configureGraphs(sessionId: string, graphs: string[]): Promise<{
  status: string;
  selected_graphs: string[];
}> {
  const { data } = await api.put(`/wizard/session/${sessionId}/configure-graphs`, { graphs });
  return data;
}

// ===== Graph Trigger Mappings =====

export interface GraphTriggerMapping {
  graph_name: string;
  node_label: string;
  field: string;
  dimension: string;
  filter_expr: string;
}

export async function getGraphTriggerMappings(sessionId: string): Promise<{ mappings: GraphTriggerMapping[] }> {
  const { data } = await api.get(`/wizard/session/${sessionId}/graph-trigger-mappings`);
  return data;
}

export async function saveGraphTriggerMappings(
  sessionId: string,
  mappings: GraphTriggerMapping[]
): Promise<{ status: string; mappings: GraphTriggerMapping[] }> {
  const { data } = await api.put(`/wizard/session/${sessionId}/graph-trigger-mappings`, { mappings });
  return data;
}
