import React from "react";

// Human-readable labels for each pipeline step, keyed by phase.
export const STEP_LABELS = {
  ingest: {
    upload: "Upload",
    parse: "Parse document",
    chunk: "Chunk",
    embed: "Embed",
    index: "Index",
    complete: "Ready",
  },
  chat: {
    embed_query: "Embed query",
    retrieve: "Retrieve",
    rerank: "Rerank",
    generate: "Generate",
    complete: "Done",
  },
};

const ICONS = { start: "◐", progress: "◐", done: "●", error: "✕", pending: "○" };

// steps: ordered array of { step, status, detail } accumulated from events.
export default function StepTimeline({ phase, steps }) {
  const labels = STEP_LABELS[phase] || {};
  const order = Object.keys(labels);
  // Latest status per step.
  const byStep = {};
  for (const s of steps) byStep[s.step] = s;

  return (
    <ol className="timeline">
      {order.map((key) => {
        const s = byStep[key];
        const status = s ? s.status : "pending";
        return (
          <li key={key} className={`timeline-item ${status}`}>
            <span className="timeline-icon">{ICONS[status] || "○"}</span>
            <span className="timeline-label">{labels[key]}</span>
            {s && s.detail && <span className="timeline-detail">{s.detail}</span>}
          </li>
        );
      })}
    </ol>
  );
}
