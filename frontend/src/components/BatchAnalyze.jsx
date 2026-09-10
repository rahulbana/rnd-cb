import { useRef, useState } from "react";
import { analyzeBatch, analyzeCsv } from "../lib/api.js";
import Dashboard from "./Dashboard.jsx";

const EXAMPLE = `The product is excellent but delivery was very slow.
Absolutely love it, works perfectly and shipping was fast!
Terrible experience, the item arrived broken and support was rude.
It's okay, nothing special but does the job.
Great quality for the price, would recommend to friends.`;

export default function BatchAnalyze() {
  const [text, setText] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const [fileName, setFileName] = useState("");
  const fileInput = useRef(null);

  async function runText() {
    const lines = text
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (!lines.length) return;
    await run(() => analyzeBatch(lines), "");
  }

  async function runCsv(file) {
    if (!file) return;
    setFileName(file.name);
    await run(() => analyzeCsv(file), "");
  }

  async function run(fn) {
    setLoading(true);
    setError("");
    setData(null);
    try {
      setData(await fn());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDrag(false);
    const file = e.dataTransfer.files?.[0];
    if (file) runCsv(file);
  }

  return (
    <div>
      <div className="card">
        <div className="section-title">Batch analysis — one text per line</div>
        <textarea
          rows={6}
          value={text}
          placeholder={"Paste multiple texts, one per line…"}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="row" style={{ marginTop: 12 }}>
          <button
            className="btn"
            onClick={runText}
            disabled={loading || !text.trim()}
          >
            {loading && <span className="spinner" />}
            {loading ? "Analyzing…" : "Analyze batch"}
          </button>
          <button className="example-btn" onClick={() => setText(EXAMPLE)}>
            Use example
          </button>
        </div>
      </div>

      <div className="card">
        <div className="section-title">Or upload a CSV file</div>
        <div
          className={`dropzone ${drag ? "drag" : ""}`}
          onClick={() => fileInput.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
        >
          <div className="big">📄 Drop a CSV here or click to browse</div>
          <p className="hint">
            Uses a column named text / review / comment / content / message,
            otherwise the first column. {fileName && <b>Selected: {fileName}</b>}
          </p>
          <input
            ref={fileInput}
            type="file"
            accept=".csv"
            hidden
            onChange={(e) => runCsv(e.target.files?.[0])}
          />
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {data && (
        <div style={{ marginTop: 18 }}>
          <Dashboard summary={data.summary} results={data.results} />
        </div>
      )}
    </div>
  );
}
