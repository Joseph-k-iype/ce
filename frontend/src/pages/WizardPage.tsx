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
    <div ref={pageRef}>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-bold text-gray-900">Policy Generator</h1>
        {currentStep >= 4 && sessionId && (
          <button onClick={handleSave} className="btn-red">Save</button>
        )}
      </div>
      <WizardStepper currentStep={currentStep} />
      <div className="mt-4">
        <WizardContainer />
      </div>
    </div>
  );
}
