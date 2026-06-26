import React, { useState } from "react";

import { useDeepSearch } from "./hooks/useDeepSearch";
import SearchBox from "./features/search/SearchBox";
import AgentTimeline from "./features/timeline/AgentTimeline";
import ResourceList from "./features/resources/ResourceList";
import Report from "./features/report/Report";
import RunStats from "./features/stats/RunStats";
import RunsDashboard from "./features/runs/RunsDashboard";

function SearchView() {
  const { running, events, subqueries, sources, report, stats, error, start, cancel } =
    useDeepSearch();

  return (
    <>
      <SearchBox onSubmit={start} running={running} onCancel={cancel} />
      {error && <div className="error-banner">⚠️ {error}</div>}
      <div className="layout">
        <aside className="sidebar">
          <AgentTimeline events={events} subqueries={subqueries} running={running} />
        </aside>
        <main className="main">
          <RunStats stats={stats} />
          <Report report={report} running={running} />
          <ResourceList sources={sources} />
        </main>
      </div>
    </>
  );
}

export default function App() {
  const [view, setView] = useState("search");

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-row">
          <div>
            <h1>🔎 Deep Search Agent</h1>
            <p className="subtitle">
              LangGraph · OpenAI · multi-query web research with live agent activity
            </p>
          </div>
          <nav className="nav">
            <button
              className={`nav-btn ${view === "search" ? "active" : ""}`}
              onClick={() => setView("search")}
            >
              Search
            </button>
            <button
              className={`nav-btn ${view === "history" ? "active" : ""}`}
              onClick={() => setView("history")}
            >
              History
            </button>
          </nav>
        </div>
      </header>

      {view === "search" ? <SearchView /> : <RunsDashboard />}
    </div>
  );
}
