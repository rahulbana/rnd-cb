import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import TranslatePanel from "./components/TranslatePanel.jsx";
import BatchPanel from "./components/BatchPanel.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";

const TABS = [
  { id: "single", label: "Translate" },
  { id: "batch", label: "Batch" },
  { id: "history", label: "History" },
];

export default function App() {
  const [meta, setMeta] = useState(null);
  const [metaError, setMetaError] = useState("");
  const [tab, setTab] = useState("single");
  // Bumping this triggers the history panel to reload after a translation.
  const [historyKey, setHistoryKey] = useState(0);

  useEffect(() => {
    api
      .metadata()
      .then(setMeta)
      .catch((e) => setMetaError(e.message));
  }, []);

  const bumpHistory = () => setHistoryKey((k) => k + 1);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🌐 AI Translator</h1>
        <p>Multilingual translation powered by an LLM — formal, casual, or technical.</p>
      </header>

      {metaError && <div className="error">Could not reach backend: {metaError}</div>}

      {meta && (
        <>
          <nav className="tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={tab === t.id ? "active" : ""}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {tab === "single" && <TranslatePanel meta={meta} onTranslated={bumpHistory} />}
          {tab === "batch" && <BatchPanel meta={meta} onTranslated={bumpHistory} />}
          {tab === "history" && <HistoryPanel meta={meta} refreshKey={historyKey} />}
        </>
      )}
    </div>
  );
}
