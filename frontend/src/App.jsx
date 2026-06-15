import React, { useRef, useState } from "react";
import { streamSearch } from "./api.js";
import SearchBox from "./components/SearchBox.jsx";
import AgentTimeline from "./components/AgentTimeline.jsx";
import ResourceList from "./components/ResourceList.jsx";
import Report from "./components/Report.jsx";

export default function App() {
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState([]);
  const [subqueries, setSubqueries] = useState([]);
  const [sources, setSources] = useState([]);
  const [report, setReport] = useState("");
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const reset = () => {
    setEvents([]);
    setSubqueries([]);
    setSources([]);
    setReport("");
    setError(null);
  };

  const handleEvent = (ev) => {
    // Keep a log of meaningful activity events for the timeline.
    if (
      ["run_start", "node_start", "node_end", "tool_call", "tool_result", "tool_error"].includes(
        ev.type
      )
    ) {
      setEvents((prev) => [...prev, ev]);
    }

    switch (ev.type) {
      case "subqueries":
        setSubqueries(ev.subqueries || []);
        break;
      case "source":
        setSources((prev) => {
          if (prev.some((s) => s.url === ev.source.url)) return prev;
          return [...prev, ev.source];
        });
        break;
      case "token":
        setReport((prev) => prev + ev.text);
        break;
      case "report":
        if (ev.report) setReport(ev.report);
        if (ev.sources) setSources(ev.sources);
        break;
      case "error":
        setError(ev.error);
        break;
      default:
        break;
    }
  };

  const onSubmit = async (query, numSubqueries) => {
    if (!query.trim() || running) return;
    reset();
    setRunning(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamSearch({
        query,
        numSubqueries,
        onEvent: handleEvent,
        signal: controller.signal,
      });
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message);
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  };

  const onCancel = () => {
    abortRef.current?.abort();
    setRunning(false);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔎 Deep Search Agent</h1>
        <p className="subtitle">
          LangGraph · OpenAI · multi-query web research with live agent activity
        </p>
      </header>

      <SearchBox onSubmit={onSubmit} running={running} onCancel={onCancel} />

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
