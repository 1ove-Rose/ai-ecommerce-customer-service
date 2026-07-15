"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { sendChatMessage } from "@/lib/api/client";
import type { ChatMessage } from "@/lib/types/api";

type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
  intent: string;
  compliancePassed: boolean | null;
  createdAt: string;
  updatedAt: string;
};

const STORAGE_KEY = "smart-cs.chat.sessions";
const DEFAULT_USER_ID = "u_1001";

function nowIso() {
  return new Date().toISOString();
}

function createSessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `session-${crypto.randomUUID()}`;
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createNewSession(): ChatSession {
  const timestamp = nowIso();
  return {
    id: createSessionId(),
    title: "新客服会话",
    messages: [],
    intent: "等待识别",
    compliancePassed: null,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
}

function getSessionTitle(messages: ChatMessage[]) {
  const firstUserMessage = messages.find((item) => item.role === "user")?.content.trim();
  if (!firstUserMessage) return "新客服会话";
  return firstUserMessage.length > 18 ? `${firstUserMessage.slice(0, 18)}...` : firstUserMessage;
}

function formatSessionTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function loadSessions(): ChatSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatSession[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveSessions(sessions: ChatSession[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const storedSessions = loadSessions();
    if (storedSessions.length > 0) {
      const sortedSessions = [...storedSessions].sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
      );
      setSessions(sortedSessions);
      setActiveSessionId(sortedSessions[0].id);
    } else {
      const initialSession = createNewSession();
      setSessions([initialSession]);
      setActiveSessionId(initialSession.id);
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    saveSessions(sessions);
  }, [hydrated, sessions]);

  const activeSession = useMemo(
    () => sessions.find((item) => item.id === activeSessionId),
    [activeSessionId, sessions],
  );

  const messages = activeSession?.messages ?? [];
  const intent = activeSession?.intent ?? "等待识别";
  const compliancePassed = activeSession?.compliancePassed ?? null;

  function updateSession(sessionId: string, updater: (session: ChatSession) => ChatSession) {
    setSessions((items) => {
      const nextItems = items.map((item) => (item.id === sessionId ? updater(item) : item));
      return [...nextItems].sort(
        (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
      );
    });
  }

  function startNewSession() {
    const session = createNewSession();
    setSessions((items) => [session, ...items]);
    setActiveSessionId(session.id);
    setMessage("");
  }

  function deleteSession(sessionId: string) {
    setSessions((items) => {
      const nextItems = items.filter((item) => item.id !== sessionId);
      if (sessionId === activeSessionId) {
        if (nextItems.length > 0) {
          setActiveSessionId(nextItems[0].id);
        } else {
          const nextSession = createNewSession();
          setActiveSessionId(nextSession.id);
          return [nextSession];
        }
      }
      return nextItems;
    });
  }

  async function submitChat(event: FormEvent) {
    event.preventDefault();
    const content = message.trim();
    if (!content || loading) return;

    const currentSession = activeSession ?? createNewSession();
    if (!activeSession) {
      setSessions((items) => [currentSession, ...items]);
      setActiveSessionId(currentSession.id);
    }

    const timestamp = nowIso();
    const userMessage: ChatMessage = { role: "user", content, timestamp };
    const nextMessages = [...currentSession.messages, userMessage];

    updateSession(currentSession.id, (session) => ({
      ...session,
      messages: nextMessages,
      title: getSessionTitle(nextMessages),
      updatedAt: timestamp,
    }));
    setMessage("");
    setLoading(true);

    try {
      const response = await sendChatMessage({
        message: content,
        user_id: DEFAULT_USER_ID,
        session_id: currentSession.id,
      });
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.response,
        timestamp: nowIso(),
      };
      const finalMessages = [...nextMessages, assistantMessage];
      updateSession(currentSession.id, (session) => ({
        ...session,
        id: response.session_id || session.id,
        messages: finalMessages,
        title: getSessionTitle(finalMessages),
        intent: response.intent || "unknown",
        compliancePassed: response.compliance_passed,
        updatedAt: assistantMessage.timestamp ?? nowIso(),
      }));
      setActiveSessionId(response.session_id || currentSession.id);
    } catch (error) {
      const errorMessage: ChatMessage = {
        role: "assistant",
        content: error instanceof Error ? error.message : "请求失败",
        timestamp: nowIso(),
      };
      updateSession(currentSession.id, (session) => {
        const finalMessages = [...nextMessages, errorMessage];
        return {
          ...session,
          messages: finalMessages,
          title: getSessionTitle(finalMessages),
          updatedAt: errorMessage.timestamp ?? nowIso(),
        };
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chatWorkbench">
      <header className="pageHeader compactHeader">
        <div>
          <h1>客服聊天工作台</h1>
          <p>四 Agent 主链路：意图路由 → 知识检索 / 工单处理 → 合规审查。</p>
        </div>
        <div className="statusPills">
          <span className="badge">{intent}</span>
          {compliancePassed !== null && (
            <span className={compliancePassed ? "badge badgeSuccess" : "badge badgeDanger"}>
              {compliancePassed ? "合规通过" : "需人工处理"}
            </span>
          )}
        </div>
      </header>

      <div className="chatLayout">
        <section className="card chatPanel">
          <div className="messages chatMessages">
            {messages.length === 0 ? (
              <div className="emptyState">
                <strong>开始一轮客服会话</strong>
                <span>可以输入订单、物流、售后、退款、商品政策等问题。</span>
              </div>
            ) : (
              messages.map((item, index) => (
                <div key={`${item.role}-${item.timestamp ?? index}`} className={`message ${item.role}`}>
                  <div className="speaker">{item.role === "user" ? "用户" : "客服 Agent"}</div>
                  <div className="bubble">{item.content}</div>
                </div>
              ))
            )}
          </div>

          <form className="composer" onSubmit={submitChat}>
            <div className="composerRow composerRowOnly">
              <textarea
                className="textarea composerInput"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="输入用户问题，例如：帮我查一下订单 ORD-10001 的物流"
              />
              <button className="button sendButton" disabled={loading}>{loading ? "发送中..." : "发送"}</button>
            </div>
          </form>
        </section>

        <aside className="card contextPanel sessionPanel">
          <div className="cardHeader sessionPanelHeader">
            <div>
              <h2>聊天记录</h2>
              <span className="panelHint">本地保留当前浏览器会话</span>
            </div>
            <button className="button secondary compactButton" onClick={startNewSession}>新会话</button>
          </div>

          <div className="cardBody sessionList">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`sessionItem ${session.id === activeSessionId ? "active" : ""}`}
                onClick={() => setActiveSessionId(session.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setActiveSessionId(session.id);
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <span className="sessionTitle">{session.title}</span>
                <span className="sessionMeta">
                  {session.messages.length} 条消息 · {formatSessionTime(session.updatedAt)}
                </span>
                <span className="sessionFooter">
                  <span>{session.intent || "等待识别"}</span>
                  <button
                    className="deleteSession"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      deleteSession(session.id);
                    }}
                  >
                    删除
                  </button>
                </span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}