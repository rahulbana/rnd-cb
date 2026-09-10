import { useState } from "react";
import { analyzeText } from "../lib/api.js";
import ResultCard from "./ResultCard.jsx";

const EXAMPLE = "The product is excellent but delivery was very slow.";

export default function SingleAnalyze() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await analyzeText(text));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="card">
        <div className="section-title">Analyze a single piece of text</div>
        <textarea
          rows={4}
          value={text}
          placeholder="Paste a review, comment, or any text…"
          onChange={(e) => setText(e.target.value)}
        />
        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn" onClick={run} disabled={loading || !text.trim()}>
            {loading && <span className="spinner" />}
            {loading ? "Analyzing…" : "Analyze"}
          </button>
          <button className="example-btn" onClick={() => setText(EXAMPLE)}>
            Use example
          </button>
        </div>
        {error && <div className="error">{error}</div>}
      </div>

      {result && (
        <div style={{ marginTop: 18 }}>
          <ResultCard result={result} />
        </div>
      )}
    </div>
  );
}
