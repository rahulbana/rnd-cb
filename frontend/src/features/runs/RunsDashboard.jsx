import React, { useCallback, useEffect, useState } from "react";

import { listRuns } from "../../api/runsApi";
import RunDetail from "./RunDetail";

function fmtTime(ts) {
  return new Date(ts * 1000).toLocaleString();
}

export default function RunsDashboard() {
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    listRuns(100)
      .then(setRuns)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (selected) {
    return <RunDetail runId={selected} onBack={() => setSelected(null)} />;
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Run History</h2>
        <button className="btn-ghost" onClick={refresh} disabled={loading}>
          {loading ? "Refreshing…" : "↻ Refresh"}
        </button>
      </div>

      {error && <div className="error-banner">⚠️ {error}</div>}

      {runs.length === 0 && !loading && (
        <p className="muted">No runs yet. Run a search to see it here.</p>
      )}

      {runs.length > 0 && (
        <table className="runs-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Query</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Sub-q</th>
              <th>Sources</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} onClick={() => setSelected(r.id)} className="run-row">
                <td className="nowrap">{fmtTime(r.started_at)}</td>
                <td className="run-query-cell">{r.query}</td>
                <td>
                  <span className={`status-pill status-${r.status}`}>{r.status}</span>
                </td>
                <td>{r.duration_ms != null ? `${(r.duration_ms / 1000).toFixed(1)}s` : "—"}</td>
                <td>{r.num_subqueries}</td>
                <td>{r.num_sources}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
