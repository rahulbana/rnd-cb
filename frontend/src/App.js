/**
 * Top-level application component.
 *
 * Renders the input form (problem statement + language dropdown), calls the
 * backend pipeline, and displays the generated result. All async states
 * (loading, error, success) are handled explicitly so the UI stays honest
 * about what is happening.
 */
import React, { useEffect, useState } from "react";

import { fetchLanguages, generateCode } from "./api";
import ResultView from "./components/ResultView";

function App() {
  const [languages, setLanguages] = useState([]);
  const [language, setLanguage] = useState("");
  const [problem, setProblem] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Load the language options once on mount.
  useEffect(() => {
    let cancelled = false;
    fetchLanguages()
      .then((options) => {
        if (cancelled) return;
        setLanguages(options);
        if (options.length > 0) {
          setLanguage(options[0].value);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(`Could not load languages: ${err.message}`);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const canSubmit =
    !loading && language && problem.trim().length >= 5;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await generateCode(language, problem.trim());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Multi-Agent Code Generator</h1>
        <p className="subtitle">
          Describe a problem and pick a language. A planner, coder, and
          reviewer agent will design, write, and harden the solution for you.
        </p>
      </header>

      <form className="card form" onSubmit={handleSubmit}>
        <label htmlFor="language">Programming language</label>
        <select
          id="language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={loading || languages.length === 0}
        >
          {languages.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <label htmlFor="problem">Problem statement</label>
        <textarea
          id="problem"
          rows={6}
          placeholder="e.g. Write a function that validates an email address and returns whether it is valid."
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          disabled={loading}
        />

        <button type="submit" disabled={!canSubmit}>
          {loading ? "Generating…" : "Generate solution"}
        </button>
      </form>

      {error && <div className="card error">{error}</div>}

      {loading && (
        <div className="card loading">
          Running planner → coder → reviewer pipeline…
        </div>
      )}

      <ResultView result={result} />
    </div>
  );
}

export default App;
