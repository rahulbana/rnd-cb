import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function Report({ report, running }) {
  const [copied, setCopied] = useState(false);

  const copyReport = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const downloadReport = () => {
    const blob = new Blob([report], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    a.download = `deep-search-report-${stamp}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!report && !running) {
    return (
      <div className="panel report empty-report">
        <p>
          Enter a question above. The agent will plan multiple search queries,
          search the web, and synthesize a cited report here.
        </p>
      </div>
    );
  }

  return (
    <div className="panel report">
      <div className="panel-header">
        <h2>Report</h2>
        <div className="report-actions">
          <button
            type="button"
            className="btn-ghost"
            onClick={copyReport}
            disabled={!report}
            title="Copy report as Markdown"
          >
            {copied ? "✓ Copied" : "📋 Copy"}
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={downloadReport}
            disabled={!report}
            title="Download report as .md"
          >
            ⬇️ Download .md
          </button>
        </div>
      </div>
      <div className="markdown">
        {report ? (
          <ReactMarkdown>{report}</ReactMarkdown>
        ) : (
          <p className="muted">Waiting for synthesis…</p>
        )}
        {running && report && <span className="cursor">▋</span>}
      </div>
    </div>
  );
}
