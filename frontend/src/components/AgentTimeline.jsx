import React from "react";

const NODE_LABELS = {
  plan_queries: "🧭 Plan",
  search: "🌐 Search",
  synthesize: "✍️ Synthesize",
};

function iconForEvent(ev) {
  switch (ev.type) {
    case "run_start":
      return "🚀";
    case "node_start":
      return "▶️";
    case "node_end":
      return "✅";
    case "tool_call":
      return ev.tool === "llm" ? "🤖" : "🔧";
    case "tool_result":
      return "📥";
    case "tool_error":
      return "⚠️";
    default:
      return "•";
  }
}

function textForEvent(ev) {
  if (ev.type === "run_start") return `Started research: "${ev.query}"`;
  if (ev.detail) return ev.detail;
  if (ev.type === "node_start") return `Entering ${NODE_LABELS[ev.node] || ev.node}`;
  if (ev.type === "node_end") return `Finished ${NODE_LABELS[ev.node] || ev.node}`;
  return ev.type;
}

export default function AgentTimeline({ events, subqueries, running }) {
  return (
    <div className="panel timeline">
      <div className="panel-header">
        <h2>Agent Activity</h2>
        {running && <span className="live-dot" title="Running">live</span>}
      </div>

      {subqueries.length > 0 && (
        <div className="subqueries">
          <h3>Generated sub-queries</h3>
          <ol>
            {subqueries.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ol>
        </div>
      )}

      <ul className="event-log">
        {events.length === 0 && !running && (
          <li className="empty">No activity yet. Ask a question to begin.</li>
        )}
        {events.map((ev, i) => (
          <li key={i} className={`event event-${ev.type}`}>
            <span className="event-icon">{iconForEvent(ev)}</span>
            <span className="event-text">
              {textForEvent(ev)}
              {ev.tool && ev.tool !== "llm" && (
                <span className="tool-tag">{ev.tool}</span>
              )}
              {ev.tool === "llm" && ev.model && (
                <span className="tool-tag model">{ev.model}</span>
              )}
            </span>
          </li>
        ))}
        {running && (
          <li className="event event-pending">
            <span className="spinner" /> working…
          </li>
        )}
      </ul>
    </div>
  );
}
