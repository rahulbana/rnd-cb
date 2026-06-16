import React from "react";

// Shows each agent and its live status: pending / working / done.
export default function AgentTimeline({ agents, statuses }) {
  if (!agents.length) return null;

  const done = agents.filter((a) => statuses[a.id] === "done").length;
  const pct = Math.round((done / agents.length) * 100);

  return (
    <div className="card timeline">
      <div className="timeline-head">
        <h3 className="timeline-title">🤖 Multi-Agent Pipeline</h3>
        <span className="timeline-count">
          {done}/{agents.length}
        </span>
      </div>

      <div
        className="progress"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>

      <ul className="agent-list">
        {agents.map((agent) => {
          const status = statuses[agent.id] || "pending";
          return (
            <li key={agent.id} className={`agent-row agent-${status}`}>
              <span className="agent-dot" aria-hidden="true">
                {status === "done" ? (
                  "✓"
                ) : status === "working" ? (
                  <span className="spinner" />
                ) : (
                  ""
                )}
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
