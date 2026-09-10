import React, { useEffect, useMemo, useRef, useState } from "react";
import CodeEditor from "./components/CodeEditor.jsx";
import ResultPanel from "./components/ResultPanel.jsx";
import { analyze, detectLanguage, getActions, getHealth } from "./api.js";

const SAMPLE = `def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
`;

const AUDIENCES = [
  { key: "beginner", label: "Beginner" },
  { key: "intermediate", label: "Intermediate" },
  { key: "expert", label: "Expert" },
];

export default function App() {
  const [code, setCode] = useState(SAMPLE);
  const [language, setLanguage] = useState("Python");
  const [audience, setAudience] = useState("beginner");
  const [actions, setActions] = useState([]);
  const [activeAction, setActiveAction] = useState(null);
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [llmReady, setLlmReady] = useState(true);

  const detectTimer = useRef(null);

  // Load the action list and backend health on mount.
  useEffect(() => {
    getActions()
      .then((data) => setActions(data.actions))
      .catch(() => setError("Could not reach the backend. Is it running?"));
    getHealth()
      .then((h) => setLlmReady(h.llm_configured))
      .catch(() => {});
  }, []);

  // Debounced language auto-detection as the user types.
  useEffect(() => {
    if (detectTimer.current) clearTimeout(detectTimer.current);
    if (!code.trim()) {
      setLanguage("Unknown");
      return;
    }
    detectTimer.current = setTimeout(() => {
      detectLanguage(code)
        .then((d) => setLanguage(d.language))
        .catch(() => {});
    }, 500);
    return () => clearTimeout(detectTimer.current);
  }, [code]);

  const actionLabel = useMemo(
    () => actions.find((a) => a.key === activeAction)?.label || "",
    [actions, activeAction]
  );

  async function runAction(actionKey) {
    if (!code.trim()) {
      setError("Please enter some code first.");
      return;
    }
    setActiveAction(actionKey);
    setLoading(true);
    setError("");
    setResult("");
    try {
      const data = await analyze({
        code,
        action: actionKey,
        language,
        audience,
      });
      setResult(data.result);
      setLanguage(data.language);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">{"</>"}</span>
          <div>
            <h1>AI Code Explainer</h1>
            <p className="tagline">Understand any code in plain language</p>
          </div>
        </div>
        <div className="audience-select">
          <label htmlFor="audience">Explain for:</label>
          <select
            id="audience"
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
          >
            {AUDIENCES.map((a) => (
              <option key={a.key} value={a.key}>
                {a.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      {!llmReady && (
        <div className="banner">
          ⚠️ The backend has no <code>OPENAI_API_KEY</code> configured. Add one
          to <code>backend/.env</code> and restart to enable AI responses.
        </div>
      )}

      <main className="layout">
        <section className="panel editor-panel">
          <div className="panel-header">
            <span>Code</span>
            <span className="lang-pill">{language || "Unknown"}</span>
          </div>
          <CodeEditor code={code} onChange={setCode} language={language} />
          <div className="toolbar">
            {actions.map((a) => (
              <button
                key={a.key}
                className={`action-btn ${
                  activeAction === a.key ? "active" : ""
                }`}
                disabled={loading}
                onClick={() => runAction(a.key)}
              >
                {a.label}
              </button>
            ))}
          </div>
        </section>

        <section className="panel output-panel">
          <div className="panel-header">
            <span>Explanation</span>
          </div>
          <ResultPanel
            loading={loading}
            error={error}
            result={result}
            actionLabel={actionLabel}
          />
        </section>
      </main>

      <footer className="footer">
        <span>FastAPI · React · OpenAI</span>
      </footer>
    </div>
  );
}
