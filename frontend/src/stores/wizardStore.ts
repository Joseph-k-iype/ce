import { create } from 'zustand';

interface WizardState {
  sessionId: string | null;
  currentStep: number;
  agenticMode: boolean;
  // Step 1
  originCountry: string;
  receivingCountries: string[];
  originLegalEntity: string[];
  receivingLegalEntity: string[];
  // Step 2
  dataCategories: string[];
  purposesOfProcessing: string[];
  processL1: string[];
  processL2: string[];
  processL3: string[];
  groupDataCategories: string[];
  sensitiveDataCategories: string[];
  regulators: string[];
  authorities: string[];
  validUntil: string;
  // Step 3
  ruleText: string;
  isPiiRelated: boolean;
  // AI results
  analysisResult: Record<string, unknown> | null;
  dictionaryResult: Record<string, unknown> | null;
  proposal: Record<string, unknown> | null;
  // Step 4
  editedRuleDefinition: Record<string, unknown> | null;
  editedTermsDictionary: Record<string, unknown> | null;
  // Step 5
  sandboxGraphName: string | null;
  sandboxTestResults: Record<string, unknown>[];
  // Step 6
  approved: boolean;
  // Status
  isProcessing: boolean;
  error: string | null;
  savedSessionId: string | null;

  setSessionId: (id: string) => void;
  setStep: (step: number) => void;
  setAgenticMode: (m: boolean) => void;
  setOriginCountry: (c: string) => void;
  setReceivingCountries: (c: string[]) => void;
  setOriginLegalEntity: (e: string[]) => void;
  setReceivingLegalEntity: (e: string[]) => void;
  setDataCategories: (c: string[]) => void;
  setPurposesOfProcessing: (p: string[]) => void;
  setProcessL1: (p: string[]) => void;
  setProcessL2: (p: string[]) => void;
  setProcessL3: (p: string[]) => void;
  setGroupDataCategories: (g: string[]) => void;
  setSensitiveDataCategories: (s: string[]) => void;
  setRegulators: (r: string[]) => void;
  setAuthorities: (a: string[]) => void;
  setValidUntil: (d: string) => void;
  setRuleText: (t: string) => void;
  setIsPiiRelated: (p: boolean) => void;
  setAnalysisResult: (r: Record<string, unknown>) => void;
  setDictionaryResult: (r: Record<string, unknown>) => void;
  setProposal: (p: Record<string, unknown> | null) => void;
  setEditedRuleDefinition: (r: Record<string, unknown>) => void;
  setEditedTermsDictionary: (r: Record<string, unknown>) => void;
  setSandboxGraphName: (n: string | null) => void;
  setSandboxTestResults: (r: Record<string, unknown>[]) => void;
  addSandboxTestResult: (r: Record<string, unknown>) => void;
  clearSandboxTestResults: () => void;
  setApproved: (a: boolean) => void;
  setProcessing: (p: boolean) => void;
  setError: (e: string | null) => void;
  setSavedSessionId: (id: string | null) => void;
  reset: () => void;
  loadFromSession: (session: Record<string, unknown>) => void;
  saveToLocalStorage: () => void;
  loadFromLocalStorage: () => boolean;
}

const initialState = {
  sessionId: null as string | null,
  currentStep: 1,
  agenticMode: false,
  originCountry: '',
  receivingCountries: [] as string[],
  originLegalEntity: [] as string[],
  receivingLegalEntity: [] as string[],
  dataCategories: [] as string[],
  purposesOfProcessing: [] as string[],
  processL1: [] as string[],
  processL2: [] as string[],
  processL3: [] as string[],
  groupDataCategories: [] as string[],
  sensitiveDataCategories: [] as string[],
  regulators: [] as string[],
  authorities: [] as string[],
  validUntil: '',
  ruleText: '',
  isPiiRelated: false,
  analysisResult: null as Record<string, unknown> | null,
  dictionaryResult: null as Record<string, unknown> | null,
  proposal: null as Record<string, unknown> | null,
  editedRuleDefinition: null as Record<string, unknown> | null,
  editedTermsDictionary: null as Record<string, unknown> | null,
  sandboxGraphName: null as string | null,
  sandboxTestResults: [] as Record<string, unknown>[],
  approved: false,
  isProcessing: false,
  error: null as string | null,
  savedSessionId: null as string | null,
};

export const useWizardStore = create<WizardState>((set, get) => ({
  ...initialState,

  setSessionId: (id) => set({ sessionId: id }),
  setStep: (step) => set({ currentStep: step }),
  setAgenticMode: (m) => set({ agenticMode: m }),
  setOriginCountry: (c) => set({ originCountry: c }),
  setReceivingCountries: (c) => set({ receivingCountries: c }),
  setOriginLegalEntity: (e) => set({ originLegalEntity: e }),
  setReceivingLegalEntity: (e) => set({ receivingLegalEntity: e }),
  setDataCategories: (c) => set({ dataCategories: c }),
  setPurposesOfProcessing: (p) => set({ purposesOfProcessing: p }),
  setProcessL1: (p) => set({ processL1: p }),
  setProcessL2: (p) => set({ processL2: p }),
  setProcessL3: (p) => set({ processL3: p }),
  setGroupDataCategories: (g) => set({ groupDataCategories: g }),
  setSensitiveDataCategories: (s) => set({ sensitiveDataCategories: s }),
  setRegulators: (r) => set({ regulators: r }),
  setAuthorities: (a) => set({ authorities: a }),
  setValidUntil: (d) => set({ validUntil: d }),
  setRuleText: (t) => set({ ruleText: t }),
  setIsPiiRelated: (p) => set({ isPiiRelated: p }),
  setAnalysisResult: (r) => set({ analysisResult: r }),
  setDictionaryResult: (r) => set({ dictionaryResult: r }),
  setProposal: (p) => set({ proposal: p }),
  setEditedRuleDefinition: (r) => set({ editedRuleDefinition: r }),
  setEditedTermsDictionary: (r) => set({ editedTermsDictionary: r }),
  setSandboxGraphName: (n) => set({ sandboxGraphName: n }),
  setSandboxTestResults: (r) => set({ sandboxTestResults: r }),
  addSandboxTestResult: (r) => set((s) => ({ sandboxTestResults: [...s.sandboxTestResults, r] })),
  clearSandboxTestResults: () => set({ sandboxTestResults: [] }),
  setApproved: (a) => set({ approved: a }),
  setProcessing: (p) => set({ isProcessing: p }),
  setError: (e) => set({ error: e }),
  setSavedSessionId: (id) => set({ savedSessionId: id }),
  reset: () => {
    localStorage.removeItem('wizardState');
    set(initialState);
  },

  loadFromSession: (session) => {
    set({
      sessionId: session.session_id as string,
      currentStep: session.current_step as number || 1,
      agenticMode: session.agentic_mode as boolean || false,
      originCountry: session.origin_country as string || '',
      receivingCountries: session.receiving_countries as string[] || [],
      originLegalEntity: (Array.isArray(session.origin_legal_entity) ? session.origin_legal_entity : session.origin_legal_entity ? [session.origin_legal_entity as string] : []) as string[],
      receivingLegalEntity: (Array.isArray(session.receiving_legal_entity) ? session.receiving_legal_entity : session.receiving_legal_entity ? [session.receiving_legal_entity as string] : []) as string[],
      dataCategories: session.data_categories as string[] || [],
      purposesOfProcessing: session.purposes_of_processing as string[] || [],
      processL1: session.process_l1 as string[] || [],
      processL2: session.process_l2 as string[] || [],
      processL3: session.process_l3 as string[] || [],
      groupDataCategories: session.group_data_categories as string[] || [],
      sensitiveDataCategories: session.sensitive_data_categories as string[] || [],
      regulators: session.regulators as string[] || [],
      authorities: session.authorities as string[] || [],
      validUntil: session.valid_until as string || '',
      ruleText: session.rule_text as string || '',
      analysisResult: session.analysis_result as Record<string, unknown> || null,
      dictionaryResult: session.dictionary_result as Record<string, unknown> || null,
      proposal: session.proposal as Record<string, unknown> || null,
      editedRuleDefinition: session.edited_rule_definition as Record<string, unknown> || null,
      editedTermsDictionary: session.edited_terms_dictionary as Record<string, unknown> || null,
      sandboxGraphName: session.sandbox_graph_name as string || null,
      sandboxTestResults: session.sandbox_test_results as Record<string, unknown>[] || [],
      approved: session.approved as boolean || false,
      error: session.error_message as string || null,
    });
  },

  saveToLocalStorage: () => {
    const state = get();
    const toSave = {
      sessionId: state.sessionId,
      currentStep: state.currentStep,
      agenticMode: state.agenticMode,
      originCountry: state.originCountry,
      receivingCountries: state.receivingCountries,
      originLegalEntity: state.originLegalEntity,
      receivingLegalEntity: state.receivingLegalEntity,
      dataCategories: state.dataCategories,
      purposesOfProcessing: state.purposesOfProcessing,
      processL1: state.processL1,
      processL2: state.processL2,
      processL3: state.processL3,
      groupDataCategories: state.groupDataCategories,
      sensitiveDataCategories: state.sensitiveDataCategories,
      regulators: state.regulators,
      authorities: state.authorities,
      validUntil: state.validUntil,
      ruleText: state.ruleText,
      editedRuleDefinition: state.editedRuleDefinition,
    };
    localStorage.setItem('wizardState', JSON.stringify(toSave));
  },

  loadFromLocalStorage: () => {
    try {
      const stored = localStorage.getItem('wizardState');
      if (stored) {
        const parsed = JSON.parse(stored);
        set(parsed);
        return true;
      }
    } catch { /* ignore */ }
    return false;
  },
}));
