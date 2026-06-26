import React from "react";

import { EVENT_TYPES, NODE_LABELS } from "../../constants/events";

function iconForEvent(ev) {
  switch (ev.type) {
    case EVENT_TYPES.RUN_START:
      return "🚀";
    case EVENT_TYPES.NODE_START:
      return "▶️";
    case EVENT_TYPES.NODE_END:
      return "✅";
    case EVENT_TYPES.TOOL_CALL:
      return ev.tool === "llm" ? "🤖" : "🔧";
    case EVENT_TYPES.TOOL_RESULT:
      return "📥";
    case EVENT_TYPES.TOOL_ERROR:
      return "⚠️";
    default:
      return "•";
  }
}

function textForEvent(ev) {
  if (ev.type === EVENT_TYPES.RUN_START) return `Started research: "${ev.query}"`;
  if (ev.detail) return ev.detail;
  if (ev.type === EVENT_TYPES.NODE_START)
    return `Entering ${NODE_LABELS[ev.node] || ev.node}`;
  if (ev.type === EVENT_TYPES.NODE_END)
    return `Finished ${NODE_LABELS[ev.node] || ev.node}`;
  return ev.type;
}

export default function EventItem({ event }) {
  return (
    <li className={`event event-${event.type}`}>
      <span className="event-icon">{iconForEvent(event)}</span>
      <span className="event-text">
        {textForEvent(event)}
        {event.tool && event.tool !== "llm" && (
          <span className="tool-tag">{event.tool}</span>
        )}
        {event.tool === "llm" && event.model && (
          <span className="tool-tag model">{event.model}</span>
        )}
      </span>
    </li>
  );
}
