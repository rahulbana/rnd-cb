import React from "react";

const AGENTS = [
  { key: "researcher", name: "Trend Researcher", icon: "🔎", desc: "Scans the last 24h for trending angles & sources" },
  { key: "writer", name: "Content Writer", icon: "✍️", desc: "Drafts title, body, keywords & hashtags" },
  { key: "verifier", name: "Verifier", icon: "✅", desc: "Fact-checks against sources & polishes" },
];

export default function AgentProgress({ statuses }) {
  return (
    <div className="card progress">
      <h3 className="section-title">Multi-agent pipeline</h3>
      <div className="agent-list">
        {AGENTS.map((a) => {
          const status = statuses[a.key] || "pending";
          return (
            <div key={a.key} className={`agent-row agent-${status}`}>
              <div className="agent-icon">{a.icon}</div>
              <div className="agent-info">
                <div className="agent-name">
                  {a.name}
                  <span className={`badge badge-${status}`}>{status}</span>
                </div>
                <div className="agent-desc">{statuses[`${a.key}_label`] || a.desc}</div>
              </div>
              <div className="agent-state">
                {status === "running" && <span className="spinner" />}
                {status === "done" && <span className="check">✓</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
