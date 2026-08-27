import { useState } from "react";

const EXAMPLES = [
  "What are the current best practices for RAG evaluation in production?",
  "Compare vLLM vs TGI for self-hosted LLM inference in 2025.",
  "State of agentic AI frameworks: LangGraph vs OpenAI Agents SDK vs CrewAI.",
];

export default function Composer({ onStart, onCancel, onReset, status }) {
  const [value, setValue] = useState("");
  const running = status === "running";
  const finished = ["completed", "error", "cancelled"].includes(status);

  const submit = (e) => {
    e.preventDefault();
    const topic = value.trim();
    if (topic.length >= 5 && !running) onStart(topic);
  };

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        className="composer__input"
        placeholder="Ask a deep research question…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={running}
        rows={3}
      />
      <div className="composer__row">
        <div className="composer__examples">
          {EXAMPLES.map((ex) => (
            <button
              type="button"
              key={ex}
              className="chip"
              disabled={running}
              onClick={() => setValue(ex)}
            >
              {ex.length > 42 ? ex.slice(0, 42) + "…" : ex}
            </button>
          ))}
        </div>
        <div className="composer__actions">
          {running ? (
            <button type="button" className="btn btn--danger" onClick={onCancel}>
              Stop
            </button>
          ) : finished ? (
            <button type="button" className="btn btn--ghost" onClick={onReset}>
              New research
            </button>
          ) : null}
          <button
            type="submit"
            className="btn btn--primary"
            disabled={running || value.trim().length < 5}
          >
            {running ? "Running…" : "Start research"}
          </button>
        </div>
      </div>
    </form>
  );
}
