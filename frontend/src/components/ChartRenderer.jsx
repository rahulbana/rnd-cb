import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

const PALETTE = [
  "#6366f1",
  "#06b6d4",
  "#f59e0b",
  "#ef4444",
  "#10b981",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#3b82f6",
];

// Map a correlation value in [-1, 1] to a diverging blue↔red colour.
function heatColor(v) {
  if (v === null || v === undefined) return "#1e293b";
  const t = Math.max(-1, Math.min(1, v));
  if (t >= 0) {
    const a = t; // 0..1 toward indigo
    return `rgba(99, 102, 241, ${0.15 + 0.85 * a})`;
  }
  const a = -t; // 0..1 toward red
  return `rgba(239, 68, 68, ${0.15 + 0.85 * a})`;
}

function Heatmap({ spec }) {
  const labels = spec.meta?.labels || [];
  const lookup = {};
  for (const cell of spec.data) lookup[`${cell.x}|${cell.y}`] = cell.value;

  return (
    <div className="heatmap-wrap">
      <table className="heatmap">
        <thead>
          <tr>
            <th />
            {labels.map((l) => (
              <th key={l} className="heat-h">
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((row) => (
            <tr key={row}>
              <th className="heat-row">{row}</th>
              {labels.map((col) => {
                const v = lookup[`${col}|${row}`];
                return (
                  <td
                    key={col}
                    className="heat-cell"
                    style={{ background: heatColor(v) }}
                    title={`${row} vs ${col}: ${v}`}
                  >
                    {v?.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChartBody({ spec }) {
  const { type, data, x_key, y_keys } = spec;

  switch (type) {
    case "pie":
      return (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie
              data={data}
              dataKey={y_keys[0]}
              nameKey={x_key}
              cx="50%"
              cy="50%"
              outerRadius={95}
              label
            >
              {data.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      );

    case "line":
      return (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey={x_key} stroke="#94a3b8" fontSize={11} />
            <YAxis stroke="#94a3b8" fontSize={11} />
            <Tooltip />
            {y_keys.map((k, i) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                stroke={PALETTE[i % PALETTE.length]}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      );

    case "scatter":
      return (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart>
            <CartesianGrid stroke="#1e293b" />
            <XAxis
              type="number"
              dataKey={x_key}
              name={x_key}
              stroke="#94a3b8"
              fontSize={11}
            />
            <YAxis
              type="number"
              dataKey={y_keys[0]}
              name={y_keys[0]}
              stroke="#94a3b8"
              fontSize={11}
            />
            <ZAxis range={[40, 40]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={data} fill={PALETTE[0]} fillOpacity={0.6} />
          </ScatterChart>
        </ResponsiveContainer>
      );

    case "histogram":
    case "bar":
    default:
      return (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey={x_key}
              stroke="#94a3b8"
              fontSize={11}
              interval={0}
              angle={data.length > 6 ? -30 : 0}
              textAnchor={data.length > 6 ? "end" : "middle"}
              height={data.length > 6 ? 70 : 30}
            />
            <YAxis stroke="#94a3b8" fontSize={11} />
            <Tooltip />
            {y_keys.map((k, i) => (
              <Bar
                key={k}
                dataKey={k}
                radius={[4, 4, 0, 0]}
                fill={PALETTE[i % PALETTE.length]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      );
  }
}

export default function ChartRenderer({ spec }) {
  return (
    <div className="chart-card">
      <h3 className="chart-title">{spec.title}</h3>
      <p className="chart-desc">{spec.description}</p>
      {spec.type === "heatmap" ? (
        <Heatmap spec={spec} />
      ) : (
        <ChartBody spec={spec} />
      )}
    </div>
  );
}
