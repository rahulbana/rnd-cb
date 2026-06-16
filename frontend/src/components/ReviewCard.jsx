const TYPE_LABELS = {
  reader: "Reader",
  critic: "Critic",
  company: "Company",
  celebrity: "Celebrity",
  unknown: "Source",
};

export default function ReviewCard({ review }) {
  const {
    reviewer_name,
    reviewer_type,
    source,
    source_url,
    rating,
    sentiment,
    excerpt,
  } = review;

  return (
    <article className="review-card">
      <header className="review-head">
        <span className={`badge type-${reviewer_type}`}>
          {TYPE_LABELS[reviewer_type] ?? reviewer_type}
        </span>
        <span className="reviewer-name">{reviewer_name}</span>
        {rating != null && <span className="rating">{rating}/5</span>}
        <span className={`sentiment sentiment-${sentiment}`}>{sentiment}</span>
      </header>
      {excerpt && <blockquote className="excerpt">“{excerpt}”</blockquote>}
      {source_url && (
        <a className="source-link" href={source_url} target="_blank" rel="noreferrer">
          {source || source_url}
        </a>
      )}
    </article>
  );
}
