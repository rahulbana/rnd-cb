function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function HistoryPanel({ items, onSelect, onDelete, onClear }) {
  return (
    <div className="panel">
      <h2>Query History</h2>

      {items.length === 0 ? (
        <p className="empty">No queries yet. Generated queries appear here.</p>
      ) : (
        <>
          <div style={{ marginBottom: 10 }}>
            <button className="link-btn" onClick={onClear}>
              Clear all
            </button>
          </div>
          {items.map((item) => (
            <div
              key={item.id}
              className="history-item"
              onClick={() => onSelect(item)}
              title="Load this query"
            >
              <div className="q">{item.question}</div>
              <div className="meta">
                <span>{item.dialect}</span>
                <span>
                  {item.valid ? "✓" : "✗"} · {formatTime(item.created_at)}
                </span>
              </div>
              <div style={{ marginTop: 6 }}>
                <button
                  className="link-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(item.id);
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
