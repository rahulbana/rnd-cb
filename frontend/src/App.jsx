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

  const onIngested = useCallback(() => {
    refreshSources();
  }, [refreshSources]);

  if (!settings) return <div className="loading">Loading…</div>;

  return (
    <div className="app">
      <header className="app-header">
        <h1>🧠 Intelligent RAG Chatbot</h1>
        <span className="subtitle">
          Multi-format ingestion · switchable retrieval · streaming answers
        </span>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <Uploader onIngested={onIngested} />
          <Settings config={config} settings={settings} onChange={setSettings} />
          <Sources
            sources={sources}
            totalChunks={totalChunks}
            onChange={refreshSources}
          />
        </aside>

        <main className="main">
          <Chat settings={settings} disabled={totalChunks === 0} />
        </main>
      </div>
    </div>
  );
}
