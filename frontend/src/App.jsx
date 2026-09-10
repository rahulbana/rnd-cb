import { useEffect, useState } from "react";
import { getHealth } from "./lib/api.js";
import SingleAnalyze from "./components/SingleAnalyze.jsx";
import BatchAnalyze from "./components/BatchAnalyze.jsx";

export default function App() {
  const [tab, setTab] = useState("single");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <div className="app">
      <header className="masthead">
        <div className="brand">
          <div className="logo">🧠</div>
          <div>
            <h1>AI Sentiment Analyzer</h1>
            <p>Sentiment, emotion, keywords & confidence — single or batch.</p>
          </div>
        </div>
        {health && (
          <div className="engine-pill">
            Engine: <b>{health.engine === "openai" ? `OpenAI · ${health.model}` : "Lexicon fallback"}</b>
          </div>
        )}
      </header>

      <div className="tabs">
        <button
          className={`tab ${tab === "single" ? "active" : ""}`}
          onClick={() => setTab("single")}
        >
          Single
        </button>
        <button
          className={`tab ${tab === "batch" ? "active" : ""}`}
          onClick={() => setTab("batch")}
        >
          Batch & CSV
        </button>
      </div>

      {tab === "single" ? <SingleAnalyze /> : <BatchAnalyze />}
    </div>
  );
}
