import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { openChatSocket } from "../api";
import { STEP_LABELS } from "./StepTimeline.jsx";

function emptyAssistant() {
  return { role: "assistant", text: "", steps: [], sources: [], status: "running" };
}

const SUGGESTIONS = [
  "Summarize the key points across my documents",
  "What are the main figures or totals mentioned?",
  "List any dates, deadlines, or amounts",
  "Explain this document in simple terms",
];

export default function Chat({ settings, disabled }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const chatRef = useRef(null);
  const activeIdx = useRef(null);
  const scrollRef = useRef(null);
  const taRef = useRef(null);

  useEffect(() => {
    const chat = openChatSocket({
      onOpen: () => setConnected(true),
      onClose: () => setConnected(false),
      onEvent: handleEvent,
    });
    chatRef.current = chat;
    return () => chat.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Auto-grow the composer textarea.
  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [input]);

  function updateActive(mutator) {
    setMessages((prev) => {
      const idx = activeIdx.current;
      if (idx == null || !prev[idx]) return prev;
      const next = prev.slice();
      next[idx] = mutator({ ...next[idx] });
      return next;
    });
  }

  function handleEvent(event) {
    switch (event.type) {
      case "step":
        updateActive((m) => ({
          ...m,
          steps: [...m.steps, { step: event.step, status: event.status, detail: event.detail }],
        }));
        break;
      case "sources":
        updateActive((m) => ({ ...m, sources: event.data || [] }));
        break;
      case "token":
        updateActive((m) => ({ ...m, text: m.text + (event.data || "") }));
        break;
      case "done":
        updateActive((m) => ({ ...m, status: "done" }));
        break;
      case "error":
        updateActive((m) => ({ ...m, status: "error", text: m.text + `\n\n⚠️ ${event.detail}` }));
        break;
      default:
        break;
    }
  }

  function send(text) {
    const q = (text ?? input).trim();
    if (!q || !chatRef.current?.ready) return;
    setMessages((prev) => {
      const next = [...prev, { role: "user", text: q }, emptyAssistant()];
      activeIdx.current = next.length - 1;
      return next;
    });
    chatRef.current.ask(q, {
      retrieval_strategy: settings.retrieval_strategy,
      rerank_enabled: settings.rerank_enabled,
      llm_provider: settings.llm_provider,
      top_k: settings.top_k,
      final_top_k: settings.final_top_k,
    });
    setInput("");
  }

  const empty = messages.length === 0;

  return (
    <div className="chat">
      <div className="thread" ref={scrollRef}>
        {empty ? (
          <div className="welcome">
            <div className="welcome-logo">✦</div>
            <h1>What would you like to know?</h1>
            <p className="welcome-sub">
              {disabled
                ? "Add a document from the sidebar, then ask anything about it."
                : "Ask a question about your uploaded documents."}
            </p>
            {!disabled && (
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="turns">
            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="turn user">
                  <div className="user-bubble">{m.text}</div>
                </div>
              ) : (
                <div key={i} className="turn assistant">
                  <div className="avatar">✦</div>
                  <div className="assistant-content">
                    <StepTrace steps={m.steps} status={m.status} />
                    {m.sources.length > 0 && <Citations sources={m.sources} />}
                    <div className="markdown">
                      {m.text ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                      ) : m.status === "running" ? (
                        <span className="thinking-dots"><span /><span /><span /></span>
                      ) : null}
                      {m.status === "running" && m.text && <span className="cursor">▍</span>}
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        )}
      </div>

      <div className="composer-wrap">
        <div className="composer">
          <textarea
            ref={taRef}
            value={input}
            rows={1}
            placeholder={disabled ? "Add a document to get started…" : "Message your documents…"}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <button
            className="send-btn"
            onClick={() => send()}
            disabled={!connected || !input.trim()}
            aria-label="Send"
          >
            ↑
          </button>
        </div>
        <div className="composer-foot">
          <span className={`conn ${connected ? "on" : "off"}`}>
            {connected ? "connected" : "connecting…"}
          </span>
          <span>·</span>
          <span>{settings.retrieval_strategy} retrieval</span>
          {settings.rerank_enabled && <><span>·</span><span>rerank on</span></>}
          <span>·</span>
          <span>{settings.llm_provider}</span>
        </div>
      </div>
    </div>
  );
}

// Collapsible ChatGPT-style "working…" trace summarizing the pipeline steps.
function StepTrace({ steps, status }) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0 && status !== "running") return null;

  const labels = STEP_LABELS.chat;
  const active = [...steps].reverse().find((s) => s.status === "start");
  const running = status === "running";
  const summary = running
    ? (active ? `${labels[active.step] || active.step}…` : "Working…")
    : "Thought process";

  return (
    <div className={`trace ${running ? "running" : ""}`}>
      <button className="trace-head" onClick={() => setOpen((o) => !o)}>
        {running && <span className="spinner" />}
        <span className="trace-summary">{summary}</span>
        <span className="trace-caret">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <ol className="trace-steps">
          {steps.map((s, i) => (
            <li key={i} className={s.status}>
              <span className="trace-dot" />
              <span className="trace-label">{labels[s.step] || s.step}</span>
              {s.detail && <span className="trace-detail">{s.detail}</span>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Citations({ sources }) {
  const [open, setOpen] = useState(null);
  return (
    <div className="citations">
      {sources.map((s) => (
        <span key={s.n} className="cite-wrap">
          <button
            className="cite"
            onMouseEnter={() => setOpen(s.n)}
            onMouseLeave={() => setOpen(null)}
            onClick={() => setOpen(open === s.n ? null : s.n)}
          >
            <span className="cite-n">{s.n}</span>
            <span className="cite-src">{s.source}</span>
          </button>
          {open === s.n && (
            <span className="cite-pop">
              <span className="cite-meta">
                {s.source}
                {s.page != null ? ` · p.${s.page}` : ""}
                {s.slide != null ? ` · slide ${s.slide}` : ""}
                {` · score ${s.score}`}
              </span>
              <span className="cite-text">{s.preview}</span>
            </span>
          )}
        </span>
      ))}
    </div>
  );
}
