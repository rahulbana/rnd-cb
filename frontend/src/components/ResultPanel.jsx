import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ResultPanel({ loading, error, result, actionLabel }) {
  if (loading) {
    return (
      <div className="result-panel">
        <div className="spinner" />
        <p className="muted">Analyzing your code…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="result-panel">
        <div className="error-box">
          <strong>Something went wrong</strong>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="result-panel empty">
        <p className="muted">
          Paste some code on the left, pick an action, and the explanation will
          appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="result-panel">
      {actionLabel && <div className="result-badge">{actionLabel}</div>}
      <div className="markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
      </div>
    </div>
  );
}
