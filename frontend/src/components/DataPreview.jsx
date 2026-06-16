export default function DataPreview({ rows, columns }) {
  if (!rows || rows.length === 0) {
    return <p className="hint">No sample rows available.</p>;
  }
  const headers = columns.map((c) => c.name);

  return (
    <section className="data-preview">
      <p className="hint">First {rows.length} rows as the agent parsed them.</p>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {headers.map((h) => (
                  <td key={h}>
                    {row[h] === null || row[h] === undefined ? (
                      <span className="null-cell">null</span>
                    ) : (
                      String(row[h])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
