import { useMutation } from '@tanstack/react-query';
import { evaluateRules } from '../services/evaluatorApi';
import type { RulesEvaluationRequest } from '../types/api';

export function useEvaluation() {
  return useMutation({
    mutationFn: (request: RulesEvaluationRequest) => evaluateRules(request),
  });
}
