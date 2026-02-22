import { useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWizardStore } from '../../stores/wizardStore';
import { useAgentEvents } from '../../hooks/useAgentEvents';
import { startWizardSession, submitWizardStep, getWizardSession, loadSandbox, approveWizard } from '../../services/wizardApi';
import { WizardNavigation } from './WizardNavigation';
import { AgentProgressPanel } from './shared/AgentProgressPanel';
import { Step1RuleInput } from './steps/Step1RuleInput';
import { Step2AIAnalysis } from './steps/Step2AIAnalysis';
import { Step2Metadata } from './steps/Step2Metadata';
import { Step4Review } from './steps/Step4Review';
import { Step5SandboxTest } from './steps/Step5SandboxTest';
import { Step6Approve } from './steps/Step6Approve';
import gsap from 'gsap';

// New workflow order:
// 1: Rule Input (text + country + PII) → triggers AI
// 2: AI Analysis (auto-progress, read-only)
// 3: Metadata (pre-filled from AI, editable)
// 4: Review
// 5: Sandbox Test
// 6: Approve
const stepComponents: Record<number, React.FC> = {
  1: Step1RuleInput,
  2: Step2AIAnalysis,
  3: Step2Metadata,
  4: Step4Review,
  5: Step5SandboxTest,
  6: Step6Approve,
};

export function WizardContainer() {
  const store = useWizardStore();
  const navigate = useNavigate();
  const stepRef = useRef<HTMLDivElement>(null);
  const prevStepRef = useRef(store.currentStep);

  // SSE for step 2 (AI analysis)
  const sseSessionId = store.currentStep === 2 ? store.sessionId : null;
  const { events, connected } = useAgentEvents(sseSessionId);

  // Auto-progress from Step 2 when workflow is complete
  useEffect(() => {
    if (store.currentStep === 2 && events.some(e => e.event_type === 'workflow_complete')) {
      const timer = setTimeout(() => {
        if (useWizardStore.getState().currentStep === 2) {
          handleNext();
        }
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [events, store.currentStep]);

  // Animate step transitions
  useEffect(() => {
    if (stepRef.current && prevStepRef.current !== store.currentStep) {
      const direction = store.currentStep > prevStepRef.current ? 1 : -1;
      gsap.fromTo(
        stepRef.current,
        { opacity: 0, x: direction * 30 },
        { opacity: 1, x: 0, duration: 0.35, ease: 'power2.out' }
      );
      prevStepRef.current = store.currentStep;
    }
  }, [store.currentStep]);

  const canGoNext = useCallback(() => {
    switch (store.currentStep) {
      case 1: return !!store.originCountry && store.ruleText.length > 10;
      case 2: return !store.isProcessing && (!!store.analysisResult || !!store.proposal); // AI must complete
      case 3: return true; // Metadata is all optional
      case 4: return !!store.editedRuleDefinition;
      case 5: return !!store.editedRuleDefinition;
      case 6: return true;
      default: return false;
    }
  }, [store]);

  const getNextLabel = () => {
    const step = store.currentStep;
    if (step === 1) return store.agenticMode ? 'Generate Policy' : 'Analyze Rule';
    if (step === 2) return store.isProcessing ? 'Processing...' : (store.agenticMode ? 'Review Proposal' : 'Configure Metadata');
    if (step === 5 && !store.sandboxGraphName) return 'Load Sandbox';
    if (step === 6) return 'Approve & Load';
    return 'Next';
  };

  const handleNext = async () => {
    const state = useWizardStore.getState();
    const step = state.currentStep;
    let sessionId = state.sessionId;

    store.setError(null);
    store.setProcessing(true);

    try {
      // Step 1: create session + submit rule text + country → triggers AI
      if (step === 1) {
        if (!sessionId) {
          const { session_id } = await startWizardSession();
          store.setSessionId(session_id);
          sessionId = session_id;
        }
        if (sessionId) {
          await submitWizardStep(sessionId, {
            step: 1,
            data: {
              origin_country: state.originCountry,
              receiving_countries: state.receivingCountries,
              origin_legal_entity: Array.isArray(state.originLegalEntity) ? state.originLegalEntity : state.originLegalEntity ? [state.originLegalEntity] : [],
              receiving_legal_entity: state.receivingLegalEntity,
              rule_text: state.ruleText,
              is_pii_related: state.isPiiRelated,
              agentic_mode: state.agenticMode,
            },
          });
        }
        store.setStep(2);
        // Don't clear isProcessing — Step 2 shows AI progress
        return;
      }

      // Step 2: AI analysis done → poll session for results
      if (step === 2 && sessionId) {
        const session = await getWizardSession(sessionId);
        if (session.status === 'failed') {
          store.setError(session.error_message || 'AI processing failed. Go Back to edit and retry.');
          store.setProcessing(false);
          return;
        }
        if (session.analysis_result) store.setAnalysisResult(session.analysis_result);
        if (session.dictionary_result) store.setDictionaryResult(session.dictionary_result);
        if (session.edited_rule_definition) store.setEditedRuleDefinition(session.edited_rule_definition);
        if (session.edited_terms_dictionary) store.setEditedTermsDictionary(session.edited_terms_dictionary);
        if (session.proposal) store.setProposal(session.proposal);
        
        await submitWizardStep(sessionId, { step: 2, data: {} });
        
        // In agentic mode, we can skip metadata if results are good, or go straight to review
        if (state.agenticMode) {
            store.setStep(4);
        } else {
            store.setStep(3);
        }
        
        store.setProcessing(false);
        return;
      }

      // Step 3: submit metadata
      if (step === 3 && sessionId) {
        await submitWizardStep(sessionId, {
          step: 3,
          data: {
            data_categories: state.dataCategories,
            purposes_of_processing: state.purposesOfProcessing,
            process_l1: state.processL1,
            process_l2: state.processL2,
            process_l3: state.processL3,
            group_data_categories: state.groupDataCategories,
            valid_until: state.validUntil || null,
          },
        });
        store.setStep(4);
        store.setProcessing(false);
        return;
      }

      // Step 4: review → advance to sandbox
      if (step === 4) {
        store.setStep(5);
        store.setProcessing(false);
        return;
      }

      // Step 5: load sandbox
      if (step === 5 && sessionId && !state.sandboxGraphName) {
        try {
          const result = await loadSandbox(sessionId);
          store.setSandboxGraphName(result.sandbox_graph);
        } catch (sandboxErr: unknown) {
          let msg = 'Failed to load sandbox';
          if (sandboxErr && typeof sandboxErr === 'object' && 'response' in sandboxErr) {
            const axiosErr = sandboxErr as { response?: { data?: { detail?: string } } };
            msg = axiosErr.response?.data?.detail || msg;
          } else if (sandboxErr instanceof Error) {
            msg = sandboxErr.message;
          }
          store.setError(`Sandbox Error: ${msg}. You can go Back to edit the rule and try again.`);
          store.setProcessing(false);
          return;
        }
        store.setProcessing(false);
        return;
      }

      // Step 5: sandbox already loaded, advance to approve
      if (step === 5 && state.sandboxGraphName) {
        store.setStep(6);
        store.setProcessing(false);
        return;
      }

      // Step 6: approve
      if (step === 6 && sessionId) {
        await approveWizard(sessionId);
        store.setApproved(true);
        store.setProcessing(false);
        setTimeout(() => {
          store.reset();
          navigate('/');
        }, 1500);
        return;
      }

      // Fallback advance
      if (step < 6) {
        store.setStep(step + 1);
      }
    } catch (err: unknown) {
      let message = 'Step submission failed';
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } };
        const status = axiosErr.response?.status;
        const detail = axiosErr.response?.data?.detail;
        message = `Request failed (${status}): ${detail || 'Unknown error'}`;
      } else if (err instanceof Error) {
        message = err.message;
      }
      store.setError(message);
    }

    store.setProcessing(false);
  };

  const handleBack = () => {
    if (store.currentStep > 1) {
      store.setError(null);
      if (store.currentStep >= 5) {
        if (store.sandboxGraphName) store.setSandboxGraphName(null);
        store.clearSandboxTestResults();
      }
      
      // Handle back transition for skipped steps in agentic mode
      if (store.agenticMode && store.currentStep === 4) {
          store.setStep(2);
      } else {
          store.setStep(store.currentStep - 1);
      }
    }
  };

  const StepComponent = stepComponents[store.currentStep] || Step1RuleInput;

  return (
    <div className="space-y-4">
      <div ref={stepRef} className="bg-white rounded-xl border border-gray-200 p-6">
        <StepComponent />
      </div>

      {store.sessionId && store.currentStep === 2 && store.isProcessing && (
        <AgentProgressPanel events={events} connected={connected} />
      )}

      {store.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-red-800">Error</p>
              <p className="text-sm text-red-700 mt-0.5">{store.error}</p>
            </div>
            <button onClick={() => store.setError(null)} className="text-red-400 hover:text-red-600 text-sm ml-3 shrink-0">&times;</button>
          </div>
        </div>
      )}

      <WizardNavigation
        currentStep={store.currentStep}
        onBack={handleBack}
        onNext={handleNext}
        canGoNext={canGoNext()}
        nextLabel={getNextLabel()}
        isProcessing={store.isProcessing}
      />
    </div>
  );
}
