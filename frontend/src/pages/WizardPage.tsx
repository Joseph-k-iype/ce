import { useEffect, useRef } from 'react';
import { useWizardStore } from '../stores/wizardStore';
import { WizardStepper } from '../components/wizard/WizardStepper';
import { WizardContainer } from '../components/wizard/WizardContainer';
import { saveWizardSession } from '../services/wizardApi';
import gsap from 'gsap';

export function WizardPage() {
  const { currentStep, sessionId } = useWizardStore();
  const pageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pageRef.current) {
      gsap.fromTo(pageRef.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.4 });
    }
  }, []);

  const handleSave = async () => {
    if (sessionId) {
      try {
        await saveWizardSession(sessionId);
        useWizardStore.getState().saveToLocalStorage();
        alert('Session saved successfully');
      } catch {
        alert('Failed to save session');
      }
    }
  };

  return (
    <div ref={pageRef} className="flex-1 flex flex-col h-full bg-slate-50">
      <div className="bg-white border-b border-gray-200 px-8 py-5 flex items-center justify-between shadow-sm relative overflow-hidden shrink-0">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-400 via-purple-500 to-purple-600"></div>
        <div className="relative z-10">
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Policy Generator</h1>
          <p className="text-sm text-gray-500 mt-1.5 font-medium">
            Create deterministic compliance rules with AI assistance.
          </p>
        </div>
        <div className="relative z-10 flex items-center gap-6">
          <div className="pt-2">
            <WizardStepper currentStep={currentStep} />
          </div>
          {currentStep >= 4 && sessionId && (
            <button
              onClick={handleSave}
              className="px-5 py-2.5 bg-purple-600 text-white text-sm font-semibold rounded-lg shadow-md hover:bg-purple-700 transition-colors"
            >
              Save Protocol
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden relative p-8">
        <div className="h-full max-w-5xl mx-auto flex flex-col">
          <WizardContainer />
        </div>
      </div>
    </div>
  );
}
