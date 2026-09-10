function scoreColor(score) {
  if (score >= 75) return "#16a34a";
  if (score >= 60) return "#ca8a04";
  return "#dc2626";
}

function Chips({ items, variant }) {
  if (!items?.length) return <p className="muted">None identified.</p>;
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
  if (!items?.length) return <p className="muted">None identified.</p>;
  return (
    <ul className="list">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  );
}

export default function Results({ data }) {
  const { analysis, filename, characters_extracted } = data;
  const score = analysis.overall_score ?? 0;
  const exp = analysis.experience || {};

  return (
    <section className="results">
      <div className="score-card">
        <div
          className="score-ring"
          style={{ "--ring": scoreColor(score), "--pct": score }}
        >
          <span className="score-value">{score}</span>
          <span className="score-max">/100</span>
        </div>
        <div className="score-meta">
          <h2>Overall Score</h2>
          <p className="muted">
            {filename} · {characters_extracted.toLocaleString()} characters analyzed
          </p>
          {exp.seniority_level && (
            <p className="badges">
              <span className="badge">{exp.seniority_level}</span>
              {exp.total_years ? (
                <span className="badge">{exp.total_years} yrs experience</span>
              ) : null}
            </p>
          )}
        </div>
      </div>

      {exp.summary && (
        <div className="card">
          <h3>Experience</h3>
          <p>{exp.summary}</p>
        </div>
      )}

      <div className="grid">
        <div className="card">
          <h3>Skills</h3>
          <Chips items={analysis.skills} variant="present" />
        </div>
        <div className="card">
          <h3>Missing Skills</h3>
          <Chips items={analysis.missing_skills} variant="missing" />
        </div>
      </div>

      <div className="grid">
        <div className="card">
          <h3>Strengths</h3>
          <List items={analysis.strengths} />
        </div>
        <div className="card">
          <h3>Weaknesses</h3>
          <List items={analysis.weaknesses} />
        </div>
      </div>

      <div className="card">
        <h3>Recommendations</h3>
        {analysis.recommendations?.length ? (
          <ol className="list ordered">
            {analysis.recommendations.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ol>
        ) : (
          <p className="muted">No recommendations.</p>
        )}
      </div>
    </section>
  );
}
