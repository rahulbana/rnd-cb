import { useState } from "react";

function num(v) {
  if (v === null || v === undefined) return "—";
  return typeof v === "number" ? Number(v.toFixed(3)).toLocaleString() : v;
}

function ColumnRow({ col }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <tr className="col-row" onClick={() => setOpen((o) => !o)}>
        <td className="col-name">
          <span className="caret">{open ? "▾" : "▸"}</span>
          {col.name}
        </td>
        <td>
          <span className={`type-chip t-${col.semantic_type}`}>
            {col.semantic_type}
          </span>
        </td>
        <td>{num(col.count)}</td>
        <td className={col.missing_pct > 10 ? "warn-text" : ""}>
          {col.missing_pct}%
        </td>
        <td>{num(col.unique)}</td>
        <td>{num(col.mean)}</td>
        <td>{num(col.min)}</td>
        <td>{num(col.max)}</td>
      </tr>
      {open && (
        <tr className="col-detail">
          <td colSpan={8}>
            <div className="detail-grid">
              {col.median != null && (
                <span>median: <b>{num(col.median)}</b></span>
              )}
              {col.std != null && <span>std: <b>{num(col.std)}</b></span>}
              {col.q1 != null && <span>Q1: <b>{num(col.q1)}</b></span>}
              {col.q3 != null && <span>Q3: <b>{num(col.q3)}</b></span>}
              {col.skew != null && <span>skew: <b>{num(col.skew)}</b></span>}
              {col.outlier_count != null && (
                <span>outliers: <b>{col.outlier_count}</b></span>
              )}
              {col.true_count != null && (
                <span>
                  true/false: <b>{col.true_count}/{col.false_count}</b>
                </span>
              )}
              {col.avg_length != null && (
                <span>avg length: <b>{num(col.avg_length)}</b></span>
              )}
              {col.min_date && (
                <span>range: <b>{col.min_date} → {col.max_date}</b></span>
              )}
            </div>
            {col.top_values.length > 0 && (
              <div className="top-values">
                <span className="tv-label">Top values:</span>
                {col.top_values.slice(0, 6).map((tv, i) => (
                  <span key={i} className="tv-chip">
                    {tv.value} <em>({tv.count})</em>
                  </span>
                ))}
              </div>
            )}
            {col.notes.length > 0 && (
              <ul className="col-notes">
                {col.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function ColumnTable({ columns }) {
  return (
    <section className="column-table-wrap">
      <p className="hint">Click any column to expand its full profile.</p>
      <table className="column-table">
        <thead>
          <tr>
            <th>Column</th>
            <th>Type</th>
            <th>Count</th>
            <th>Missing</th>
            <th>Unique</th>
            <th>Mean</th>
            <th>Min</th>
            <th>Max</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((c) => (
            <ColumnRow key={c.name} col={c} />
          ))}
        </tbody>
      </table>
    </section>
  );
}
