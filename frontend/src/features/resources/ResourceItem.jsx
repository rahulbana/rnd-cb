import React from "react";

import { hostname } from "../../utils/format";

export default function ResourceItem({ source, index }) {
  return (
    <li className="resource">
      <span className="resource-index">[{index + 1}]</span>
      <div className="resource-body">
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="resource-title"
        >
          {source.title || source.url}
        </a>
        <div className="resource-meta">
          <span className="resource-host">{hostname(source.url)}</span>
          {source.subquery && <span className="resource-subq">↳ {source.subquery}</span>}
        </div>
        {source.content && (
          <p className="resource-snippet">{source.content.slice(0, 220)}…</p>
        )}
      </div>
    </li>
  );
}
