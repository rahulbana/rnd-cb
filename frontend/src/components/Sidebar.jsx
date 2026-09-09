import React from "react";

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  username,
  onLogout,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="new-btn" onClick={onNew}>
          + New conversation
        </button>
      </div>

      <nav className="conversation-list">
        {conversations.length === 0 && (
          <p className="empty-hint">No conversations yet.</p>
        )}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`conversation-item ${c.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(c.id)}
          >
            <span className="conversation-title" title={c.title}>
              {c.title || "New conversation"}
            </span>
            <button
              className="delete-btn"
              title="Delete conversation"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(c.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="user-badge" title={username}>
          {username}
        </span>
        <button className="logout-btn" onClick={onLogout}>
          Sign out
        </button>
      </div>
    </aside>
  );
}
