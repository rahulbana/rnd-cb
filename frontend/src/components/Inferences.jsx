export default function Inferences({ result }) {
  const { narrative, inferences, suggested_questions, correlations } = result;
  return (
    <section className="insights">
      <div className="narrative-card">
        <h3>What the agent understood</h3>
        <p>{narrative}</p>
      </div>

      <div className="insight-columns">
        <div className="insight-block">
          <h3>Key inferences</h3>
          <ul className="inference-list">
            {inferences.map((text, i) => (
              <li key={i}>
                <span className="bullet">›</span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <div className="insight-block">
          <h3>Questions worth exploring</h3>
          <ul className="question-list">
            {suggested_questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>

          {correlations.length > 0 && (
            <>
              <h3 className="mt">Notable relationships</h3>
              <ul className="corr-list">
                {correlations.slice(0, 6).map((c, i) => (
                  <li key={i}>
                    <code>{c.column_a}</code> ↔ <code>{c.column_b}</code>
                    <span className={`corr-tag ${c.direction}`}>
                      {c.strength} {c.direction} (r={c.coefficient})
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
