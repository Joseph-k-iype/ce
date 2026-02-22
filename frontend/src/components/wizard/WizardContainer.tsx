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
  const autoProgressedRef = useRef(false);

  // SSE for step 2 (AI analysis)
  const sseSessionId = store.currentStep === 2 ? store.sessionId : null;
  const { events, connected } = useAgentEvents(sseSessionId);

  const handleNext = useCallback(async () => {
    const state = useWizardStore.getState();
    const step = state.currentStep;
    let sessionId = state.sessionId;

    console.log(`[Wizard] handleNext called for step ${step}, agenticMode: ${state.agenticMode}`);
    store.setError(null);
    store.setProcessing(true);

    try {
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
              origin_legal_entity: state.originLegalEntity,
              receiving_legal_entity: state.receivingLegalEntity,
              rule_text: state.ruleText,
              is_pii_related: state.isPiiRelated,
              agentic_mode: state.agenticMode,
            },
          });
        }
        store.setStep(2);
        return;
      }

      if (step === 2 && sessionId) {
        console.log('[Wizard] Step 2 complete event, fetching results...');

        // Race condition fix: retry fetching session results if results are missing
        let session = await getWizardSession(sessionId);
        let retries = 0;
        const maxRetries = 5;

        while (session.status !== 'failed' && !session.analysis_result && retries < maxRetries) {
          console.log(`[Wizard] Results not ready (attempt ${retries + 1}/${maxRetries}), waiting...`);
          await new Promise(resolve => setTimeout(resolve, 1000 + (retries * 500)));
          session = await getWizardSession(sessionId);
          retries++;
        }

        console.log('[Wizard] Final session status for transition:', session.status);

        if (session.status === 'failed') {
          store.setError(session.error_message || 'AI processing failed. Go Back to edit and retry.');
          store.setProcessing(false);
          return;
        }

        // Populate store with whatever results we have
        if (session.analysis_result) store.setAnalysisResult(session.analysis_result);
        if (session.dictionary_result) store.setDictionaryResult(session.dictionary_result);
        if (session.edited_rule_definition) store.setEditedRuleDefinition(session.edited_rule_definition);
        if (session.edited_terms_dictionary) store.setEditedTermsDictionary(session.edited_terms_dictionary);
        if (session.proposal) store.setProposal(session.proposal);

        // Notify backend that we are moving off step 2
        try {
          await submitWizardStep(sessionId, { step: 2, data: {} });
        } catch (e) {
          console.warn('[Wizard] submitWizardStep(2) failed, continuing anyway...', e);
        }

        if (state.agenticMode) {
          console.log('[Wizard] Agentic mode: jumping to step 4 (Review)');
          store.setStep(4);
        } else {
          console.log('[Wizard] Standard mode: advancing to step 3 (Metadata)');
          store.setStep(3);
        }

        store.setProcessing(false);
        return;
      }

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

      if (step === 4) {
        store.setStep(5);
        store.setProcessing(false);
        return;
      }

      if (step === 5 && sessionId && !state.sandboxGraphName) {
        try {
          const result = await loadSandbox(sessionId);
          store.setSandboxGraphName(result.sandbox_graph);
        } catch (sandboxErr: any) {
          let msg = 'Failed to load sandbox';
          if (sandboxErr?.response?.data?.detail) {
            msg = sandboxErr.response.data.detail;
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

      if (step === 5 && state.sandboxGraphName) {
        store.setStep(6);
        store.setProcessing(false);
        return;
      }

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

      if (step < 6) {
        store.setStep(step + 1);
      }
    } catch (err: any) {
      console.error('[Wizard] handleNext error:', err);
      let message = 'Step submission failed';
      if (err?.response?.data?.detail) {
        message = `Request failed: ${err.response.data.detail}`;
      } else if (err instanceof Error) {
        message = err.message;
      }
      store.setError(message);
    }

    store.setProcessing(false);
  }, [store, navigate]);

  useEffect(() => {
    const isComplete = events.some(e => e.event_type === 'workflow_complete');

    if (store.currentStep === 2 && isComplete && !autoProgressedRef.current) {
      console.log('[Wizard] workflow_complete detected via SSE, triggering auto-progression...');
      autoProgressedRef.current = true;

      const timer = setTimeout(() => {
        if (useWizardStore.getState().currentStep === 2) {
          handleNext();
        }
      }, 1000);
      return () => clearTimeout(timer);
    }

    if (store.currentStep !== 2) {
      autoProgressedRef.current = false;
    }
  }, [events, store.currentStep, handleNext]);

  // Polling fallback: check session status every 3s while on step 2 and processing
  // This catches the case where SSE events are missed (network issues, connection timing)
  useEffect(() => {
    if (store.currentStep !== 2 || !store.isProcessing || !store.sessionId) return;

    const pollInterval = setInterval(async () => {
      try {
        const session = await getWizardSession(store.sessionId!);
        if (session.status === 'awaiting_review' || session.status === 'failed') {
          console.log(`[Wizard] Poll detected completion: status=${session.status}`);
          if (!autoProgressedRef.current) {
            autoProgressedRef.current = true;
            clearInterval(pollInterval);
            handleNext();
          }
        }
      } catch (err) {
        console.warn('[Wizard] Poll error:', err);
      }
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [store.currentStep, store.isProcessing, store.sessionId, handleNext]);

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
      case 2: return !store.isProcessing && (!!store.analysisResult || !!store.proposal);
      case 3: return true;
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

  const handleBack = () => {
    if (store.currentStep > 1) {
      store.setError(null);
      if (store.currentStep >= 5) {
        if (store.sandboxGraphName) store.setSandboxGraphName(null);
        store.clearSandboxTestResults();
      }

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
