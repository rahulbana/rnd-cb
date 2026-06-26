import React from "react";

import ResourceItem from "./ResourceItem";

export default function ResourceList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="panel resources">
      <div className="panel-header">
        <h2>Resources ({sources.length})</h2>
      </div>
      <ol className="resource-list">
        {sources.map((s, i) => (
          <ResourceItem key={s.url || i} source={s} index={i} />
        ))}
      </ol>
    </div>
  );
}
