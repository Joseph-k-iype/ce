import { create } from 'zustand';
import type { RulesEvaluationResponse, RulesEvaluationRequest } from '../types/api';

interface EvaluationState {
  result: RulesEvaluationResponse | null;
  scenarioInput: RulesEvaluationRequest | null;
  isLoading: boolean;
  error: string | null;

  setResult: (r: RulesEvaluationResponse) => void;
  setScenarioInput: (input: RulesEvaluationRequest) => void;
  setLoading: (l: boolean) => void;
  setError: (e: string | null) => void;
  clear: () => void;
}

export const useEvaluationStore = create<EvaluationState>((set) => ({
  result: null,
  scenarioInput: null,
  isLoading: false,
  error: null,

  setResult: (r) => set({ result: r, isLoading: false, error: null }),
  setScenarioInput: (input) => set({ scenarioInput: input }),
  setLoading: (l) => set({ isLoading: l }),
  setError: (e) => set({ error: e, isLoading: false }),
  clear: () => set({ result: null, scenarioInput: null, error: null, isLoading: false }),
}));
