import React, { useCallback, useEffect, useState } from "react";
import { getConfig, listSources } from "./api";
import {
  loadConversations, saveConversations, newConversation, titleFrom,
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

  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);

  const refreshSources = useCallback(async () => {
    try {
      const data = await listSources();
      setSources(data.sources || []);
      setTotalChunks(data.total_chunks || 0);
    } catch {
      /* backend may still be starting */
    }
  }, []);

  // Load config + conversation history on mount.
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

    const loaded = loadConversations();
    if (loaded.length) {
      const newest = [...loaded].sort((a, b) => b.updatedAt - a.updatedAt)[0];
      setConversations(loaded);
      setActiveId(newest.id);
    } else {
      const conv = newConversation();
      setConversations([conv]);
      setActiveId(conv.id);
    }
  }, [refreshSources]);

  // Persist history whenever it changes.
  useEffect(() => {
    if (conversations.length) saveConversations(conversations);
  }, [conversations]);

  const persist = useCallback((id, messages) => {
    setConversations((prev) => {
      const i = prev.findIndex((c) => c.id === id);
      if (i < 0) return prev;
      const conv = { ...prev[i], messages, updatedAt: Date.now() };
      if (conv.title === "New chat" || !conv.title) {
        const firstUser = messages.find((m) => m.role === "user");
        if (firstUser) conv.title = titleFrom(firstUser.text);
      }
      const list = prev.slice();
      list[i] = conv;
      return list;
    });
  }, []);

  function newChat() {
    const empty = conversations.find((c) => !c.messages || !c.messages.length);
    if (empty) { setActiveId(empty.id); return; }
    const conv = newConversation();
    setConversations((prev) => [conv, ...prev]);
    setActiveId(conv.id);
  }

  function deleteChat(id) {
    setConversations((prev) => {
      const list = prev.filter((c) => c.id !== id);
      if (id === activeId) {
        const next = [...list].sort((a, b) => b.updatedAt - a.updatedAt)[0];
        if (next) setActiveId(next.id);
        else {
          const conv = newConversation();
          setActiveId(conv.id);
          return [conv];
        }
      }
      return list;
    });
  }

  function renameChat(id, title) {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title } : c))
    );
  }

  if (!settings || !activeId) return <div className="boot">Loading…</div>;

  const activeConv = conversations.find((c) => c.id === activeId);

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
        <Chat
          key={activeId}
          settings={settings}
          disabled={totalChunks === 0}
          onIngested={refreshSources}
          initialMessages={activeConv ? activeConv.messages : []}
          onPersist={(msgs) => persist(activeId, msgs)}
        />
      </main>
    </div>
  );
}
