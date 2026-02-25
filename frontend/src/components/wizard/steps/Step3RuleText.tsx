import { useWizardStore } from '../../../stores/wizardStore';
import { useAgentEvents } from '../../../hooks/useAgentEvents';
import { useRef, useEffect, useMemo } from 'react';
import { TerminalStream } from '../TerminalStream';
import gsap from 'gsap';

export function Step3RuleText() {
  const { ruleText, setRuleText, isPiiRelated, setIsPiiRelated, isProcessing, sessionId } = useWizardStore();
  const { events } = useAgentEvents(isProcessing ? sessionId : null);
  const progressRef = useRef<HTMLDivElement>(null);

  // Calculate progress: prefer progress_pct from events, fallback to counting completed agents
  const progressPct = useMemo(() => {
    const eventList = events || [];
    // Use the latest progress_pct from any event that has it
    for (let i = eventList.length - 1; i >= 0; i--) {
      const evt = eventList[i];
      if (evt.progress_pct != null && evt.progress_pct > 0) {
        return Math.min(100, Math.round(evt.progress_pct));
      }
    }
    // Fallback: count completed agents
    const completedPhases = eventList.filter(e => e.event_type === 'agent_completed').length;
    const totalPhases = 6;
    return Math.min(100, Math.round((completedPhases / totalPhases) * 100));
  }, [events]);

  // Initialize progress bar to 0% on mount
  useEffect(() => {
    if (progressRef.current) {
      gsap.set(progressRef.current, { width: '0%' });
    }
  }, []);

  useEffect(() => {
    if (progressRef.current) {
      gsap.to(progressRef.current, { width: `${progressPct}%`, duration: 0.5, ease: 'power2.out' });
    }
  }, [progressPct]);

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900 mb-1">Step 3: Rule Text</h3>
        <p className="text-xs text-gray-400">
          Describe the compliance rule in natural language. AI agents will analyze it and generate a machine-readable definition.
        </p>
      </div>

      <textarea
        value={ruleText}
        onChange={(e) => setRuleText(e.target.value)}
        disabled={isProcessing}
        placeholder="e.g., Customer financial data originating from the EU must not be transferred to jurisdictions without an adequacy decision unless SCCs are in place and a TIA has been completed..."
        className="w-full h-40 rounded-lg border border-gray-200 py-3 px-4 text-sm text-gray-900 placeholder:text-gray-300 resize-none focus:outline-none focus:border-gray-400 transition-colors"
      />

      <div className="flex items-center justify-between">
        <p className="text-[10px] text-gray-300 tabular-nums">{ruleText.length} characters</p>
        <label className="flex items-center gap-2 cursor-pointer select-none group">
          <div className="relative">
            <input
              type="checkbox"
              checked={isPiiRelated}
              onChange={(e) => setIsPiiRelated(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-8 h-[18px] rounded-full bg-gray-200 peer-checked:bg-gray-900 transition-colors" />
            <div className="absolute top-[3px] left-[3px] w-3 h-3 rounded-full bg-white transition-transform peer-checked:translate-x-[14px]" />
          </div>
          <span className="text-xs text-gray-500 group-hover:text-gray-700 transition-colors">PII Related</span>
        </label>
      </div>

      {/* Agent Workflow Progress */}
      {isProcessing && (
        <div className="card-dark p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-white">AI Agent Processing</span>
            <span className="text-xs text-gray-400">{progressPct}%</span>
          </div>

          {/* Progress bar */}
          <div className="progress-bar">
            <div ref={progressRef} className="progress-bar-fill" />
          </div>

          {/* Event stream */}
          <TerminalStream events={events} maxHeight="16rem" />
        </div>
      )}
    </div>
  );
}
