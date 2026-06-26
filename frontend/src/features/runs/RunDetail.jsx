import React, { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import { getRun } from "../../api/runsApi";
import { hostname } from "../../utils/format";

function fmtTime(ts) {
  return new Date(ts * 1000).toLocaleString();
}

export default function RunDetail({ runId, onBack }) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    getRun(runId)
      .then((r) => active && setRun(r))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [runId]);

  if (error) return <div className="error-banner">⚠️ {error}</div>;
  if (!run) return <div className="panel">Loading run…</div>;

  return (
    <div className="run-detail">
      <button className="btn-ghost" onClick={onBack}>
        ← Back to history
      </button>

      <div className="panel">
        <div className="panel-header">
          <h2>Query</h2>
          <span className={`status-pill status-${run.status}`}>{run.status}</span>
        </div>
        <p className="run-query">{run.query}</p>
        <div className="run-meta">
          <span>{fmtTime(run.started_at)}</span>
          {run.duration_ms != null && <span>· {(run.duration_ms / 1000).toFixed(1)}s</span>}
          <span>· {run.subqueries.length} sub-queries</span>
          <span>· {run.sources.length} sources</span>
        </div>
        {run.error && <div className="error-banner">⚠️ {run.error}</div>}
      </div>

      {run.subqueries.length > 0 && (
        <div className="panel">
          <div className="panel-header"><h2>Sub-queries</h2></div>
          <ol className="subq-list">
            {run.subqueries.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ol>
        </div>
      )}

      <div className="panel">
        <div className="panel-header"><h2>Steps ({run.steps.length})</h2></div>
        <ul className="step-log">
          {run.steps.map((s, i) => (
            <li key={i} className="step">
              <span className="step-type">{s.type}</span>
              <span className="step-detail">
                {s.detail || s.node || s.tool || ""}
                {s.tool && <span className="tool-tag">{s.tool}</span>}
                {s.error && <span className="step-error"> {s.error}</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {run.sources.length > 0 && (
        <div className="panel">
          <div className="panel-header"><h2>Sources ({run.sources.length})</h2></div>
          <ol className="resource-list">
            {run.sources.map((s, i) => (
              <li key={s.url || i} className="resource">
                <span className="resource-index">[{i + 1}]</span>
                <div className="resource-body">
                  <a href={s.url} target="_blank" rel="noreferrer" className="resource-title">
                    {s.title || s.url}
                  </a>
                  <div className="resource-meta">
                    <span className="resource-host">{hostname(s.url)}</span>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {run.report && (
        <div className="panel">
          <div className="panel-header"><h2>Report</h2></div>
          <div className="markdown">
            <ReactMarkdown>{run.report}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
