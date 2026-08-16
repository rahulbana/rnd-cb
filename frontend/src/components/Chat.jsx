import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { openChatSocket, ingestFile } from "../api";
import { STEP_LABELS } from "./StepTimeline.jsx";

const MAX_UPLOAD_MB = 50;
const SUPPORTED = [
  "txt", "md", "log", "csv", "tsv", "pdf", "doc", "docx", "xls", "xlsx",
  "xlsm", "ppt", "pptx", "png", "jpg", "jpeg", "webp", "tiff", "bmp",
];

function emptyAssistant() {
  return { role: "assistant", text: "", steps: [], sources: [], status: "running" };
}

const SUGGESTIONS = [
  "Summarize the key points across my documents",
  "What are the main figures or totals mentioned?",
  "List any dates, deadlines, or amounts",
  "Explain this document in simple terms",
];

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

function humanSize(bytes) {
  if (!bytes) return "";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0, n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
}

export default function Chat({ settings, disabled, onIngested, initialMessages, onPersist, traceDefaultOpen = true }) {
  const [messages, setMessages] = useState(() => initialMessages || []);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [atBottom, setAtBottom] = useState(true);
  const chatRef = useRef(null);
  const activeIdx = useRef(null);
  const lastQuery = useRef(null);
  const scrollRef = useRef(null);
  const taRef = useRef(null);
  const fileRef = useRef(null);
  const persistRef = useRef(onPersist);
  persistRef.current = onPersist;

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

  // Persist conversation to history after each turn settles. Skipping the
  // initial mount avoids re-saving on open; skipping the running state avoids
  // storing half-streamed turns and needless writes.
  const firstPersist = useRef(true);
  useEffect(() => {
    if (firstPersist.current) { firstPersist.current = false; return; }
    const last = messages[messages.length - 1];
    if (last && last.status === "running") return;
    const t = setTimeout(() => persistRef.current && persistRef.current(messages), 400);
    return () => clearTimeout(t);
  }, [messages]);

  useEffect(() => {
    if (atBottom) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages, atBottom]);

  useEffect(() => {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  }, [input]);

  function onScroll() {
    const el = scrollRef.current;
    if (!el) return;
    setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 120);
  }

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
          steps: [...m.steps, { step: event.step, status: event.status, detail: event.detail, t: Date.now() }],
        }));
        break;
      case "sources":
        updateActive((m) => ({ ...m, sources: event.data || [] }));
        break;
      case "token":
        // Ignore tokens after a manual Stop.
        updateActive((m) => (m.status !== "running" ? m : { ...m, text: m.text + (event.data || "") }));
        break;
      case "done":
        updateActive((m) => (m.status === "stopped" ? m : { ...m, status: "done" }));
        break;
      case "error":
        updateActive((m) => ({ ...m, status: "error", text: m.text + `\n\n⚠️ ${event.detail}` }));
        break;
      default:
        break;
    }
  }

  function ask(q, replaceIdx = null) {
    if (!chatRef.current?.ready) return;
    lastQuery.current = q;
    setMessages((prev) => {
      let next;
      if (replaceIdx != null) {
        next = prev.slice();
        next[replaceIdx] = emptyAssistant();
        activeIdx.current = replaceIdx;
      } else {
        next = [...prev, { role: "user", text: q }, emptyAssistant()];
        activeIdx.current = next.length - 1;
      }
      return next;
    });
    setAtBottom(true);
    chatRef.current.ask(q, {
      retrieval_strategy: settings.retrieval_strategy,
      rerank_enabled: settings.rerank_enabled,
      llm_provider: settings.llm_provider,
      top_k: settings.top_k,
      final_top_k: settings.final_top_k,
    });
  }

  function send(text) {
    const q = (text ?? input).trim();
    if (!q) return;
    ask(q);
    setInput("");
  }

  function regenerate() {
    const idx = messages.length - 1;
    if (messages[idx]?.role !== "assistant") return;
    // Fall back to the last user turn (e.g. after reloading a saved chat where
    // the in-memory lastQuery ref was reset).
    const q = lastQuery.current || [...messages].reverse().find((m) => m.role === "user")?.text;
    if (!q) return;
    ask(q, idx);
  }

  function stop() {
    updateActive((m) => ({ ...m, status: "stopped" }));
  }

  // ---- uploads ----
  function handleFiles(fileList) {
    for (const file of Array.from(fileList)) {
      const id = (crypto.randomUUID && crypto.randomUUID()) || String(Math.random());
      const ext = (file.name.split(".").pop() || "").toLowerCase();
      const base = { id, name: file.name, size: file.size, file, steps: [] };

      if (!SUPPORTED.includes(ext)) {
        setAttachments((a) => [...a, { ...base, status: "error", error: `Unsupported .${ext}` }]);
        continue;
      }
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        setAttachments((a) => [...a, {
          ...base, status: "error", error: `Too large (max ${MAX_UPLOAD_MB} MB)`,
        }]);
        continue;
      }
      setAttachments((a) => [...a, { ...base, status: "uploading" }]);
      startIngest(id, file);
    }
  }

  function startIngest(id, file) {
    setAttachments((a) => a.map((x) => (x.id === id ? { ...x, status: "uploading", steps: [] } : x)));
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

  function onDrop(e) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files);
  }

  const empty = messages.length === 0;
  const streaming = messages[messages.length - 1]?.status === "running";

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

      <div className="thread" ref={scrollRef} onScroll={onScroll}>
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
                    <StepTrace steps={m.steps} status={m.status} defaultOpen={traceDefaultOpen} />
                    {m.sources.length > 0 && <Citations sources={m.sources} />}
                    <div className="markdown">
                      {m.text ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD}>
                          {m.text}
                        </ReactMarkdown>
                      ) : m.status === "running" ? (
                        <span className="thinking-dots"><span /><span /><span /></span>
                      ) : null}
                      {m.status === "running" && m.text && <span className="cursor">▍</span>}
                    </div>
                    {m.status !== "running" && m.text && (
                      <MessageActions
                        text={m.text}
                        canRegenerate={i === messages.length - 1}
                        onRegenerate={regenerate}
                      />
                    )}
                  </div>
                </div>
              )
            )}
          </div>
        )}
      </div>

      {!atBottom && !empty && (
        <button
          className="scroll-bottom"
          onClick={() => { setAtBottom(true); scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }); }}
          aria-label="Scroll to bottom"
        >
          ↓
        </button>
      )}

      <div className="composer-wrap">
        <div className="composer">
          {attachments.length > 0 && (
            <div className="composer-attachments">
              {attachments.map((att) => (
                <AttachmentChip
                  key={att.id}
                  att={att}
                  onRemove={() => setAttachments((a) => a.filter((x) => x.id !== att.id))}
                  onRetry={() => att.file && startIngest(att.id, att.file)}
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
              accept={SUPPORTED.map((e) => "." + e).join(",")}
              onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }}
            />
            <button className="attach-btn" onClick={() => fileRef.current?.click()} title="Attach documents" aria-label="Attach documents">
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
            {streaming ? (
              <button className="send-btn stop" onClick={stop} aria-label="Stop" title="Stop">■</button>
            ) : (
              <button className="send-btn" onClick={() => send()} disabled={!connected || !input.trim()} aria-label="Send">↑</button>
            )}
          </div>
        </div>
        <div className="composer-foot">
          <span className={`conn ${connected ? "on" : "off"}`}>{connected ? "connected" : "connecting…"}</span>
          <span>·</span><span>{settings.retrieval_strategy} retrieval</span>
          {settings.rerank_enabled && <><span>·</span><span>rerank on</span></>}
          <span>·</span><span>{settings.llm_provider}</span>
        </div>
      </div>
    </div>
  );
}

// ---- code block with language label + copy ----
function CodeBlock({ className, children }) {
  const raw = String(children ?? "");
  const isBlock = /language-/.test(className || "") || raw.includes("\n");
  if (!isBlock) return <code className={className}>{children}</code>;
  const lang = (/language-(\w+)/.exec(className || "") || [])[1] || "code";
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard?.writeText(raw.replace(/\n$/, ""));
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };
  return (
    <div className="code-wrap">
      <div className="code-head">
        <span className="code-lang">{lang}</span>
        <button className="code-copy" onClick={copy}>{copied ? "Copied!" : "Copy"}</button>
      </div>
      <pre><code className={className}>{children}</code></pre>
    </div>
  );
}
const MD = { code: CodeBlock };

function MessageActions({ text, canRegenerate, onRegenerate }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="msg-actions">
      <button
        className="action-btn"
        onClick={() => { navigator.clipboard?.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
        title="Copy"
      >
        {copied ? "✓ Copied" : "⧉ Copy"}
      </button>
      {canRegenerate && (
        <button className="action-btn" onClick={onRegenerate} title="Regenerate">↻ Regenerate</button>
      )}
    </div>
  );
}

function AttachmentChip({ att, onRemove, onRetry }) {
  const [label, color] = fileKind(att.name);
  const labels = STEP_LABELS.ingest;
  const done = att.steps.filter((s) => s.status === "done").map((s) => s.step);
  const doneCount = new Set(done).size;
  const pct = att.status === "ready" ? 100 : Math.min(95, Math.round((doneCount / 6) * 100));
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
          {att.size ? <span className="attachment-size"> · {humanSize(att.size)}</span> : null}
        </div>
        {att.status === "uploading" && (
          <div className="attachment-bar"><div style={{ width: `${pct}%` }} /></div>
        )}
      </div>
      {att.status === "error" && att.file && (
        <button className="attachment-retry" onClick={onRetry} title="Retry">↻</button>
      )}
      <button className="attachment-x" onClick={onRemove} aria-label="Remove">×</button>
    </div>
  );
}

const STEP_ICON = {
  done: "✓",
  start: null,      // rendered as a spinner
  progress: null,
  error: "✕",
};

function StepTrace({ steps, status, defaultOpen = true }) {
  // Visible per the global preference by default; the user can toggle per message.
  const [open, setOpen] = useState(defaultOpen);
  if (steps.length === 0 && status !== "running") return null;

  const labels = STEP_LABELS.chat;
  const order = Object.keys(labels).filter((k) => k !== "complete");
  const running = status === "running";

  // Collapse the start/done event stream into one row per step (last wins),
  // and derive each step's duration from its start→done timestamps.
  const byStep = {};
  const startT = {};
  for (const s of steps) {
    byStep[s.step] = s;
    if (s.status === "start" && startT[s.step] == null) startT[s.step] = s.t;
  }
  const rows = order.filter((k) => byStep[k]).map((k) => {
    const s = byStep[k];
    const ms = s.status === "done" && startT[k] != null && s.t != null ? s.t - startT[k] : null;
    return { key: k, ...s, ms };
  });

  const active = [...steps].reverse().find((s) => s.status === "start");
  const headline = running
    ? (active ? `${labels[active.step] || active.step}…` : "Thinking…")
    : "Thought process";

  return (
    <div className={`trace ${running ? "running" : ""}`}>
      <div className="trace-head">
        <span className="trace-headline">
          {running ? <span className="spinner" /> : <span className="trace-spark">✦</span>}
          {headline}
        </span>
        <button className="trace-toggle" onClick={() => setOpen((o) => !o)}>
          {open ? "Hide" : "Show"}
        </button>
      </div>
      {open && (
        <ol className="trace-steps">
          {rows.map((s) => (
            <li key={s.key} className={s.status}>
              <span className="trace-icon">
                {s.status === "start" || s.status === "progress"
                  ? <span className="spinner sm" />
                  : (STEP_ICON[s.status] || "•")}
              </span>
              <div className="trace-body">
                <span className="trace-label">
                  {labels[s.key] || s.key}
                  {s.ms != null && <span className="trace-time">{(s.ms / 1000).toFixed(1)}s</span>}
                </span>
                {s.detail && <span className="trace-detail">{s.detail}</span>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function Citations({ sources }) {
  const [show, setShow] = useState(false); // collapsed by default
  const [open, setOpen] = useState(null);
  return (
    <div className="citations-block">
      <button className="citations-toggle" onClick={() => setShow((s) => !s)}>
        <span className="cite-badge">{sources.length}</span>
        {sources.length === 1 ? "source" : "sources"}
        <span className="citations-caret">{show ? "▾" : "▸"}</span>
      </button>
      {show && (
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
      )}
    </div>
  );
}
