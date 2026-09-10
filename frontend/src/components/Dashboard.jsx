import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EMOTION_EMOJI, SENTIMENT_COLORS } from "../lib/format.js";

const AXIS = { fill: "#93a0b8", fontSize: 12 };

// Aggregate dashboard for a batch of results.
export default function Dashboard({ summary, results }) {
  const sentimentData = [
    { name: "Positive", value: summary.positive, key: "positive" },
    { name: "Negative", value: summary.negative, key: "negative" },
    { name: "Neutral", value: summary.neutral, key: "neutral" },
    { name: "Mixed", value: summary.mixed, key: "mixed" },
  ].filter((d) => d.value > 0);

  const emotionData = Object.entries(summary.emotion_distribution)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <div>
      <div className="card">
        <div className="section-title">Overview · {summary.total} items</div>
        <div className="stat-grid">
          <div className="stat">
            <div className="big" style={{ color: SENTIMENT_COLORS.positive }}>
              {summary.positive}
            </div>
            <div className="cap">Positive</div>
          </div>
          <div className="stat">
            <div className="big" style={{ color: SENTIMENT_COLORS.negative }}>
              {summary.negative}
            </div>
            <div className="cap">Negative</div>
          </div>
          <div className="stat">
            <div className="big" style={{ color: SENTIMENT_COLORS.neutral }}>
              {summary.neutral}
            </div>
            <div className="cap">Neutral</div>
          </div>
          <div className="stat">
            <div className="big" style={{ color: SENTIMENT_COLORS.mixed }}>
              {summary.mixed}
            </div>
            <div className="cap">Mixed</div>
          </div>
          <div className="stat">
            <div className="big">{summary.average_score.toFixed(2)}</div>
            <div className="cap">Avg score</div>
          </div>
          <div className="stat">
            <div className="big">{Math.round(summary.average_confidence * 100)}%</div>
            <div className="cap">Avg confidence</div>
          </div>
        </div>
      </div>

      <div className="charts">
        <div className="card">
          <div className="section-title">Sentiment distribution</div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={sentimentData}
                dataKey="value"
                nameKey="name"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
              >
                {sentimentData.map((d) => (
                  <Cell key={d.key} fill={SENTIMENT_COLORS[d.key]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#1c2333",
                  border: "1px solid #2c3547",
                  borderRadius: 8,
                  color: "#e6ebf5",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="chip-list" style={{ justifyContent: "center" }}>
            {sentimentData.map((d) => (
              <span className="chip" key={d.key}>
                <span style={{ color: SENTIMENT_COLORS[d.key] }}>●</span> {d.name} ({d.value})
              </span>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="section-title">Emotion distribution</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={emotionData} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
              <XAxis dataKey="name" tick={AXIS} tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} tick={AXIS} tickLine={false} axisLine={false} />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                contentStyle={{
                  background: "#1c2333",
                  border: "1px solid #2c3547",
                  borderRadius: 8,
                  color: "#e6ebf5",
                }}
              />
              <Bar dataKey="value" fill="#6d8bff" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {(summary.top_positive_keywords.length > 0 ||
        summary.top_negative_keywords.length > 0) && (
        <div className="card">
          <div className="aspects" style={{ marginTop: 0 }}>
            <div>
              <div className="section-title">Top positive keywords</div>
              <div className="chip-list">
                {summary.top_positive_keywords.map((k) => (
                  <span className="chip pos" key={k}>
                    {k}
                  </span>
                ))}
                {!summary.top_positive_keywords.length && <p className="hint">None.</p>}
              </div>
            </div>
            <div>
              <div className="section-title">Top negative keywords</div>
              <div className="chip-list">
                {summary.top_negative_keywords.map((k) => (
                  <span className="chip neg" key={k}>
                    {k}
                  </span>
                ))}
                {!summary.top_negative_keywords.length && <p className="hint">None.</p>}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="section-title">All results</div>
        <div className="table-wrap">
          <table className="results">
            <thead>
              <tr>
                <th>Text</th>
                <th>Overall</th>
                <th>Score</th>
                <th>Emotion</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td className="text">{r.text}</td>
                  <td>
                    <span className={`badge ${r.overall}`}>{r.overall}</span>
                  </td>
                  <td style={{ color: SENTIMENT_COLORS[r.overall] }}>{r.score.toFixed(2)}</td>
                  <td>
                    {EMOTION_EMOJI[r.emotion]} {r.emotion}
                  </td>
                  <td>{Math.round(r.confidence * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
