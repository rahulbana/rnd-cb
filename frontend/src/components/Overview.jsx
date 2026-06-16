function Stat({ label, value, accent }) {
  return (
    <div className={`stat-card ${accent || ""}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default function Overview({ overview, llmUsed }) {
  const fmt = (n) => n.toLocaleString();
  return (
    <section className="overview">
      <div className="overview-head">
        <h2>{overview.filename}</h2>
        <span className={`source-pill ${llmUsed ? "ai" : "rule"}`}>
          {llmUsed ? "AI-generated insights" : "Heuristic insights"}
        </span>
      </div>
      <div className="stat-grid">
        <Stat label="Rows" value={fmt(overview.rows)} />
        <Stat label="Columns" value={fmt(overview.columns)} />
        <Stat
          label="Missing cells"
          value={`${overview.missing_pct}%`}
          accent={overview.missing_pct > 10 ? "warn" : ""}
        />
        <Stat
          label="Duplicate rows"
          value={fmt(overview.duplicate_rows)}
          accent={overview.duplicate_rows > 0 ? "warn" : ""}
        />
        <Stat label="Memory" value={`${overview.memory_kb} KB`} />
      </div>
      <div className="type-chips">
        {Object.entries(overview.type_breakdown).map(([type, count]) => (
          <span key={type} className={`type-chip t-${type}`}>
            {type}: {count}
          </span>
        ))}
      </div>
    </section>
  );
}
