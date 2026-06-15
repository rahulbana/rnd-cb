import React from "react";

function hostname(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export default function ResourceList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="panel resources">
      <div className="panel-header">
        <h2>Resources ({sources.length})</h2>
      </div>
      <ol className="resource-list">
        {sources.map((s, i) => (
          <li key={s.url || i} className="resource">
            <span className="resource-index">[{i + 1}]</span>
            <div className="resource-body">
              <a href={s.url} target="_blank" rel="noreferrer" className="resource-title">
                {s.title || s.url}
              </a>
              <div className="resource-meta">
                <span className="resource-host">{hostname(s.url)}</span>
                {s.subquery && <span className="resource-subq">↳ {s.subquery}</span>}
              </div>
              {s.content && <p className="resource-snippet">{s.content.slice(0, 220)}…</p>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
