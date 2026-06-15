import React from "react";

// Shows each agent and its live status: pending / working / done.
export default function AgentTimeline({ agents, statuses }) {
  if (!agents.length) return null;

  return (
    <div className="card timeline">
      <h3 className="timeline-title">🤖 Multi-Agent Pipeline</h3>
      <ul className="agent-list">
        {agents.map((agent) => {
          const status = statuses[agent.id] || "pending";
          return (
            <li key={agent.id} className={`agent-row agent-${status}`}>
              <span className="agent-dot" aria-hidden="true">
                {status === "done" ? "✓" : status === "working" ? "" : ""}
              </span>
              <span className="agent-label">{agent.label}</span>
              <span className="agent-status">{status}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
