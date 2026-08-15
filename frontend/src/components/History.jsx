import React, { useState } from "react";
import { groupByDate } from "../history";

export default function History({ conversations, activeId, onSelect, onDelete, onRename }) {
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState("");

  const convs = conversations
    .filter((c) => (c.messageCount || 0) > 0)
    .sort((a, b) => b.updatedAt - a.updatedAt);
  const groups = groupByDate(convs);

  function commitRename(id) {
    const t = draft.trim();
    if (t) onRename(id, t);
    setEditing(null);
  }

  if (convs.length === 0) {
    return <p className="hint history-empty">No conversations yet.</p>;
  }

  return (
    <div className="history">
      {groups.map((g) => (
        <div key={g.label} className="history-group">
          <div className="history-label">{g.label}</div>
          {g.items.map((c) => (
            <div
              key={c.id}
              className={`history-item ${c.id === activeId ? "active" : ""}`}
              onClick={() => onSelect(c.id)}
              title={c.title}
            >
              {editing === c.id ? (
                <input
                  className="history-edit"
                  autoFocus
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  onBlur={() => commitRename(c.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitRename(c.id);
                    if (e.key === "Escape") setEditing(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <>
                  <span className="history-title">{c.title}</span>
                  <span className="history-actions">
                    <button
                      className="history-btn"
                      title="Rename"
                      onClick={(e) => { e.stopPropagation(); setEditing(c.id); setDraft(c.title); }}
                    >
                      ✎
                    </button>
                    <button
                      className="history-btn"
                      title="Delete"
                      onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
                    >
                      🗑
                    </button>
                  </span>
                </>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
