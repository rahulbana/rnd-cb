import React from "react";
import { deleteSource } from "../api";

export default function Sources({ sources, totalChunks, onChange }) {
  async function remove(src) {
    await deleteSource(src);
    onChange && onChange();
  }
  return (
    <div className="panel">
      <h2>
        Indexed documents{" "}
        <span className="muted">
          ({sources.length} docs · {totalChunks} chunks)
        </span>
      </h2>
      {sources.length === 0 && <p className="hint">Nothing indexed yet.</p>}
      <ul className="source-list">
        {sources.map((s) => (
          <li key={s.source}>
            <span className="source-name" title={s.source}>{s.source}</span>
            <span className="muted">{s.chunks} chunks</span>
            <button className="link-btn" onClick={() => remove(s.source)}>
              remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
