export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
};

export type ChatResponse = {
  response: string;
  session_id: string;
  intent: string;
  compliance_passed: boolean;
};

export type ToolCallResult<T = unknown> = {
  success: boolean;
  result: T;
  error?: string | null;
  duration_ms?: number;
};

export type ToolLog = {
  tool: string;
  success: boolean;
  duration_ms: number;
  timestamp: string;
  error?: string | null;
};

export type MetricsResponse = {
  agent_metrics: Record<string, unknown>;
  tool_call_log: ToolLog[];
};