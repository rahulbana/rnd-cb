import { useEffect, useState } from "react";
import { api } from "./api/client.js";
import SqlResult from "./components/SqlResult.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";

const SAMPLE_SCHEMA = `-- Sample e-commerce schema
CREATE TABLE customers (
  customer_id   INTEGER PRIMARY KEY,
  name          TEXT,
  country       TEXT,
  created_at    TIMESTAMP
);

CREATE TABLE sales (
  sale_id       INTEGER PRIMARY KEY,
  customer_id   INTEGER REFERENCES customers(customer_id),
  product       TEXT,
  revenue       NUMERIC,
  sold_at       TIMESTAMP
);`;

const DIALECTS = ["postgres", "mysql", "sqlite", "snowflake", "bigquery", "tsql"];

export default function App() {
  const [schema, setSchema] = useState(SAMPLE_SCHEMA);
  const [question, setQuestion] = useState("Show the top 10 customers by revenue.");
  const [dialect, setDialect] = useState("postgres");

  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    refreshHistory();
  }, []);

  const refreshHistory = () => {
    api
      .listHistory()
      .then((data) => setHistory(data.items))
      .catch(() => {});
  };

  const generate = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.generate({
        question,
        schema_text: schema,
        dialect,
      });
      setResult(res);
      refreshHistory();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const reformat = async () => {
    if (!result) return;
    setBusy(true);
    try {
      const { sql } = await api.format({ sql: result.sql, dialect });
      const validation = await api.validate({ sql, dialect });
      setResult({ ...result, sql, validation });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const explainAgain = async () => {
    if (!result) return;
    setBusy(true);
    try {
      const { explanation } = await api.explain({
        sql: result.sql,
        schema_text: schema,
        dialect,
      });
      setResult({ ...result, explanation });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const loadHistoryItem = (item) => {
    setQuestion(item.question);
    setDialect(item.dialect || "postgres");
    setResult({
      sql: item.sql,
      explanation: item.explanation,
      validation: null,
      tables_used: [],
      assumptions: [],
    });
    // Re-validate the loaded SQL so badges are accurate.
    api
      .validate({ sql: item.sql, dialect: item.dialect })
      .then((validation) =>
        setResult((r) => (r ? { ...r, validation } : r))
      )
      .catch(() => {});
  };

  const deleteItem = async (id) => {
    await api.deleteHistoryItem(id).catch(() => {});
    refreshHistory();
  };

  const clearAll = async () => {
    await api.clearHistory().catch(() => {});
    refreshHistory();
  };

  const llmReady = health?.llm_configured;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>🧠 AI SQL Generator</h1>
          <div className="subtitle">
            Natural language → read-only SQL, with explanation, formatting &amp; validation.
          </div>
        </div>
        {health && (
          <span className={`status-pill ${llmReady ? "ok" : "warn"}`}>
            {llmReady
              ? `LLM ready · ${health.model}`
              : "LLM not configured — set OPENAI_API_KEY"}
          </span>
        )}
      </header>

      <div className="layout">
        <main>
          <div className="panel">
            <h2>1 · Database Schema</h2>
            <label>Paste DDL or describe your tables (optional)</label>
            <textarea
              className="schema"
              value={schema}
              onChange={(e) => setSchema(e.target.value)}
              placeholder="CREATE TABLE ..."
            />
            <div className="toolbar">
              <button
                className="btn small secondary"
                onClick={() => setSchema(SAMPLE_SCHEMA)}
              >
                Load sample schema
              </button>
              <button className="btn small secondary" onClick={() => setSchema("")}>
                Clear
              </button>
            </div>
          </div>

          <div className="panel">
            <h2>2 · Your Question</h2>
            <div className="row">
              <div className="grow">
                <label>Ask in plain English</label>
                <textarea
                  className="question"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="e.g. Show the top 10 customers by revenue."
                />
              </div>
              <div>
                <label>Dialect</label>
                <select value={dialect} onChange={(e) => setDialect(e.target.value)}>
                  {DIALECTS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="toolbar">
              <button className="btn" onClick={generate} disabled={loading}>
                {loading && <span className="spinner" />}
                {loading ? "Generating…" : "Generate SQL"}
              </button>
            </div>
            {error && <div className="error-box">{error}</div>}
          </div>

          <SqlResult
            result={result}
            onFormat={reformat}
            onExplain={explainAgain}
            busy={busy}
          />
        </main>

        <aside>
          <HistoryPanel
            items={history}
            onSelect={loadHistoryItem}
            onDelete={deleteItem}
            onClear={clearAll}
          />
        </aside>
      </div>
    </div>
  );
}
