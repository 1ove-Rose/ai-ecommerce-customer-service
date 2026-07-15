import type { ChatMessage, ChatResponse, MetricsResponse, ToolCallResult } from "@/lib/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function sendChatMessage(input: {
  message: string;
  user_id: string;
  session_id?: string;
}) {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getHistory(sessionId: string) {
  return request<{ session_id: string; messages: ChatMessage[] }>(`/api/history/${sessionId}`);
}

export function callTool<T = unknown>(name: string, args: Record<string, unknown>) {
  return request<ToolCallResult<T>>("/api/tools/call", {
    method: "POST",
    body: JSON.stringify({ name, arguments: args }),
  });
}

export function listTools() {
  return request<{ tools: Array<{ name: string; description: string; category: string }> }>("/api/tools");
}

export function getMetrics() {
  return request<MetricsResponse>("/api/metrics");
}

export function getHealth() {
  return request<{ status: string; version: string }>("/health");
}