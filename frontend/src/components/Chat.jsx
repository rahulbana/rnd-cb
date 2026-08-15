import React, { useEffect, useRef, useState } from "react";
import { openChatSocket } from "../api";
import StepTimeline from "./StepTimeline.jsx";

// A single assistant turn accumulates step events, sources, and streamed text.
function emptyAssistant() {
  return { role: "assistant", text: "", steps: [], sources: [], status: "running" };
}

export default function Chat({ settings, disabled }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const chatRef = useRef(null);
  const activeIdx = useRef(null); // index of the assistant message being filled
  const scrollRef = useRef(null);

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
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

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
        updateActive((m) => {
          m.steps = [...m.steps, { step: event.step, status: event.status, detail: event.detail }];
          return m;
        });
        break;
      case "sources":
        updateActive((m) => {
          m.sources = event.data || [];
          return m;
        });
        break;
      case "token":
        updateActive((m) => {
          m.text += event.data || "";
          return m;
        });
        break;
      case "done":
        updateActive((m) => {
          m.status = "done";
          return m;
        });
        break;
      case "error":
        updateActive((m) => {
          m.status = "error";
          m.text += `\n\n⚠️ ${event.detail}`;
          return m;
        });
        break;
      default:
        break;
    }
  }

  function send() {
    const q = input.trim();
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

  return (
    <div className="chat">
      <div className="chat-status">
        <span className={`dot ${connected ? "on" : "off"}`} />
        {connected ? "connected" : "connecting…"}
      </div>

      <div className="messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-chat">
            Ask a question about your uploaded documents.
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="msg user">
              <div className="bubble">{m.text}</div>
            </div>
          ) : (
            <div key={i} className="msg assistant">
              <StepTimeline phase="chat" steps={m.steps} />
              {m.sources.length > 0 && <SourceChips sources={m.sources} />}
              <div className="bubble">
                {m.text || (m.status === "running" ? <em className="muted">…</em> : "")}
                {m.status === "running" && <span className="cursor">▍</span>}
              </div>
            </div>
          )
        )}
      </div>

      <div className="composer">
        <textarea
          value={input}
          placeholder={disabled ? "Index a document first…" : "Ask a question…"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          rows={2}
        />
        <button onClick={send} disabled={!connected || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}

function SourceChips({ sources }) {
  const [open, setOpen] = useState(null);
  return (
    <div className="sources">
      {sources.map((s) => (
        <div key={s.n} className="source-chip-wrap">
          <button
            className="source-chip"
            onClick={() => setOpen(open === s.n ? null : s.n)}
            title={s.source}
          >
            [{s.n}] {s.source}
            {s.page != null ? ` · p.${s.page}` : ""}
            {s.slide != null ? ` · slide ${s.slide}` : ""}
            <span className="score">{s.score}</span>
          </button>
          {open === s.n && (
            <div className="source-popover">
              <div className="scores">
                {Object.entries(s.scores || {}).map(([k, v]) => (
                  <span key={k} className="score-tag">{k}: {v}</span>
                ))}
              </div>
              <p>{s.preview}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
