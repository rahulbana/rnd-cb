import { useCallback, useRef, useState } from "react";
import { analyzeResume } from "./api.js";
import Results from "./Results.jsx";

export default function App() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const pickFile = (f) => {
    setError("");
    setResult(null);
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Please choose a PDF file.");
      return;
    }
    setFile(f);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    pickFile(e.dataTransfer.files?.[0]);
  }, []);

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await analyzeResume(file);
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="page">
      <header className="header">
        <h1>AI Resume Analyzer</h1>
        <p>Upload your resume as a PDF to get instant, AI-generated feedback.</p>
      </header>

      <section
        className={`dropzone${dragging ? " dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          hidden
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
        <div className="dropzone-inner">
          <div className="upload-icon">📄</div>
          {file ? (
            <p className="filename">{file.name}</p>
          ) : (
            <>
              <p className="strong">Drop your PDF here</p>
              <p className="muted">or click to browse</p>
            </>
          )}
        </div>
      </section>

      <div className="actions">
        <button className="btn primary" onClick={submit} disabled={!file || loading}>
          {loading ? "Analyzing…" : "Analyze resume"}
        </button>
        {(file || result) && (
          <button className="btn ghost" onClick={reset} disabled={loading}>
            Clear
          </button>
        )}
      </div>

      {error && <div className="alert error">{error}</div>}

      {loading && (
        <div className="loading">
          <div className="spinner" />
          <p>Reading your resume and generating feedback…</p>
        </div>
      )}

      {result && <Results data={result} />}

      <footer className="footer">
        <span>Built with FastAPI, React &amp; OpenAI.</span>
      </footer>
    </div>
  );
}
