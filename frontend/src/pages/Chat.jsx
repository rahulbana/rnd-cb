import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext.jsx";

export default function Chat() {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [memories, setMemories] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showMemories, setShowMemories] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    refreshSessions();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function refreshSessions() {
    const data = await api.listSessions();
    setSessions(data);
  }

  async function refreshMemories() {
    const data = await api.listMemories();
    setMemories(data);
  }

  async function openSession(id) {
    setActiveId(id);
    const detail = await api.getSession(id);
    setMessages(detail.messages);
  }

  function newChat() {
    setActiveId(null);
    setMessages([]);
  }

  async function removeSession(id, e) {
    e.stopPropagation();
    if (!confirm("Delete this chat?")) return;
    await api.deleteSession(id);
    if (id === activeId) newChat();
    refreshSessions();
  }

  async function send(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setInput("");
    setMessages((m) => [...m, { role: "user", content: text, id: `tmp-${Date.now()}` }]);
    setSending(true);

    try {
      const res = await api.sendChat(text, activeId);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.reply, id: `a-${Date.now()}` },
      ]);
      if (!activeId) {
        setActiveId(res.session_id);
      }
      refreshSessions();
      if (showMemories) refreshMemories();
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `⚠️ ${err.message}`, id: `e-${Date.now()}`, error: true },
      ]);
    } finally {
      setSending(false);
    }
  }

  function toggleMemories() {
    const next = !showMemories;
    setShowMemories(next);
    if (next) refreshMemories();
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <button className="new-chat" onClick={newChat}>
          + New chat
        </button>
        <div className="sessions">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`session ${s.id === activeId ? "active" : ""}`}
              onClick={() => openSession(s.id)}
            >
              <span className="session-title">{s.title || "New chat"}</span>
              <button
                className="del"
                title="Delete"
                onClick={(e) => removeSession(s.id, e)}
              >
                ×
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <p className="muted empty">No chats yet</p>
          )}
        </div>
        <div className="sidebar-footer">
          <div className="user-row">
            <span className="avatar">{user?.username?.[0]?.toUpperCase()}</span>
            <span className="uname">{user?.username}</span>
          </div>
          <button className="link-btn" onClick={toggleMemories}>
            {showMemories ? "Hide memory" : "Long-term memory"}
          </button>
          <button className="link-btn" onClick={logout}>
            Log out
          </button>
        </div>
      </aside>

      <main className="chat">
        <header className="chat-header">
          <h2>Memory Chatbot</h2>
          <span className="badge">short-term + long-term memory</span>
        </header>

        <div className="messages">
          {messages.length === 0 && (
            <div className="welcome">
              <h3>Hi {user?.username} 👋</h3>
              <p className="muted">
                Start a conversation. I remember our chat (short-term) and
                durable facts about you across sessions (long-term).
              </p>
            </div>
          )}
          {messages.map((m) => (
            <div key={m.id} className={`msg ${m.role} ${m.error ? "err" : ""}`}>
              <div className="bubble">{m.content}</div>
            </div>
          ))}
          {sending && (
            <div className="msg assistant">
              <div className="bubble typing">…</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <form className="composer" onSubmit={send}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message…"
            disabled={sending}
          />
          <button type="submit" disabled={sending || !input.trim()}>
            Send
          </button>
        </form>
      </main>

      {showMemories && (
        <aside className="memory-panel">
          <h3>Long-term memory</h3>
          <p className="muted">Facts remembered about you</p>
          {memories.length === 0 && <p className="muted">Nothing yet.</p>}
          <ul>
            {memories.map((m) => (
              <li key={m.id}>{m.content}</li>
            ))}
          </ul>
        </aside>
      )}
    </div>
  );
}
