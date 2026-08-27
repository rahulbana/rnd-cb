import { useCallback, useEffect, useRef, useState } from "react";
import {
  cancelResearch,
  getResearch,
  startResearch,
  streamResearch,
} from "./api.js";
import Composer from "./components/Composer.jsx";
import ProgressTimeline from "./components/ProgressTimeline.jsx";
import ReportView from "./components/ReportView.jsx";
import SourcesList from "./components/SourcesList.jsx";

const STATUS = {
  IDLE: "idle",
  RUNNING: "running",
  COMPLETED: "completed",
  ERROR: "error",
  CANCELLED: "cancelled",
};

export default function App() {
  const [status, setStatus] = useState(STATUS.IDLE);
  const [threadId, setThreadId] = useState(null);
  const [topic, setTopic] = useState("");
  const [events, setEvents] = useState([]);
  const [report, setReport] = useState("");
  const [sources, setSources] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const esRef = useRef(null);

  const closeStream = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  useEffect(() => () => closeStream(), [closeStream]);

  const handleEvent = useCallback(
    (type, payload) => {
      setEvents((prev) => [...prev, { type, payload, at: Date.now() }]);
      if (type === "completed") {
        setReport(payload.final_report || "");
        setSources(payload.sources || []);
        setStatus(STATUS.COMPLETED);
        closeStream();
      } else if (type === "error") {
        setErrorMsg(payload.message || "The research run failed.");
        setStatus(STATUS.ERROR);
        closeStream();
      } else if (type === "cancelled") {
        setStatus(STATUS.CANCELLED);
        closeStream();
      }
    },
    [closeStream]
  );

  const onStart = useCallback(
    async (topicText) => {
      setStatus(STATUS.RUNNING);
      setTopic(topicText);
      setEvents([]);
      setReport("");
      setSources([]);
      setErrorMsg("");
      try {
        const { thread_id } = await startResearch(topicText);
        setThreadId(thread_id);
        esRef.current = streamResearch(thread_id, handleEvent);
      } catch (err) {
        setErrorMsg(err.message);
        setStatus(STATUS.ERROR);
      }
    },
    [handleEvent]
  );

  const onCancel = useCallback(async () => {
    if (threadId) await cancelResearch(threadId);
  }, [threadId]);

  const onReset = useCallback(() => {
    closeStream();
    setStatus(STATUS.IDLE);
    setThreadId(null);
    setTopic("");
    setEvents([]);
    setReport("");
    setSources([]);
    setErrorMsg("");
  }, [closeStream]);

  // Safety net: if the stream drops before completion, poll durable state once.
  useEffect(() => {
    if (status !== STATUS.RUNNING || !threadId) return;
    const id = setInterval(async () => {
      if (esRef.current) return; // stream still live
      try {
        const state = await getResearch(threadId);
        if (state.is_complete && state.final_report) {
          setReport(state.final_report);
          setSources(state.sources || []);
          setStatus(STATUS.COMPLETED);
        }
      } catch {
        /* ignore transient poll errors */
      }
    }, 4000);
    return () => clearInterval(id);
  }, [status, threadId]);

  const running = status === STATUS.RUNNING;

  return (
    <div className="app">
      <header className="app__header">
        <div className="brand">
          <span className="brand__dot" />
          <h1>Deep Research Agent</h1>
        </div>
        <p className="app__subtitle">
          Autonomous multi-step research · LangGraph · OpenAI · Tavily → DuckDuckGo
        </p>
      </header>

      <main className="app__main">
        <Composer
          onStart={onStart}
          onCancel={onCancel}
          onReset={onReset}
          status={status}
        />

        {errorMsg && status === STATUS.ERROR && (
          <div className="banner banner--error">⚠ {errorMsg}</div>
        )}
        {status === STATUS.CANCELLED && (
          <div className="banner banner--warn">Run cancelled.</div>
        )}

        {(running || events.length > 0) && (
          <section className="panel">
            <h2 className="panel__title">
              {running ? "Researching…" : "Research trace"}
              {topic && <span className="panel__topic">“{topic}”</span>}
            </h2>
            <ProgressTimeline events={events} running={running} />
          </section>
        )}

        {report && (
          <section className="panel panel--report">
            <h2 className="panel__title">Report</h2>
            <ReportView markdown={report} />
            <SourcesList sources={sources} />
          </section>
        )}
      </main>

      <footer className="app__footer">
        State is checkpointed to Postgres — long runs survive restarts and are
        resumable by thread id.
      </footer>
    </div>
  );
}
