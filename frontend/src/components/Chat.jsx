import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { openChatSocket, ingestFile } from "../api";
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

// File-type badge shown on each attachment chip.
function fileKind(name) {
  const ext = (name.split(".").pop() || "").toLowerCase();
  const map = {
    pdf: ["PDF", "#e5484d"],
    doc: ["DOC", "#2563eb"], docx: ["DOC", "#2563eb"],
    xls: ["XLS", "#16a34a"], xlsx: ["XLS", "#16a34a"], xlsm: ["XLS", "#16a34a"],
    csv: ["CSV", "#16a34a"], tsv: ["CSV", "#16a34a"],
    ppt: ["PPT", "#d97706"], pptx: ["PPT", "#d97706"],
    png: ["IMG", "#7c3aed"], jpg: ["IMG", "#7c3aed"], jpeg: ["IMG", "#7c3aed"],
    webp: ["IMG", "#7c3aed"], tiff: ["IMG", "#7c3aed"], bmp: ["IMG", "#7c3aed"],
    txt: ["TXT", "#6b7280"], md: ["TXT", "#6b7280"], log: ["TXT", "#6b7280"],
  };
  return map[ext] || ["FILE", "#6b7280"];
}

export default function Chat({ settings, disabled, onIngested }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const chatRef = useRef(null);
  const activeIdx = useRef(null);
  const scrollRef = useRef(null);
  const taRef = useRef(null);
  const fileRef = useRef(null);

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

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [input]);

  // ---- chat streaming ----
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

  // ---- uploads (ChatGPT-style, in the composer) ----
  function handleFiles(fileList) {
    for (const file of Array.from(fileList)) {
      const id = (crypto.randomUUID && crypto.randomUUID()) || String(Math.random());
      setAttachments((a) => [...a, { id, name: file.name, status: "uploading", steps: [] }]);
      const onEvent = (event) => {
        if (event.type === "step") {
          setAttachments((a) =>
            a.map((x) => (x.id === id ? { ...x, steps: [...x.steps, event] } : x))
          );
        }
      };
      ingestFile(file, onEvent)
        .then(() => {
          setAttachments((a) => a.map((x) => (x.id === id ? { ...x, status: "ready" } : x)));
          onIngested && onIngested();
        })
        .catch((err) => {
          setAttachments((a) =>
            a.map((x) => (x.id === id ? { ...x, status: "error", error: err.message } : x))
          );
        });
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files);
  }

  const empty = messages.length === 0;

  return (
    <div
      className="chat"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={(e) => { if (e.currentTarget === e.target) setDragOver(false); }}
      onDrop={onDrop}
    >
      {dragOver && (
        <div className="drop-overlay">
          <div className="drop-card">⬇ Drop files to add them to the chat</div>
        </div>
      )}

      <div className="thread" ref={scrollRef}>
        {empty ? (
          <div className="welcome">
            <div className="welcome-logo">✦</div>
            <h1>What would you like to know?</h1>
            <p className="welcome-sub">
              {disabled
                ? "Attach a document below (or drop one here), then ask anything about it."
                : "Ask a question about your documents — or attach more below."}
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
          {attachments.length > 0 && (
            <div className="composer-attachments">
              {attachments.map((att) => (
                <AttachmentChip
                  key={att.id}
                  att={att}
                  onRemove={() => setAttachments((a) => a.filter((x) => x.id !== att.id))}
                />
              ))}
            </div>
          )}
          <div className="composer-row">
            <input
              ref={fileRef}
              type="file"
              multiple
              hidden
              accept=".txt,.md,.log,.csv,.tsv,.pdf,.doc,.docx,.xls,.xlsx,.xlsm,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
              onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }}
            />
            <button
              className="attach-btn"
              onClick={() => fileRef.current?.click()}
              title="Attach documents"
              aria-label="Attach documents"
            >
              +
            </button>
            <textarea
              ref={taRef}
              value={input}
              rows={1}
              placeholder={disabled ? "Attach a document to get started…" : "Message your documents…"}
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

function AttachmentChip({ att, onRemove }) {
  const [label, color] = fileKind(att.name);
  const labels = STEP_LABELS.ingest;
  const last = att.steps[att.steps.length - 1];
  let status = "Uploading…";
  if (att.status === "ready") status = "Ready";
  else if (att.status === "error") status = att.error || "Failed";
  else if (last) status = `${labels[last.step] || last.step}…`;

  return (
    <div className={`attachment ${att.status}`}>
      <div className="attachment-icon" style={{ background: color }}>
        {att.status === "uploading" ? <span className="spinner light" /> : label}
      </div>
      <div className="attachment-meta">
        <div className="attachment-name" title={att.name}>{att.name}</div>
        <div className="attachment-status">
          {att.status === "ready" && "✓ "}
          {status}
        </div>
      </div>
      <button className="attachment-x" onClick={onRemove} aria-label="Remove">×</button>
    </div>
  );
}

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
