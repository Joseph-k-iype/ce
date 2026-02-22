import api from './api';
import type { RulesEvaluationRequest, RulesEvaluationResponse } from '../types/api';

export async function evaluateRules(request: RulesEvaluationRequest): Promise<RulesEvaluationResponse> {
  const { data } = await api.post<RulesEvaluationResponse>('/evaluate-rules', request);
  return data;
}

export async function searchCases(params: Record<string, unknown>) {
  const { data } = await api.post('/search-cases', params);
  return data;
}
