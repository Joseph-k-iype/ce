export interface AgentEvent {
  event_type: string;
  session_id: string;
  agent_name: string;
  phase: string;
  message: string;
  data?: Record<string, unknown>;
  progress_pct?: number;
  timestamp: string;
}
