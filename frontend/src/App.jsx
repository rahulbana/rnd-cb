import React, { useCallback, useEffect, useRef, useState } from "react";
import { getConfig, listSources } from "./api";
import {
  newConversation, titleFrom, sanitizeMessages,
  apiListConversations, apiGetConversation, apiUpsertConversation,
  apiRenameConversation, apiDeleteConversation,
} from "./history";
import Settings from "./components/Settings.jsx";
import Sources from "./components/Sources.jsx";
import History from "./components/History.jsx";
import Chat from "./components/Chat.jsx";

export default function App() {
  const [config, setConfig] = useState(null);
  const [settings, setSettings] = useState(null);
  const [sources, setSources] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

  const [conversations, setConversations] = useState([]); // summaries
  const [activeId, setActiveId] = useState(null);
  const [activeMessages, setActiveMessages] = useState(null); // null = loading
  const convsRef = useRef([]);
  convsRef.current = conversations;

  const refreshSources = useCallback(async () => {
    try {
      const data = await listSources();
      setSources(data.sources || []);
      setTotalChunks(data.total_chunks || 0);
    } catch {
      /* backend may still be starting */
    }
  }, []);

  // Config + sources.
  useEffect(() => {
    getConfig()
      .then((cfg) => {
        setConfig(cfg);
        const d = cfg.defaults;
        setSettings({
          retrieval_strategy: d.retrieval_strategy,
          rerank_enabled: d.rerank_enabled,
          llm_provider: d.llm_provider,
          top_k: d.top_k,
          final_top_k: d.final_top_k,
        });
      })
      .catch(() => {
        setConfig({ options: {}, defaults: {}, openai_configured: false });
        setSettings({
          retrieval_strategy: "hybrid", rerank_enabled: true,
          llm_provider: "openai", top_k: 20, final_top_k: 5,
        });
      });
    refreshSources();
  }, [refreshSources]);

  // Conversation list.
  useEffect(() => {
    apiListConversations()
      .then((list) => {
        if (list.length) {
          setConversations(list);
          setActiveId(list[0].id); // server returns newest-first
        } else {
          const conv = newConversation();
          setConversations([conv]);
          setActiveId(conv.id);
        }
      })
      .catch(() => {
        const conv = newConversation();
        setConversations([conv]);
        setActiveId(conv.id);
      });
  }, []);

  // Load messages for the active conversation when it changes.
  useEffect(() => {
    if (!activeId) return;
    const summary = convsRef.current.find((c) => c.id === activeId);
    if (summary && (summary.messageCount || 0) === 0) {
      setActiveMessages([]); // brand-new / empty — no fetch needed
      return;
    }
    let cancelled = false;
    setActiveMessages(null);
    apiGetConversation(activeId)
      .then((full) => { if (!cancelled) setActiveMessages(sanitizeMessages(full.messages)); })
      .catch(() => { if (!cancelled) setActiveMessages([]); });
    return () => { cancelled = true; };
  }, [activeId]);

  // Persist a conversation (called debounced by Chat after each settled turn).
  const persist = useCallback(async (id, messages) => {
    const summary = convsRef.current.find((c) => c.id === id);
    let title = summary?.title;
    if (!title || title === "New chat") {
      const firstUser = messages.find((m) => m.role === "user");
      if (firstUser) title = titleFrom(firstUser.text);
    }
    try {
      const res = await apiUpsertConversation(id, { title, messages });
      setConversations((prev) => {
        const others = prev.filter((c) => c.id !== id);
        return [res, ...others]; // move to top (most recent)
      });
    } catch {
      /* keep local state; will retry on next change */
    }
  }, []);

  function newChat() {
    const empty = conversations.find((c) => (c.messageCount || 0) === 0);
    if (empty) { setActiveId(empty.id); return; }
    const conv = newConversation();
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
  }

  async function deleteChat(id) {
    try { await apiDeleteConversation(id); } catch { /* ignore */ }
    setConversations((prev) => {
      const list = prev.filter((c) => c.id !== id);
      if (id === activeId) {
        if (list.length) setActiveId(list[0].id);
        else {
          const conv = newConversation();
          setActiveId(conv.id);
          return [conv];
        }
      }
      return list;
    });
  }

  async function renameChat(id, title) {
    setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
    try { await apiRenameConversation(id, title); } catch { /* ignore */ }
  }

  if (!settings || !activeId) return <div className="boot">Loading…</div>;

  return (
    <div className={`app ${sidebarOpen ? "" : "collapsed"}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand">✦ DocChat</div>
          <button className="icon-btn" onClick={() => setSidebarOpen(false)} title="Hide sidebar">⟨</button>
        </div>

        <button className="new-chat" onClick={newChat}>✎ New chat</button>

        <div className="sidebar-scroll">
          <div className="sidebar-section">
            <div className="section-label">Chats</div>
            <History
              conversations={conversations}
              activeId={activeId}
              onSelect={setActiveId}
              onDelete={deleteChat}
              onRename={renameChat}
            />
          </div>
          <div className="sidebar-section">
            <Sources sources={sources} totalChunks={totalChunks} onChange={refreshSources} />
          </div>
        </div>

        <div className="sidebar-foot">
          <button className="settings-toggle" onClick={() => setShowSettings((s) => !s)}>
            ⚙ Retrieval settings {showSettings ? "▾" : "▸"}
          </button>
          {showSettings && <Settings config={config} settings={settings} onChange={setSettings} />}
        </div>
      </aside>

      <main className="main">
        {!sidebarOpen && (
          <button className="icon-btn floating" onClick={() => setSidebarOpen(true)} title="Show sidebar">⟩</button>
        )}
        {activeMessages === null ? (
          <div className="boot">Loading conversation…</div>
        ) : (
          <Chat
            key={activeId}
            settings={settings}
            disabled={totalChunks === 0}
            onIngested={refreshSources}
            initialMessages={activeMessages}
            onPersist={(msgs) => persist(activeId, msgs)}
          />
        )}
      </main>
    </div>
  );
}
