import ReviewCard from "./ReviewCard.jsx";

const TYPE_ORDER = ["critic", "celebrity", "company", "reader", "unknown"];

export default function ReportView({ report, onDownload, downloading }) {
  const { book, reviews, verification, sources } = report;

  // Group reviews by reviewer type for a tidy, sectioned layout.
  const grouped = TYPE_ORDER.map((type) => ({
    type,
    items: reviews.filter((r) => r.reviewer_type === type),
  })).filter((g) => g.items.length > 0);

  return (
    <section className="report">
      <div className="report-head">
        <div>
          <h2>{book.title}</h2>
          <p className="byline">
            by {book.author}
            {book.published_year ? ` · ${book.published_year}` : ""}
          </p>
          {book.genres?.length > 0 && (
            <div className="genres">
              {book.genres.map((g) => (
                <span key={g} className="genre">
                  {g}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="downloads">
          <button onClick={() => onDownload("markdown")} disabled={downloading}>
            ⬇ Markdown
          </button>
          <button onClick={() => onDownload("pdf")} disabled={downloading}>
            ⬇ PDF
          </button>
        </div>
      </div>

      {book.summary && (
        <div className="summary">
          <h3>Summary</h3>
          <p>{book.summary}</p>
        </div>
      )}

      <VerificationBanner verification={verification} />

      <div className="reviews">
        <h3>Reviews ({reviews.length})</h3>
        {grouped.length === 0 && <p className="muted">No reviews found.</p>}
        {grouped.map((group) => (
          <div key={group.type} className="review-group">
            <h4 className="group-title">{group.type}</h4>
            {group.items.map((r, i) => (
              <ReviewCard key={`${r.reviewer_name}-${i}`} review={r} />
            ))}
          </div>
        ))}
      </div>

      {sources?.length > 0 && (
        <details className="sources">
          <summary>Sources ({sources.length})</summary>
          <ul>
            {sources.map((s) => (
              <li key={s}>
                <a href={s} target="_blank" rel="noreferrer">
                  {s}
                </a>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

function VerificationBanner({ verification }) {
  const { verified, confidence, notes, flagged_claims } = verification;
  const pct = Math.round((confidence ?? 0) * 100);
  return (
    <div className={`verification ${verified ? "ok" : "warn"}`}>
      <div className="verification-head">
        <strong>{verified ? "✓ Verified" : "⚠ Unverified"}</strong>
        <span className="confidence">Confidence: {pct}%</span>
      </div>
      {notes && <p className="notes">{notes}</p>}
      {flagged_claims?.length > 0 && (
        <ul className="flagged">
          {flagged_claims.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
