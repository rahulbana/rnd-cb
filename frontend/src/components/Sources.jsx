import React from "react";

function hostname(url) {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

export default function Sources({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="card sources">
      <h3 className="section-title">
        Sources <span className="count">{sources.length}</span>
      </h3>
      <ul className="source-list">
        {sources.map((s, i) => (
          <li key={`${s.url}-${i}`} className="source-item">
            <a href={s.url} target="_blank" rel="noreferrer" className="source-link">
              <span className="source-index">{i + 1}</span>
              <span className="source-body">
                <span className="source-title">{s.title || hostname(s.url)}</span>
                <span className="source-host">{hostname(s.url)}</span>
                {s.snippet && <span className="source-snippet">{s.snippet}</span>}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
