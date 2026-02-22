interface Props {
  currentStep: number;
  onBack: () => void;
  onNext: () => void;
  canGoNext: boolean;
  nextLabel?: string;
  isProcessing?: boolean;
}

export function WizardNavigation({ currentStep, onBack, onNext, canGoNext, nextLabel, isProcessing }: Props) {
  return (
    <div className="flex justify-between mt-6 pt-4">
      <button
        onClick={onBack}
        disabled={currentStep <= 1}
        className="px-5 py-2 text-sm text-gray-600 border border-gray-300 rounded-full hover:bg-gray-50 disabled:opacity-40 transition-colors"
      >
        Back
      </button>
      <button
        onClick={onNext}
        disabled={!canGoNext || isProcessing}
        className="btn-red px-8"
      >
        {isProcessing ? 'Processing...' : nextLabel || 'Next'}
      </button>
    </div>
  );
}
