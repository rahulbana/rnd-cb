import { useEffect, useState } from "react";
import { api } from "./api";
import BriefForm from "./components/BriefForm";
import Markdown from "./components/Markdown";

const DEFAULT_BRIEF = {
  topic: "Generative AI for Beginners",
  audience: "complete beginners with no coding background",
  style: "informative and engaging",
  length: "medium",
};

export default function App() {
  const [brief, setBrief] = useState(DEFAULT_BRIEF);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  const [outline, setOutline] = useState([]);
  const [sections, setSections] = useState([]); // { heading, content }
  const [title, setTitle] = useState("");
  const [titleOptions, setTitleOptions] = useState([]);
  const [meta, setMeta] = useState("");

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const run = async (label, fn) => {
    setBusy(label);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy("");
    }
  };

  const needTopic = !brief.topic.trim();

  // --- Individual steps ---------------------------------------------------
  const genOutline = () =>
    run("outline", async () => {
      const data = await api.outline(brief);
      setOutline(data.outline);
      setSections([]);
    });

  const genSection = (item, index) =>
    run(`section-${index}`, async () => {
      const data = await api.section({
        ...brief,
        heading: item.heading,
        section_summary: item.summary || "",
        outline,
      });
      setSections((prev) => {
        const next = [...prev];
        next[index] = { heading: data.heading, content: data.content };
        return next;
      });
    });

  const genAllSections = () =>
    run("all-sections", async () => {
      const results = [];
      for (const item of outline) {
        const data = await api.section({
          ...brief,
          heading: item.heading,
          section_summary: item.summary || "",
          outline,
        });
        results.push({ heading: data.heading, content: data.content });
        setSections([...results]);
      }
    });

  const genTitles = () =>
    run("titles", async () => {
      const data = await api.titles(brief);
      setTitleOptions(data.titles);
      if (!title && data.titles.length) setTitle(data.titles[0]);
    });

  const genMeta = () =>
    run("meta", async () => {
      const data = await api.metaDescription(brief);
      setMeta(data.meta_description);
    });

  const rewrite = (index) =>
    run(`rewrite-${index}`, async () => {
      const instruction =
        window.prompt("How should this section be rewritten?", "Make it more concise and engaging.");
      if (instruction === null) return;
      const section = sections[index];
      const data = await api.rewrite({
        ...brief,
        heading: section.heading,
        content: section.content,
        instruction,
      });
      setSections((prev) => {
        const next = [...prev];
        next[index] = { heading: data.heading, content: data.content };
        return next;
      });
    });

  // --- One-click full article --------------------------------------------
  const genArticle = () =>
    run("article", async () => {
      const data = await api.article(brief);
      setOutline(data.outline);
      setSections(data.sections);
      setTitle(data.title);
      setTitleOptions([data.title]);
      setMeta(data.meta_description);
    });

  const fullMarkdown = () => {
    const lines = [];
    if (title) lines.push(`# ${title}\n`);
    for (const s of sections) {
      if (!s) continue;
      lines.push(`## ${s.heading}\n\n${s.content}\n`);
    }
    return lines.join("\n").trim();
  };

  const copyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(fullMarkdown());
    } catch {
      setError("Could not copy to clipboard.");
    }
  };

  return (
    <div className="app">
      <header>
        <h1>✍️ AI Blog Generator</h1>
        <p className="subtitle">
          Multi-step prompt chaining: outline → sections → title → meta description.
        </p>
        {health && !health.openai_configured && (
          <div className="banner warn">
            ⚠️ Backend has no OpenAI key. Add <code>OPENAI_API_KEY</code> to{" "}
            <code>backend/.env</code> and restart.
          </div>
        )}
      </header>

      {error && <div className="banner error">{error}</div>}

      <BriefForm brief={brief} setBrief={setBrief} disabled={!!busy} />

      <div className="card">
        <h2>2. Generate</h2>
        <div className="btn-row">
          <button onClick={genOutline} disabled={!!busy || needTopic}>
            {busy === "outline" ? "Generating…" : "Generate outline"}
          </button>
          <button onClick={genTitles} disabled={!!busy || needTopic}>
            {busy === "titles" ? "Generating…" : "Suggest titles"}
          </button>
          <button onClick={genMeta} disabled={!!busy || needTopic}>
            {busy === "meta" ? "Generating…" : "Meta description"}
          </button>
          <button className="primary" onClick={genArticle} disabled={!!busy || needTopic}>
            {busy === "article" ? "Writing full article…" : "⚡ Generate complete article"}
          </button>
        </div>
        {needTopic && <p className="hint">Enter a topic to get started.</p>}
      </div>

      {titleOptions.length > 0 && (
        <div className="card">
          <h2>Title</h2>
          <div className="title-options">
            {titleOptions.map((t) => (
              <label key={t} className="title-option">
                <input
                  type="radio"
                  name="title"
                  checked={title === t}
                  onChange={() => setTitle(t)}
                />
                {t}
              </label>
            ))}
          </div>
        </div>
      )}

      {meta && (
        <div className="card">
          <h2>Meta description</h2>
          <p className="meta">{meta}</p>
          <span className="hint">{meta.length} characters</span>
        </div>
      )}

      {outline.length > 0 && (
        <div className="card">
          <div className="card-head">
            <h2>Outline</h2>
            <button onClick={genAllSections} disabled={!!busy}>
              {busy === "all-sections" ? "Writing sections…" : "Write all sections"}
            </button>
          </div>
          <ol className="outline">
            {outline.map((item, i) => (
              <li key={i}>
                <div className="outline-item">
                  <div>
                    <strong>{item.heading}</strong>
                    {item.summary && <p className="summary">{item.summary}</p>}
                  </div>
                  <button onClick={() => genSection(item, i)} disabled={!!busy}>
                    {busy === `section-${i}` ? "Writing…" : sections[i] ? "Rewrite ↺" : "Write"}
                  </button>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}

      {sections.some(Boolean) && (
        <div className="card article">
          <div className="card-head">
            <h2>Article preview</h2>
            <button onClick={copyMarkdown} disabled={!!busy}>
              Copy Markdown
            </button>
          </div>
          {title && <h1 className="article-title">{title}</h1>}
          {sections.map((s, i) =>
            s ? (
              <section key={i} className="article-section">
                <div className="card-head">
                  <h3>{s.heading}</h3>
                  <button
                    className="link"
                    onClick={() => rewrite(i)}
                    disabled={!!busy}
                  >
                    {busy === `rewrite-${i}` ? "Rewriting…" : "Rewrite"}
                  </button>
                </div>
                <Markdown>{s.content}</Markdown>
              </section>
            ) : null
          )}
        </div>
      )}

      <footer>
        <p>
          FastAPI + OpenAI backend · React + Vite frontend
          {health?.model ? ` · model: ${health.model}` : ""}
        </p>
      </footer>
    </div>
  );
}
