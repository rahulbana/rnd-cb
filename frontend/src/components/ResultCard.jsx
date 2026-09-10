import { EMOTION_EMOJI, pct, scoreToBar } from "../lib/format.js";

function Badge({ sentiment }) {
  return <span className={`badge ${sentiment}`}>{sentiment}</span>;
}

// Detailed view of a single AnalysisResult.
export default function ResultCard({ result }) {
  const bar = scoreToBar(result.score);
  const emotions = Object.entries(result.emotion_scores || {})
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="card">
      <div className="result-head">
        <Badge sentiment={result.overall} />
        <span className="badge neutral">
          {EMOTION_EMOJI[result.emotion] || "•"} {result.emotion}
        </span>
      </div>

      {result.summary && <p className="hint" style={{ marginTop: 12 }}>{result.summary}</p>}

      <div className="metrics">
        <div className="metric">
          <div className="label">Sentiment score</div>
          <div className="value" style={{ color: bar.color }}>
            {result.score.toFixed(2)}
          </div>
          <div className="bar">
            <span style={{ width: `${bar.pct}%`, background: bar.color }} />
          </div>
        </div>
        <div className="metric">
          <div className="label">Confidence</div>
          <div className="value">{pct(result.confidence)}</div>
          <div className="bar">
            <span style={{ width: pct(result.confidence), background: "var(--brand)" }} />
          </div>
        </div>
        <div className="metric">
          <div className="label">Dominant emotion</div>
          <div className="value" style={{ fontSize: 20 }}>
            {EMOTION_EMOJI[result.emotion]} {result.emotion}
          </div>
        </div>
      </div>

      <div className="aspects">
        <div>
          <div className="section-title">Positive aspects</div>
          {result.positive_aspects.length ? (
            <div className="chip-list">
              {result.positive_aspects.map((a) => (
                <span className="chip pos" key={a}>
                  {a}
                </span>
              ))}
            </div>
          ) : (
            <p className="hint">None detected.</p>
          )}
        </div>
        <div>
          <div className="section-title">Negative aspects</div>
          {result.negative_aspects.length ? (
            <div className="chip-list">
              {result.negative_aspects.map((a) => (
                <span className="chip neg" key={a}>
                  {a}
                </span>
              ))}
            </div>
          ) : (
            <p className="hint">None detected.</p>
          )}
        </div>
      </div>

      {result.keywords.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="section-title">Keywords</div>
          <div className="chip-list">
            {result.keywords.map((k) => (
              <span className="chip" key={k}>
                {k}
              </span>
            ))}
          </div>
        </div>
      )}

      {emotions.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="section-title">Emotion breakdown</div>
          {emotions.map(([name, val]) => (
            <div key={name} style={{ marginBottom: 8 }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span style={{ fontSize: 13 }}>
                  {EMOTION_EMOJI[name]} {name}
                </span>
                <span className="hint" style={{ margin: 0 }}>
                  {pct(val)}
                </span>
              </div>
              <div className="bar">
                <span style={{ width: pct(val), background: "var(--brand)" }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
