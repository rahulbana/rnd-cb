import React, { useEffect, useState } from "react";
import GenerateForm from "./components/GenerateForm.jsx";
import AgentProgress from "./components/AgentProgress.jsx";
import ResultView from "./components/ResultView.jsx";
import Sources from "./components/Sources.jsx";
import { generateStream, fetchHealth } from "./lib/api.js";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [statuses, setStatuses] = useState({});
  const [sources, setSources] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => {});
  }, []);

  const handleGenerate = async (form) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setSources([]);
    setStatuses({});

    try {
      await generateStream(form, (event) => {
        switch (event.type) {
          case "agent_start":
            setStatuses((s) => ({ ...s, [event.agent]: "running", [`${event.agent}_label`]: event.label }));
            break;
          case "agent_complete":
            setStatuses((s) => ({ ...s, [event.agent]: "done", [`${event.agent}_label`]: event.label }));
            break;
          case "sources":
            setSources(event.sources || []);
            break;
          case "complete":
            setResult(event.result);
            break;
          case "error":
            setError(event.message || "Something went wrong");
            break;
          default:
            break;
        }
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const anyActivity = loading || result || sources.length > 0;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">⚡</span>
          <div>
            <h1>ContentForge</h1>
            <p className="tagline">Multi-agent AI studio for content writers</p>
          </div>
        </div>
        {health && (
          <div className="health">
            <span className={`dot ${health.openai_configured ? "on" : "off"}`} />
            {health.openai_configured ? "AI ready" : "Demo mode"}
            {health.deep_search_configured ? " · Deep search on" : ""}
          </div>
        )}
      </header>

      <main className="layout">
        <section className="col-left">
          <GenerateForm onGenerate={handleGenerate} loading={loading} />
          {(loading || Object.keys(statuses).length > 0) && <AgentProgress statuses={statuses} />}
        </section>

        <section className="col-right">
          {error && <div className="card error-banner">⚠ {error}</div>}
          {!anyActivity && !error && (
            <div className="card empty">
              <div className="empty-emoji">📝</div>
              <h3>Your generated content will appear here</h3>
              <p className="muted">
                Fill in the form and hit generate. Three AI agents will research a trending topic,
                write your piece, and verify it — with sources shown for transparency.
              </p>
            </div>
          )}
          {result && <ResultView result={result} />}
          <Sources sources={sources} />
        </section>
      </main>

      <footer className="footer">
        <span>Built with FastAPI · OpenAI · React · PostgreSQL</span>
      </footer>
    </div>
  );
}
