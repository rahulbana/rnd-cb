import { useState } from "react";
import { generateNotes, uploadTranscript } from "./api.js";
import NotesDisplay from "./components/NotesDisplay.jsx";

const SAMPLE = `Meeting title: Q3 Launch Planning

Sarah: Thanks everyone for joining. We need to lock the launch date for the mobile app today.
Raj: Engineering can be ready by October 15th if we cut the offline mode from v1.
Sarah: Let's do that. Decision: launch October 15th, offline mode moves to v1.1.
Priya: I'll own the marketing campaign and have the landing page ready by October 8th.
Raj: I'll coordinate the app store submission, needs to be in by October 10th.
Sarah: Great. Priya, can you also send the press release draft to me by October 6th?
Priya: Will do.
Sarah: Let's sync again next Monday. Thanks all.`;

export default function App() {
  const [title, setTitle] = useState("");
  const [transcript, setTranscript] = useState("");
  const [notes, setNotes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const data = await uploadTranscript(file);
      setTranscript(data.transcript);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleGenerate() {
    if (!transcript.trim()) {
      setError("Please paste or upload a transcript first.");
      return;
    }
    setError("");
    setLoading(true);
    setNotes(null);
    try {
      const result = await generateNotes(transcript, title);
      setNotes(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>AI Meeting Notes Generator</h1>
        <p>Turn a raw transcript into summary, decisions, action items, and a follow-up email.</p>
      </header>

      <section className="panel">
        <label className="field">
          <span>Meeting title (optional)</span>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Q3 Launch Planning"
          />
        </label>

        <label className="field">
          <span>Transcript</span>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste the meeting transcript here..."
            rows={12}
          />
        </label>

        <div className="actions">
          <label className="file-btn">
            Upload .txt
            <input type="file" accept=".txt,.md,text/plain" onChange={handleFile} hidden />
          </label>
          <button className="secondary" onClick={() => setTranscript(SAMPLE)}>
            Load sample
          </button>
          <button className="primary" onClick={handleGenerate} disabled={loading}>
            {loading ? "Generating…" : "Generate notes"}
          </button>
        </div>

        {error && <p className="error">{error}</p>}
      </section>

      {notes && <NotesDisplay notes={notes} />}
    </div>
  );
}
