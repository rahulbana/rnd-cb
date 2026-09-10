export default function ValidationBadges({ validation }) {
  if (!validation) return null;
  const { valid, read_only, statement_type, errors, warnings } = validation;

  return (
    <div>
      <div className="badges">
        <span className={`badge ${valid ? "good" : "bad"}`}>
          {valid ? "✓ Valid SQL" : "✗ Invalid SQL"}
        </span>
        <span className={`badge ${read_only ? "good" : "bad"}`}>
          {read_only ? "🔒 Read-only" : "⚠ Not read-only"}
        </span>
        {statement_type && <span className="badge info">{statement_type}</span>}
      </div>

      {errors?.length > 0 && (
        <ul className="msg-list errors">
          {errors.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
      {warnings?.length > 0 && (
        <ul className="msg-list warnings">
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
