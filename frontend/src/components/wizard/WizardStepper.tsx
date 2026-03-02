const steps = ['Rule Input', 'AI Analysis', 'Metadata', 'Data Sources', 'Review', 'Sandbox Test', 'Approve'];

export function WizardStepper({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center gap-0 mb-6">
      {steps.map((label, i) => {
        const stepNum = i + 1;
        const isActive = stepNum === currentStep;
        const isDone = stepNum < currentStep;
        return (
          <div key={i} className="flex items-center">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs tracking-wide ${
              isActive ? 'step-pill-active' :
              isDone ? 'text-gray-500' :
              'text-gray-300'
            }`}>
              <span className={`w-5 h-5 flex items-center justify-center rounded-full text-[10px] font-semibold ${
                isActive ? 'bg-white text-gray-900' :
                isDone ? 'bg-gray-300 text-white' :
                'bg-gray-100 text-gray-400'
              }`}>{stepNum}</span>
              <span className="hidden sm:inline font-medium">{label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`w-6 h-px ${isDone ? 'bg-gray-400' : 'bg-gray-200'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
