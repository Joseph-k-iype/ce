import { useEffect, useState, useCallback, useRef } from 'react';
import type { AgentEvent } from '../types/agent';

const MAX_EVENTS = 200;
const TERMINAL_EVENTS = new Set(['workflow_complete', 'workflow_failed']);
const MAX_RECONNECT_ATTEMPTS = 5;
const BASE_RECONNECT_DELAY_MS = 1000;

export function useAgentEvents(sessionId: string | null) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const terminalRef = useRef(false);

  const connect = useCallback(() => {
    if (!sessionId) return;

    // Close any existing connection
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    terminalRef.current = false;

    const source = new EventSource(`/api/agent-events/stream/${sessionId}`);
    sourceRef.current = source;

    source.onopen = () => {
      setConnected(true);
      reconnectAttemptRef.current = 0; // Reset on successful connect
    };

    source.onerror = () => {
      setConnected(false);
      source.close();
      sourceRef.current = null;

      // Auto-reconnect with exponential backoff (unless terminal event received)
      if (!terminalRef.current && reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = BASE_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttemptRef.current);
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };

    const handler = (e: MessageEvent) => {
      try {
        const event: AgentEvent = JSON.parse(e.data);
        setEvents(prev => {
          const next = [...prev, event];
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
        });

        // Close connection on terminal events
        if (TERMINAL_EVENTS.has(event.event_type)) {
          terminalRef.current = true;
          source.close();
          sourceRef.current = null;
          setConnected(false);
        }
      } catch {
        // ignore parse errors
      }
    };

    // Listen to all event types
    const eventTypes = [
      'agent_started', 'agent_completed', 'agent_failed',
      'phase_changed', 'analysis_progress', 'dictionary_progress',
      'validation_progress', 'cypher_progress', 'human_review_required',
      'workflow_complete', 'workflow_failed', 'heartbeat',
    ];

    eventTypes.forEach(type => source.addEventListener(type, handler));

    return () => {
      terminalRef.current = true; // Prevent reconnect on intentional cleanup
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      source.close();
      sourceRef.current = null;
      setConnected(false);
    };
  }, [sessionId]);

  useEffect(() => {
    reconnectAttemptRef.current = 0;
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}
