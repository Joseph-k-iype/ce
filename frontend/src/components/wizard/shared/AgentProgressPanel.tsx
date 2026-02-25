import { useEffect, useRef, useState, useMemo } from 'react';
import type { AgentEvent } from '../../../types/agent';

interface Props {
  events: AgentEvent[];
  connected: boolean;
}

const STEP_LABELS: Record<number, string> = {
  1: 'Analyzing rule text',
  2: 'Generating data dictionary',
  3: 'Generating graph queries',
  4: 'Validating outputs',
  5: 'Running test scenarios',
  6: 'Preparing proposal',
};

const DETAIL_EVENT_TYPES = new Set([
  'ai_call_started', 'ai_call_completed', 'ai_call_retry',
  'query_execution', 'circuit_breaker_state', 'validation_detail',
  'agent_reasoning',
]);

export function AgentProgressPanel({ events, connected }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [logExpanded, setLogExpanded] = useState(false);
  const [startTime] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);

  // Tick elapsed time
  useEffect(() => {
    const isTerminal = events.some(e =>
      e.event_type === 'workflow_complete' || e.event_type === 'workflow_failed'
    );
    if (isTerminal) return;

    const interval = setInterval(() => setElapsed(Date.now() - startTime), 1000);
    return () => clearInterval(interval);
  }, [startTime, events]);

  // Latest step progress
  const latestStep = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      const e = events[i];
      if (e.step_current && e.step_total) {
        return { current: e.step_current, total: e.step_total };
      }
    }
    return null;
  }, [events]);

  // Latest non-heartbeat, non-detail event for "what's happening now"
  const latestActivity = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      const e = events[i];
      if (e.event_type !== 'heartbeat' && !DETAIL_EVENT_TYPES.has(e.event_type)) {
        return e;
      }
    }
    return null;
  }, [events]);

  // Separate main events from detail events
  const mainEvents = events.filter(e => e.event_type !== 'heartbeat' && !DETAIL_EVENT_TYPES.has(e.event_type));
  const detailEvents = events.filter(e => DETAIL_EVENT_TYPES.has(e.event_type));

  const progressPct = latestStep ? (latestStep.current / latestStep.total) * 100 : 0;
  const stepLabel = latestStep ? STEP_LABELS[latestStep.current] || '' : '';
  const isComplete = events.some(e => e.event_type === 'workflow_complete');
  const isFailed = events.some(e => e.event_type === 'workflow_failed');

  // Format elapsed time
  const formatElapsed = (ms: number) => {
    const secs = Math.floor(ms / 1000);
    const mins = Math.floor(secs / 60);
    const remainingSecs = secs % 60;
    return mins > 0 ? `${mins}m ${remainingSecs}s` : `${remainingSecs}s`;
  };

  // Auto-scroll detail log
  useEffect(() => {
    if (scrollRef.current && logExpanded) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [detailEvents.length, logExpanded]);

  return (
    <div className="bg-gray-900 rounded-lg p-4 text-sm font-mono transition-all">
      {/* Header with connection status */}
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full transition-colors ${
            isComplete ? 'bg-green-400' :
            isFailed ? 'bg-red-400' :
            connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
          }`} />
          <span className="text-gray-400 text-xs">
            {isComplete ? 'Complete' : isFailed ? 'Failed' : connected ? 'Processing' : 'Disconnected'}
          </span>
        </div>
        <span className="text-gray-500 text-xs tabular-nums">{formatElapsed(elapsed)}</span>
      </div>

      {/* Progress bar with step counter */}
      {latestStep && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-gray-300 text-xs">
              Step {latestStep.current}/{latestStep.total} — {stepLabel}
            </span>
            <span className="text-gray-500 text-xs">{Math.round(progressPct)}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${
                isComplete ? 'bg-green-500' : isFailed ? 'bg-red-500' : 'bg-purple-500'
              }`}
              style={{ width: `${isComplete ? 100 : progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* "What's happening now" section */}
      {latestActivity && !isComplete && !isFailed && (
        <div className="mb-3 px-2 py-1.5 bg-gray-800/50 rounded border border-gray-700/50">
          <div className="flex items-center gap-2">
            <span className="text-purple-400 text-xs animate-pulse">●</span>
            <span className="text-gray-300 text-xs">{latestActivity.message}</span>
          </div>
        </div>
      )}

      {/* Main event stream (always visible) */}
      <div className="space-y-0.5 mb-2">
        {mainEvents.length === 0 ? (
          <p className="text-gray-500 text-xs">Waiting for agent events...</p>
        ) : (
          mainEvents.slice(-8).map((event, i) => (
            <div key={i} className="flex gap-2 text-[10px] leading-relaxed">
              <span className="text-gray-600 shrink-0 tabular-nums">
                {new Date(event.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className={
                event.event_type.includes('failed') ? 'text-red-400' :
                event.event_type.includes('complete') ? 'text-green-400' :
                event.event_type === 'step_progress' ? 'text-yellow-400' :
                'text-purple-400 font-bold'
              }>
                [{event.agent_name || 'system'}]
              </span>
              <span className="text-gray-300">{event.message}</span>
            </div>
          ))
        )}
      </div>

      {/* Expandable detailed log */}
      {detailEvents.length > 0 && (
        <div className="border-t border-gray-800 pt-2">
          <button
            onClick={() => setLogExpanded(!logExpanded)}
            className="flex items-center gap-1 text-gray-500 text-[10px] hover:text-gray-400 transition-colors"
          >
            <span className={`transform transition-transform ${logExpanded ? 'rotate-90' : ''}`}>▶</span>
            Detailed log ({detailEvents.length} events)
          </button>
          {logExpanded && (
            <div
              ref={scrollRef}
              className="mt-1 max-h-48 overflow-y-auto scroll-smooth"
            >
              {detailEvents.map((event, i) => (
                <div key={i} className="flex gap-2 text-[10px] leading-relaxed text-gray-500">
                  <span className="shrink-0 tabular-nums">
                    {new Date(event.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                  <span className="text-gray-600">[{event.agent_name || 'system'}]</span>
                  <span>{event.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
