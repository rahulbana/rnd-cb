import { useState } from "react";
import { getTranscript, getSummary, getMindMap } from "./api.js";
import Summary from "./components/Summary.jsx";
import QA from "./components/QA.jsx";
import MindMap from "./components/MindMap.jsx";

const TABS = ["Summary", "Q&A", "Mind Map"];

export default function App() {
  const [url, setUrl] = useState("");
  const [video, setVideo] = useState(null); // { video_id, title, author, thumbnail_url, char_count }
  const [loadingVideo, setLoadingVideo] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [tab, setTab] = useState("Summary");

  // Lazily-loaded, cached results per feature for the current video.
  const [summary, setSummary] = useState(null);
  const [summaryState, setSummaryState] = useState({ loading: false, error: null });
  const [mindmap, setMindmap] = useState(null);
  const [mindmapState, setMindmapState] = useState({ loading: false, error: null });

  function reset() {
    setVideo(null);
    setSummary(null);
    setSummaryState({ loading: false, error: null });
    setMindmap(null);
    setMindmapState({ loading: false, error: null });
    setTab("Summary");
  }

  async function loadVideo(e) {
    e.preventDefault();
    if (!url.trim() || loadingVideo) return;
    setLoadingVideo(true);
    setLoadError(null);
    reset();
    try {
      const t = await getTranscript(url.trim());
      setVideo(t);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoadingVideo(false);
    }
  }

  async function loadSummary() {
    if (summary || summaryState.loading) return;
    setSummaryState({ loading: true, error: null });
    try {
      const res = await getSummary(video.video_id);
      setSummary(res.summary);
      setSummaryState({ loading: false, error: null });
    } catch (err) {
      setSummaryState({ loading: false, error: err.message });
    }
  }

  async function loadMindMap() {
    if (mindmap || mindmapState.loading) return;
    setMindmapState({ loading: true, error: null });
    try {
      const res = await getMindMap(video.video_id);
      setMindmap(res.mermaid);
      setMindmapState({ loading: false, error: null });
    } catch (err) {
      setMindmapState({ loading: false, error: err.message });
    }
  }

  function selectTab(next) {
    setTab(next);
    if (!video) return;
    if (next === "Summary") loadSummary();
    if (next === "Mind Map") loadMindMap();
  }

  return (
    <div className="app">
      <header className="header">
        <h1>
          <span className="logo">▶</span> YouTube Research Assistant
        </h1>
        <p className="subtitle">
          Summarize a video, ask questions about it, and generate a mind map — from
          its transcript.
        </p>
      </header>

      <form className="url-form" onSubmit={loadVideo}>
        <input
          type="text"
          value={url}
          placeholder="Paste a YouTube URL (e.g. https://youtu.be/…)"
          onChange={(e) => setUrl(e.target.value)}
          disabled={loadingVideo}
        />
        <button type="submit" disabled={loadingVideo || !url.trim()}>
          {loadingVideo ? "Loading…" : "Load video"}
        </button>
      </form>

      {loadError && <div className="error">{loadError}</div>}

      {video && (
        <main className="workspace">
          <section className="video-card">
            {video.thumbnail_url && (
              <img
                className="thumb"
                src={video.thumbnail_url}
                alt={video.title || "Video thumbnail"}
              />
            )}
            <div className="video-meta">
              <h2>{video.title || "Untitled video"}</h2>
              {video.author && <p className="author">{video.author}</p>}
              <p className="stat">
                Transcript loaded · {video.char_count.toLocaleString()} characters
                {video.language ? ` · ${video.language}` : ""}
              </p>
              <a
                className="yt-link"
                href={`https://www.youtube.com/watch?v=${video.video_id}`}
                target="_blank"
                rel="noreferrer"
              >
                Open on YouTube ↗
              </a>
            </div>
          </section>

          <nav className="tabs">
            {TABS.map((t) => (
              <button
                key={t}
                className={t === tab ? "tab active" : "tab"}
                onClick={() => selectTab(t)}
              >
                {t}
              </button>
            ))}
          </nav>

          <section className="panel">
            {tab === "Summary" && (
              <>
                {summaryState.loading && <Loader label="Summarizing…" />}
                {summaryState.error && <div className="error">{summaryState.error}</div>}
                {summary && <Summary text={summary} />}
                {!summary && !summaryState.loading && !summaryState.error && (
                  <button className="cta" onClick={loadSummary}>
                    Generate summary
                  </button>
                )}
              </>
            )}

            {tab === "Q&A" && <QA url={video.video_id} />}

            {tab === "Mind Map" && (
              <>
                {mindmapState.loading && <Loader label="Building mind map…" />}
                {mindmapState.error && <div className="error">{mindmapState.error}</div>}
                {mindmap && <MindMap code={mindmap} />}
                {!mindmap && !mindmapState.loading && !mindmapState.error && (
                  <button className="cta" onClick={loadMindMap}>
                    Generate mind map
                  </button>
                )}
              </>
            )}
          </section>
        </main>
      )}

      {!video && !loadingVideo && (
        <div className="empty">
          <p>Paste a YouTube link above to get started.</p>
          <p className="fine">
            The video must have captions available. Your OpenAI key stays on the
            server.
          </p>
        </div>
      )}

      <footer className="footer">
        Built with FastAPI · React · OpenAI
      </footer>
    </div>
  );
}

function Loader({ label }) {
  return (
    <div className="loader">
      <span className="spinner" /> {label}
    </div>
  );
}
