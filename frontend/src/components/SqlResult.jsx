import { useState } from "react";
import ValidationBadges from "./ValidationBadges.jsx";

export default function SqlResult({ result, onFormat, onExplain, busy }) {
  const [copied, setCopied] = useState(false);

  if (!result) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard may be unavailable */
    }
  };

  return (
    <div className="panel">
      <h2>Generated SQL</h2>
      <pre className="sql">{result.sql}</pre>

      <div className="toolbar">
        <button className="btn small secondary" onClick={copy}>
          {copied ? "Copied!" : "Copy"}
        </button>
        <button className="btn small secondary" onClick={onFormat} disabled={busy}>
          Re-format
        </button>
        <button className="btn small secondary" onClick={onExplain} disabled={busy}>
          Explain again
        </button>
      </div>

      <ValidationBadges validation={result.validation} />

      {result.tables_used?.length > 0 && (
        <>
          <label style={{ marginTop: 8 }}>Tables used</label>
          <div className="chips">
            {result.tables_used.map((t) => (
              <span className="chip" key={t}>
                {t}
              </span>
            ))}
          </div>
        </>
      )}

      {result.assumptions?.length > 0 && (
        <ul className="msg-list warnings" style={{ marginTop: 10 }}>
          {result.assumptions.map((a, i) => (
            <li key={i}>Assumption: {a}</li>
          ))}
        </ul>
      )}

      {result.explanation && (
        <>
          <h2 style={{ marginTop: 18 }}>Explanation</h2>
          <div className="explanation">{result.explanation}</div>
        </>
      )}
    </div>
  );
}
