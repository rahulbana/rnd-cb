import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const nameFor = (langs, code) =>
  langs.find((l) => l.code === code)?.name || code;

// Displays translation history with a clear-all action.
export default function HistoryPanel({ meta, refreshKey }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setEntries(await api.history());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]);

  const clear = async () => {
    await api.clearHistory();
    load();
  };

  return (
    <div className="card">
      <div className="row" style={{ marginTop: 0, justifyContent: "space-between" }}>
        <strong>{entries.length} translation(s)</strong>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn ghost" onClick={load}>
            Refresh
          </button>
          <button className="btn ghost" onClick={clear} disabled={entries.length === 0}>
            Clear all
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <p className="hint">Loading…</p>}

      {!loading && entries.length === 0 && (
        <div className="empty">No translations yet. Translate something to see it here.</div>
      )}

      <div style={{ marginTop: 16 }}>
        {entries.map((e) => (
          <div className="history-item" key={e.id}>
            <div className="meta">
              <span className="badge">{e.style}</span>
              <span>
                {nameFor(meta.languages, e.detected_source_lang || e.source_lang)} →{" "}
                {nameFor(meta.languages, e.target_lang)}
              </span>
              <span>{new Date(e.created_at).toLocaleString()}</span>
            </div>
            <div className="pair">
              <div className="orig" style={{ color: "var(--muted)" }}>
                {e.original}
              </div>
              <div>{e.translated_text}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
