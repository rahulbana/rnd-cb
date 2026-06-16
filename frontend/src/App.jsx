import { useEffect, useState } from "react";
import { analyzeCsv, fetchHealth } from "./api";
import FileUpload from "./components/FileUpload.jsx";
import Overview from "./components/Overview.jsx";
import Inferences from "./components/Inferences.jsx";
import ChartRenderer from "./components/ChartRenderer.jsx";
import ColumnTable from "./components/ColumnTable.jsx";
import DataPreview from "./components/DataPreview.jsx";

const TABS = [
  { id: "insights", label: "Insights" },
  { id: "charts", label: "Charts" },
  { id: "columns", label: "Columns" },
  { id: "data", label: "Data" },
];

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("insights");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchHealth().then(setHealth);
  }, []);

  async function handleFile(file) {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeCsv(file);
      setResult(data);
      setTab("insights");
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
          <span className="logo">◆</span>
          <div>
            <h1>CSV Insight Agent</h1>
            <p className="tagline">
              Autonomous, multi-perspective analysis of any CSV
            </p>
          </div>
        </div>
        {health && (
          <div className={`llm-badge ${health.llm_enabled ? "on" : "off"}`}>
            {health.llm_enabled
              ? `LLM: ${health.model}`
              : "LLM: rule-based fallback"}
          </div>
        )}
      </header>

      <main className="container">
        <FileUpload onFile={handleFile} loading={loading} hasResult={!!result} />

        {error && <div className="error-box">⚠ {error}</div>}

        {loading && (
          <div className="loading">
            <div className="spinner" />
            <p>The agent is reading your data from every angle…</p>
          </div>
        )}

        {result && !loading && (
          <>
            <Overview overview={result.overview} llmUsed={result.llm_used} />

            <nav className="tabs">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  className={tab === t.id ? "tab active" : "tab"}
                  onClick={() => setTab(t.id)}
                >
                  {t.label}
                  {t.id === "charts" && ` (${result.charts.length})`}
                  {t.id === "columns" && ` (${result.columns.length})`}
                </button>
              ))}
            </nav>

            {tab === "insights" && <Inferences result={result} />}
            {tab === "charts" && (
              <div className="chart-grid">
                {result.charts.map((c) => (
                  <ChartRenderer key={c.id} spec={c} />
                ))}
              </div>
            )}
            {tab === "columns" && <ColumnTable columns={result.columns} />}
            {tab === "data" && (
              <DataPreview rows={result.sample_rows} columns={result.columns} />
            )}
          </>
        )}
      </main>

      <footer className="footer">
        FastAPI · OpenAI · React · Recharts — drop a CSV to begin.
      </footer>
    </div>
  );
}
