import React, { useRef, useState } from "react";
import { ingestFile, ingestText } from "../api";
import StepTimeline from "./StepTimeline.jsx";

// Reduce a stream of ingestion events into an ordered step list.
function useIngestJob() {
  const [steps, setSteps] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [error, setError] = useState(null);

  const onEvent = (event) => {
    if (event.type === "step") {
      setSteps((prev) => [...prev, { step: event.step, status: event.status, detail: event.detail }]);
    } else if (event.type === "error") {
      setError(event.detail);
      setStatus("error");
    }
  };

  const reset = () => {
    setSteps([]);
    setError(null);
    setStatus("idle");
  };

  return { steps, status, setStatus, error, setError, onEvent, reset };
}

export default function Uploader({ onIngested }) {
  const fileInput = useRef(null);
  const [text, setText] = useState("");
  const [busyName, setBusyName] = useState(null);
  const job = useIngestJob();

  async function runFile(file) {
    job.reset();
    job.setStatus("running");
    setBusyName(file.name);
    try {
      await ingestFile(file, job.onEvent);
      job.setStatus("done");
      onIngested && onIngested();
    } catch (e) {
      job.setError(e.message);
      job.setStatus("error");
    } finally {
      setBusyName(null);
    }
  }

  async function runText() {
    if (!text.trim()) return;
    job.reset();
    job.setStatus("running");
    setBusyName("pasted text");
    try {
      await ingestText(text, null, job.onEvent);
      job.setStatus("done");
      setText("");
      onIngested && onIngested();
    } catch (e) {
      job.setError(e.message);
      job.setStatus("error");
    } finally {
      setBusyName(null);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) runFile(file);
  }

  return (
    <div className="panel">
      <h2>Add knowledge</h2>
      <div
        className="dropzone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => fileInput.current?.click()}
      >
        <input
          ref={fileInput}
          type="file"
          hidden
          onChange={(e) => e.target.files[0] && runFile(e.target.files[0])}
        />
        <p>📄 Drop a file or click to browse</p>
        <p className="hint">
          PDF · Word · PPT · Excel · CSV · text · PNG/JPEG (OCR)
        </p>
      </div>

      <div className="text-upload">
        <textarea
          placeholder="…or paste raw text to index"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
        />
        <button onClick={runText} disabled={job.status === "running" || !text.trim()}>
          Index text
        </button>
      </div>

      {job.status !== "idle" && (
        <div className="ingest-progress">
          <div className="progress-head">
            <strong>{busyName || "document"}</strong>
            <span className={`badge ${job.status}`}>{job.status}</span>
          </div>
          <StepTimeline phase="ingest" steps={job.steps} />
          {job.error && <div className="error-text">{job.error}</div>}
        </div>
      )}
    </div>
  );
}
