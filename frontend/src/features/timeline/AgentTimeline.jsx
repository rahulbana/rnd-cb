import React from "react";

import EventItem from "./EventItem";

export default function AgentTimeline({ events, subqueries, running }) {
  return (
    <div className="panel timeline">
      <div className="panel-header">
        <h2>Agent Activity</h2>
        {running && (
          <span className="live-dot" title="Running">
            live
          </span>
        )}
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
          <EventItem key={i} event={ev} />
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
