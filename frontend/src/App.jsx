import React from "react";

import { useDeepSearch } from "./hooks/useDeepSearch";
import SearchBox from "./features/search/SearchBox";
import AgentTimeline from "./features/timeline/AgentTimeline";
import ResourceList from "./features/resources/ResourceList";
import Report from "./features/report/Report";

export default function App() {
  const { running, events, subqueries, sources, report, error, start, cancel } =
    useDeepSearch();

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔎 Deep Search Agent</h1>
        <p className="subtitle">
          LangGraph · OpenAI · multi-query web research with live agent activity
        </p>
      </header>

      <SearchBox onSubmit={start} running={running} onCancel={cancel} />

      {error && <div className="error-banner">⚠️ {error}</div>}

      <div className="layout">
        <aside className="sidebar">
          <AgentTimeline events={events} subqueries={subqueries} running={running} />
        </aside>

        <main className="main">
          <Report report={report} running={running} />
          <ResourceList sources={sources} />
        </main>
      </div>
    </div>
  );
}
