import type { AgentEvent } from '../../../types/agent';

interface Props {
  events: AgentEvent[];
  connected: boolean;
}

export function AgentProgressPanel({ events, connected }: Props) {
  const filtered = events.filter(e => e.event_type !== 'heartbeat');

  return (
    <div className="bg-gray-900 rounded-lg p-4 text-sm font-mono max-h-64 overflow-y-auto">
      <div className="flex items-center gap-2 mb-3">
        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
        <span className="text-gray-400 text-xs">Agent Progress</span>
      </div>
      {filtered.length === 0 ? (
        <p className="text-gray-500 text-xs">Waiting for agent events...</p>
      ) : (
        filtered.map((event, i) => (
          <div key={i} className="flex gap-2 text-xs mb-1">
            <span className="text-gray-500 shrink-0">
              {new Date(event.timestamp).toLocaleTimeString()}
            </span>
            <span className={
              event.event_type.includes('failed') ? 'text-red-400' :
              event.event_type.includes('complete') ? 'text-green-400' :
              'text-blue-400'
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
