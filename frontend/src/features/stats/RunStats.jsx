import React from "react";

export default function RunStats({ stats }) {
  if (!stats) return null;

  const items = [
    { label: "Duration", value: `${(stats.durationMs / 1000).toFixed(1)}s` },
    { label: "Sub-queries", value: stats.subqueries },
    { label: "Sources", value: stats.sources },
    { label: "Report", value: `${stats.reportChars.toLocaleString()} chars` },
  ];

  return (
    <div className="run-stats">
      {items.map((it) => (
        <div className="stat" key={it.label}>
          <span className="stat-value">{it.value}</span>
          <span className="stat-label">{it.label}</span>
        </div>
      ))}
    </div>
  );
}
