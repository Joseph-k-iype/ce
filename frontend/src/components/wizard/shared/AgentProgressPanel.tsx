import { useEffect, useRef } from 'react';
import type { AgentEvent } from '../../../types/agent';

interface Props {
  events: AgentEvent[];
  connected: boolean;
}

export function AgentProgressPanel({ events, connected }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const filtered = events.filter(e => e.event_type !== 'heartbeat');

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filtered.length]);

  return (
    <div 
      ref={scrollRef}
      className="bg-gray-900 rounded-lg p-4 text-sm font-mono max-h-64 overflow-y-auto transition-all scroll-smooth"
    >
      <div className="flex items-center gap-2 mb-3 sticky top-0 bg-gray-900 pb-2 border-b border-gray-800">
        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-gray-400 text-xs">Agent Progress</span>
      </div>
      {filtered.length === 0 ? (
        <p className="text-gray-500 text-xs">Waiting for agent events...</p>
      ) : (
        filtered.map((event, i) => (
          <div key={i} className="flex gap-2 text-[10px] mb-1 leading-relaxed">
            <span className="text-gray-600 shrink-0 tabular-nums">
              {new Date(event.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            <span className={
              event.event_type.includes('failed') ? 'text-red-400' :
              event.event_type.includes('complete') ? 'text-green-400' :
              'text-blue-400 font-bold'
            }>
              [{event.agent_name || 'system'}]
            </span>
            <span className="text-gray-300">{event.message}</span>
          </div>
        ))
      )}
    </div>
  );
}
