import { useRef, useEffect, useMemo } from 'react';
import { useWizardStore } from '../../../stores/wizardStore';
import { useAgentEvents } from '../../../hooks/useAgentEvents';
import { TerminalStream } from '../TerminalStream';
import gsap from 'gsap';

export function Step2AIAnalysis() {
  const { sessionId, isProcessing, analysisResult, error } = useWizardStore();
  const { events } = useAgentEvents(sessionId); // Always listen if sessionId is present
  const progressRef = useRef<HTMLDivElement>(null);

  // Calculate progress
  const progressPct = useMemo(() => {
    const eventList = events || [];
    for (let i = eventList.length - 1; i >= 0; i--) {
      if (eventList[i].progress_pct != null && eventList[i].progress_pct! > 0) {
        return Math.min(100, Math.round(eventList[i].progress_pct!));
      }
    }
    const completed = eventList.filter(e => e.event_type === 'agent_completed').length;
    const isWorkflowComplete = eventList.some(e => e.event_type === 'workflow_complete');
    if (isWorkflowComplete) return 100;
    return Math.min(95, Math.round((completed / 6) * 100));
  }, [events]);

  const hasResult = !!analysisResult;
  const hasFailed = !!error;

  // Animate progress bar
  useEffect(() => {
    if (progressRef.current) {
      gsap.to(progressRef.current, { width: `${progressPct}%`, duration: 0.5, ease: 'power2.out' });
    }
  }, [progressPct]);

  // Initialize progress bar
  useEffect(() => {
    if (progressRef.current) {
      gsap.set(progressRef.current, { width: '0%' });
    }
  }, []);

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-900 mb-1">
          Step 2: AI Analysis
        </h3>
        <p className="text-xs text-gray-400">
          {hasResult
            ? 'Analysis complete. Advancing to the next step...'
            : hasFailed
              ? 'Analysis failed. Go back to edit your rule text and try again.'
              : 'AI agents are analyzing your rule text and generating a machine-readable definition...'
          }
        </p>
      </div>

      {/* Progress display - show until we have a result OR if still processing */}
      {(isProcessing || !hasResult) && !hasFailed && (
        <div className="card-dark p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-white">
              {progressPct === 100 ? 'Analysis Finalized' : 'AI Agent Processing'}
            </span>
            <span className="text-xs text-gray-400">{progressPct}%</span>
          </div>

          <div className="progress-bar">
            <div ref={progressRef} className="progress-bar-fill" />
          </div>

          {/* Event stream via synthetic CLI ink-like component */}
          <TerminalStream events={events} maxHeight="16rem" />
        </div>
      )}

      {/* Analysis results (read-only) - show even if processing the transition */}
      {hasResult && (
        <div className="space-y-3">
          <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3">
            <p className="text-sm font-medium text-green-800">Analysis Complete</p>
            <p className="text-xs text-green-600 mt-0.5">
              AI has generated a rule definition. Preparing the next step...
            </p>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">AI Analysis Summary</h4>
            <pre className="text-xs text-gray-700 whitespace-pre-wrap max-h-60 overflow-y-auto font-mono">
              {typeof analysisResult === 'string'
                ? analysisResult
                : JSON.stringify(analysisResult, null, 2)
              }
            </pre>
          </div>
        </div>
      )}

      {/* Error display */}
      {hasFailed && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <p className="text-sm font-medium text-red-800">Analysis Failed</p>
          <p className="text-xs text-red-600 mt-0.5">{error}</p>
        </div>
      )}
    </div>
  );
}
