import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { askQuestion } from "../api.js";

// Conversational Q&A over the loaded video's transcript.
export default function QA({ url }) {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]); // { question, answer }
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await askQuestion(url, q);
      setHistory((h) => [...h, { question: q, answer: res.answer }]);
      setQuestion("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="qa">
      <form className="qa-form" onSubmit={submit}>
        <input
          type="text"
          value={question}
          placeholder="Ask anything about this video…"
          onChange={(e) => setQuestion(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {history.length === 0 && !loading && (
        <p className="hint">
          Try: “What are the main arguments?” or “Summarize the section about X.”
        </p>
      )}

      <div className="qa-history">
        {history
          .slice()
          .reverse()
          .map((item, i) => (
            <div className="qa-item" key={history.length - i}>
              <div className="qa-question">{item.question}</div>
              <div className="qa-answer markdown">
                <ReactMarkdown>{item.answer}</ReactMarkdown>
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
