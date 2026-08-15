import React, { useCallback, useEffect, useState } from "react";
import { getConfig, listSources } from "./api";
import Uploader from "./components/Uploader.jsx";
import Settings from "./components/Settings.jsx";
import Sources from "./components/Sources.jsx";
import Chat from "./components/Chat.jsx";

export default function App() {
  const [config, setConfig] = useState(null);
  const [settings, setSettings] = useState(null);
  const [sources, setSources] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [sessionKey, setSessionKey] = useState(0); // bump to start a new chat
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

  const refreshSources = useCallback(async () => {
    try {
      const data = await listSources();
      setSources(data.sources || []);
      setTotalChunks(data.total_chunks || 0);
    } catch {
      /* backend may still be starting */
    }
  }, []);

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
          retrieval_strategy: "hybrid",
          rerank_enabled: true,
          llm_provider: "openai",
          top_k: 20,
          final_top_k: 5,
        });
      });
    refreshSources();
  }, [refreshSources]);

  if (!settings) return <div className="boot">Loading…</div>;

  return (
    <div className={`app ${sidebarOpen ? "" : "collapsed"}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <div className="brand">✦ DocChat</div>
          <button className="icon-btn" onClick={() => setSidebarOpen(false)} title="Hide sidebar">
            ⟨
          </button>
        </div>

        <button className="new-chat" onClick={() => setSessionKey((k) => k + 1)}>
          ✎ New chat
        </button>

        <div className="sidebar-scroll">
          <Uploader onIngested={refreshSources} />
          <Sources sources={sources} totalChunks={totalChunks} onChange={refreshSources} />
        </div>

        <div className="sidebar-foot">
          <button className="settings-toggle" onClick={() => setShowSettings((s) => !s)}>
            ⚙ Retrieval settings {showSettings ? "▾" : "▸"}
          </button>
          {showSettings && (
            <Settings config={config} settings={settings} onChange={setSettings} />
          )}
        </div>
      </aside>

      <main className="main">
        {!sidebarOpen && (
          <button className="icon-btn floating" onClick={() => setSidebarOpen(true)} title="Show sidebar">
            ⟩
          </button>
        )}
        <Chat key={sessionKey} settings={settings} disabled={totalChunks === 0} />
      </main>
    </div>
  );
}
