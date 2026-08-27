const META = {
  run_started: { icon: "◷", label: "Run started", cls: "t--muted" },
  planned: { icon: "◆", label: "Planned", cls: "t--plan" },
  searched: { icon: "⌕", label: "Searched", cls: "t--search" },
  reflected: { icon: "↻", label: "Reflected", cls: "t--reflect" },
  synthesized: { icon: "✎", label: "Synthesizing report", cls: "t--synth" },
  completed: { icon: "✓", label: "Completed", cls: "t--done" },
  error: { icon: "✕", label: "Error", cls: "t--error" },
  cancelled: { icon: "⊘", label: "Cancelled", cls: "t--warn" },
};

function Detail({ type, payload }) {
  if (type === "planned") {
    return (
      <div className="timeline__detail">
        {payload.plan?.length > 0 && (
          <ul className="mini-list">
            {payload.plan.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        )}
        {payload.queries?.length > 0 && (
          <div className="tags">
            {payload.queries.map((q, i) => (
              <span className="tag" key={i}>
                {q}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }
  if (type === "searched") {
    return (
      <div className="timeline__detail">
        <div className="tags">
          {(payload.queries || []).map((q, i) => (
            <span className="tag" key={i}>
              {q}
            </span>
          ))}
        </div>
        <div className="stat-row">
          <span className="stat">+{payload.new_sources ?? 0} sources</span>
          <span className="stat">+{payload.new_findings ?? 0} findings</span>
        </div>
      </div>
    );
  }
  if (type === "reflected") {
    return (
      <div className="timeline__detail">
        <div className="stat-row">
          <span className="stat">iteration {payload.iteration}</span>
          <span className="stat">
            {payload.is_complete ? "sufficient — finishing" : "gaps found — continuing"}
          </span>
        </div>
        {payload.knowledge_gaps?.length > 0 && !payload.is_complete && (
          <ul className="mini-list mini-list--gap">
            {payload.knowledge_gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  if (type === "error") {
    return <div className="timeline__detail err-text">{payload.message}</div>;
  }
  return null;
}

export default function ProgressTimeline({ events, running }) {
  return (
    <ol className="timeline">
      {events.map((e, idx) => {
        const meta = META[e.type] || { icon: "•", label: e.type, cls: "" };
        return (
          <li className={`timeline__item ${meta.cls}`} key={idx}>
            <span className="timeline__marker">{meta.icon}</span>
            <div className="timeline__body">
              <div className="timeline__label">{meta.label}</div>
              <Detail type={e.type} payload={e.payload} />
            </div>
          </li>
        );
      })}
      {running && (
        <li className="timeline__item t--live">
          <span className="timeline__marker spin">◌</span>
          <div className="timeline__body">
            <div className="timeline__label">Working…</div>
          </div>
        </li>
      )}
    </ol>
  );
}
