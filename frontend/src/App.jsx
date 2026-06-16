import { useState } from "react";
import { rateText, rateFile } from "./api.js";
import Results from "./Results.jsx";

const SAMPLE_JD = `Senior Backend Engineer
- 5+ years building Python web services (FastAPI/Django)
- Strong with PostgreSQL, Redis, and async programming
- Experience with Docker, Kubernetes, and CI/CD
- Bonus: LLM/OpenAI integration experience`;

export default function App() {
  const [jobDescription, setJobDescription] = useState("");
  const [resume, setResume] = useState("");
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("text"); // "text" | "file"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const canSubmit =
    jobDescription.trim() &&
    (mode === "text" ? resume.trim() : file) &&
    !loading;

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const data =
        mode === "file"
          ? await rateFile(file, jobDescription)
          : await rateText(resume, jobDescription);
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>📄 Resume Rater</h1>
        <p>Score a resume against a job description, powered by AI.</p>
      </header>

      <form className="card" onSubmit={onSubmit}>
        <label className="field">
          <div className="field-head">
            <span>Job Description</span>
            <button
              type="button"
              className="link"
              onClick={() => setJobDescription(SAMPLE_JD)}
            >
              use sample
            </button>
          </div>
          <textarea
            rows={8}
            placeholder="Paste the job description here…"
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
          />
        </label>

        <div className="tabs">
          <button
            type="button"
            className={mode === "text" ? "tab active" : "tab"}
            onClick={() => setMode("text")}
          >
            Paste resume
          </button>
          <button
            type="button"
            className={mode === "file" ? "tab active" : "tab"}
            onClick={() => setMode("file")}
          >
            Upload file
          </button>
        </div>

        {mode === "text" ? (
          <label className="field">
            <span>Resume</span>
            <textarea
              rows={10}
              placeholder="Paste the resume text here…"
              value={resume}
              onChange={(e) => setResume(e.target.value)}
            />
          </label>
        ) : (
          <label className="field">
            <span>Resume file (PDF or .txt)</span>
            <input
              type="file"
              accept=".pdf,.txt,text/plain,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        )}

        {error && <div className="error">{error}</div>}

        <button className="submit" type="submit" disabled={!canSubmit}>
          {loading ? "Rating…" : "Rate Resume"}
        </button>
      </form>

      {result && <Results data={result} />}
    </div>
  );
}
