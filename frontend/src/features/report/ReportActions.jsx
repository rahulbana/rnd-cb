import React, { useState } from "react";

import { downloadMarkdown, timestamp } from "../../utils/format";

export default function ReportActions({ report }) {
  const [copied, setCopied] = useState(false);
  const disabled = !report;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(report);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const download = () => {
    downloadMarkdown(report, `deep-search-report-${timestamp()}.md`);
  };

  return (
    <div className="report-actions">
      <button
        type="button"
        className="btn-ghost"
        onClick={copy}
        disabled={disabled}
        title="Copy report as Markdown"
      >
        {copied ? "✓ Copied" : "📋 Copy"}
      </button>
      <button
        type="button"
        className="btn-ghost"
        onClick={download}
        disabled={disabled}
        title="Download report as .md"
      >
        ⬇️ Download .md
      </button>
    </div>
  );
}
