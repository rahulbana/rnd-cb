import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

function CopyButton({ text, label = "Copy" }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <button className="btn-ghost" onClick={copy} type="button">
      {copied ? "Copied!" : label}
    </button>
  );
}

export default function ResultView({ result }) {
  if (!result) return null;

  const fullText = `${result.title}\n\n${result.body}\n\n${(result.hashtags || []).join(" ")}`;
  const verification = result.verification || {};

  return (
    <div className="card result">
      <div className="result-head">
        <h2 className="result-title">{result.title}</h2>
        <CopyButton text={fullText} label="Copy all" />
      </div>

      {result.trending_topic && (
        <div className="trend-pill">📈 Trending angle: {result.trending_topic}</div>
      )}

      {verification && (
        <div className={`verify-banner ${verification.approved ? "ok" : "warn"}`}>
          <strong>{verification.approved ? "✓ Verified" : "⚠ Needs review"}</strong>
          {typeof verification.score === "number" && verification.score > 0 && (
            <span> · Quality score {Math.round(verification.score)}/100</span>
          )}
          {verification.notes && <span className="verify-notes"> — {verification.notes}</span>}
          {verification.issues && verification.issues.length > 0 && (
            <ul className="verify-issues">
              {verification.issues.map((iss, i) => (
                <li key={i}>{iss}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="block">
        <div className="block-head">
          <h4>Content</h4>
          <CopyButton text={result.body} />
        </div>
        <div className="markdown">
          <ReactMarkdown>{result.body}</ReactMarkdown>
        </div>
      </div>

      <div className="block">
        <h4>Meta description</h4>
        <p className="muted">{result.description}</p>
      </div>

      <div className="grid-2">
        <div className="block">
          <h4>Keywords</h4>
          <div className="tag-row">
            {(result.keywords || []).map((k, i) => (
              <span key={i} className="tag">
                {k}
              </span>
            ))}
          </div>
        </div>
        <div className="block">
          <div className="block-head">
            <h4>Hashtags</h4>
            <CopyButton text={(result.hashtags || []).join(" ")} />
          </div>
          <div className="tag-row">
            {(result.hashtags || []).map((h, i) => (
              <span key={i} className="tag tag-hash">
                {h}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
