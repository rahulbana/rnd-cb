import { useState } from "react";
import SearchForm from "./components/SearchForm.jsx";
import ReportView from "./components/ReportView.jsx";
import { analyzeBook, downloadReport } from "./api.js";

export default function App() {
  const [query, setQuery] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(q) {
    setLoading(true);
    setError("");
    setReport(null);
    setQuery(q);
    try {
      const data = await analyzeBook(q);
      setReport(data);
    } catch (e) {
      setError(e.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload(format) {
    if (!query) return;
    setDownloading(true);
    setError("");
    try {
      await downloadReport(query, format);
    } catch (e) {
      setError(e.message || "Download failed.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>📚 Book Review Aggregator</h1>
        <p className="tagline">
          Enter a book and let the agents gather a summary and reviews from
          readers, critics, companies, and celebrities across the web.
        </p>
      </header>

      <SearchForm onSubmit={handleSubmit} loading={loading} />

      {error && <div className="error">{error}</div>}

      {loading && (
        <div className="loading">
          <div className="spinner" />
          <p>Agents are searching the web and verifying reviews…</p>
        </div>
      )}

      {report && !loading && (
        <ReportView
          report={report}
          onDownload={handleDownload}
          downloading={downloading}
        />
      )}

      <footer className="app-footer">
        Multi-agent pipeline · FastAPI + OpenAI backend
      </footer>
    </div>
  );
}
