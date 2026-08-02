import { useCallback, useEffect, useRef, useState } from "react";
import { Composer } from "./components/Composer";
import { MessageBubble } from "./components/MessageBubble";
import { fetchHealth, streamChat, type HealthInfo } from "./lib/chatClient";
import type { ChatMessage, ToolActivity } from "./lib/types";

const WELCOME: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "👋 Hi, I'm **Reel**, your movie concierge. Ask me about films, actors, or " +
    "what's trending. I can also translate text and tell you the time around the world.\n\n" +
    "Try: _\"What are the top rated sci-fi movies from 2019?\"_ or " +
    "_\"What time is it in Tokyo and how does that compare to New York?\"_",
};

const uid = () => Math.random().toString(36).slice(2);

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      if (isStreaming) return;

      const userMessage: ChatMessage = { id: uid(), role: "user", content: text };
      const assistantId = uid();
      const history = messages
        .filter((m) => m.id !== "welcome")
        .map(({ role, content }) => ({ role, content }));

      setMessages((prev) => [
        ...prev,
        userMessage,
        { id: assistantId, role: "assistant", content: "", streaming: true, tools: [] },
      ]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      const patch = (fn: (m: ChatMessage) => ChatMessage) =>
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? fn(m) : m)));

      try {
        for await (const event of streamChat([...history, { role: "user", content: text }], controller.signal)) {
          switch (event.type) {
            case "token":
              patch((m) => ({ ...m, content: m.content + event.content }));
              break;
            case "tool_call":
              patch((m) => ({
                ...m,
                tools: upsertTool(m.tools, { name: event.name, args: event.args, status: "running" }),
              }));
              break;
            case "tool_result":
              patch((m) => ({
                ...m,
                tools: markToolDone(m.tools, event.name, event.status === "error" ? "error" : "success"),
              }));
              break;
            case "error":
              patch((m) => ({
                ...m,
                content: m.content || `⚠️ ${event.message}`,
                streaming: false,
              }));
              break;
          }
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Something went wrong.";
        if (message !== "The user aborted a request.") {
          patch((m) => ({ ...m, content: m.content || `⚠️ ${message}`, streaming: false }));
        }
      } finally {
        patch((m) => ({ ...m, streaming: false }));
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, messages]
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">🎬</span>
          <div>
            <h1>Reel</h1>
            <p>Movie concierge · powered by OpenAI, LangGraph & a remote MCP server</p>
          </div>
        </div>
        <StatusPill health={health} />
      </header>

      <main className="chat" ref={scrollRef}>
        <div className="messages">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
        </div>
      </main>

      <Composer onSend={send} onStop={stop} isStreaming={isStreaming} />
    </div>
  );
}

function StatusPill({ health }: { health: HealthInfo | null }) {
  if (!health) return <span className="pill pill--unknown">connecting…</span>;
  const ok = health.status === "ok";
  return (
    <span
      className={`pill ${ok ? "pill--ok" : "pill--down"}`}
      title={`${health.tools.length} tools · MCP: ${health.mcp_server}`}
    >
      {ok ? `${health.model} · ${health.tools.length} tools` : "backend degraded"}
    </span>
  );
}

function upsertTool(tools: ToolActivity[] = [], tool: ToolActivity): ToolActivity[] {
  const existing = tools.find((t) => t.name === tool.name && t.status === "running");
  if (existing) return tools;
  return [...tools, tool];
}

function markToolDone(tools: ToolActivity[] = [], name: string, status: ToolActivity["status"]): ToolActivity[] {
  let patched = false;
  const next = tools.map((t) => {
    if (!patched && t.name === name && t.status === "running") {
      patched = true;
      return { ...t, status };
    }
    return t;
  });
  return next;
}
