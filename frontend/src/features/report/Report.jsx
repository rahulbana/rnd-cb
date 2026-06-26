import React from "react";
import ReactMarkdown from "react-markdown";

import ReportActions from "./ReportActions";

export default function Report({ report, running }) {
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
        <ReportActions report={report} />
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
