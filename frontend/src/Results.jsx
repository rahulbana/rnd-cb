// Renders the structured rating returned by the backend.

function scoreColor(score) {
  if (score >= 75) return "#16a34a"; // green
  if (score >= 50) return "#d97706"; // amber
  return "#dc2626"; // red
}

function ScoreRing({ score }) {
  const color = scoreColor(score);
  return (
    <div
      className="ring"
      style={{
        background: `conic-gradient(${color} ${score * 3.6}deg, #e5e7eb 0deg)`,
      }}
    >
      <div className="ring-inner">
        <span className="ring-score" style={{ color }}>
          {score}
        </span>
        <span className="ring-label">/ 100</span>
      </div>
    </div>
  );
}

function Bar({ label, score, reasoning }) {
  return (
    <div className="bar-row">
      <div className="bar-head">
        <span>{label}</span>
        <strong style={{ color: scoreColor(score) }}>{score}</strong>
      </div>
      <div className="bar-track">
        <div
          className="bar-fill"
          style={{ width: `${score}%`, background: scoreColor(score) }}
        />
      </div>
      {reasoning && <p className="bar-reason">{reasoning}</p>}
    </div>
  );
}

function Chips({ items, variant }) {
  if (!items?.length) return <p className="muted">None</p>;
  return (
    <div className="chips">
      {items.map((item, i) => (
        <span key={i} className={`chip ${variant}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

function List({ items }) {
  if (!items?.length) return <p className="muted">None</p>;
  return (
    <ul className="list">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

export default function Results({ data }) {
  return (
    <div className="card results">
      <div className="verdict">
        <ScoreRing score={data.overall_score} />
        <div>
          <h2>{data.verdict}</h2>
          <p>{data.summary}</p>
        </div>
      </div>

      {data.categories?.length > 0 && (
        <section>
          <h3>Breakdown</h3>
          {data.categories.map((c, i) => (
            <Bar key={i} label={c.name} score={c.score} reasoning={c.reasoning} />
          ))}
        </section>
      )}

      <div className="grid">
        <section>
          <h3>✅ Matched skills</h3>
          <Chips items={data.matched_skills} variant="good" />
        </section>
        <section>
          <h3>❌ Missing skills</h3>
          <Chips items={data.missing_skills} variant="bad" />
        </section>
      </div>

      <div className="grid">
        <section>
          <h3>💪 Strengths</h3>
          <List items={data.strengths} />
        </section>
        <section>
          <h3>⚠️ Gaps</h3>
          <List items={data.gaps} />
        </section>
      </div>

      <section>
        <h3>🛠️ Recommendations</h3>
        <List items={data.recommendations} />
      </section>
    </div>
  );
}
