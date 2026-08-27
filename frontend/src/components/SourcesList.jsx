export default function SourcesList({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="sources">
      <h3 className="sources__title">Sources ({sources.length})</h3>
      <ol className="sources__list">
        {sources.map((s, i) => (
          <li key={i} className="sources__item">
            <a href={s.url} target="_blank" rel="noopener noreferrer">
              {s.title || s.url}
            </a>
            {s.provider && <span className="sources__provider">{s.provider}</span>}
          </li>
        ))}
      </ol>
    </div>
  );
}
