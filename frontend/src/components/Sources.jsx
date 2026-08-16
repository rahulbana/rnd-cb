import React, { useState } from "react";
import { deleteSource } from "../api";

export default function Sources({ sources, totalChunks, onChange }) {
  const [open, setOpen] = useState(false); // collapsed by default

  async function remove(src) {
    await deleteSource(src);
    onChange && onChange();
  }

  return (
    <div className="disclosure">
      <button className="disclosure-head" onClick={() => setOpen((o) => !o)}>
        <span className="disclosure-title">
          🗂 Documents
          <span className="disclosure-count">{sources.length}</span>
        </span>
        <span className="disclosure-caret">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="disclosure-body">
          {sources.length === 0 ? (
            <p className="hint">Nothing indexed yet. Attach a file in the chat.</p>
          ) : (
            <>
              <ul className="source-list">
                {sources.map((s) => (
                  <li key={s.source}>
                    <span className="source-name" title={s.source}>{s.source}</span>
                    <span className="muted">{s.chunks}</span>
                    <button className="link-btn" onClick={() => remove(s.source)} title="Remove">
                      remove
                    </button>
                  </li>
                ))}
              </ul>
              <div className="source-total">{sources.length} docs · {totalChunks} chunks</div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
