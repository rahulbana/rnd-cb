import { useEffect, useState } from "react";
import {
  Field,
  TextArea,
  LinesField,
  TagsField,
  RepeatableSection,
} from "./components/FormControls.jsx";
import { generateResume, previewHtml, renderPdf, getHealth } from "./lib/api.js";

const STYLES = ["modern", "classic", "minimal", "creative"];
const TONES = ["professional", "concise", "impactful", "friendly"];

const EMPTY_EXPERIENCE = {
  company: "",
  role: "",
  location: "",
  start_date: "",
  end_date: "",
  highlights: [],
};
const EMPTY_EDUCATION = {
  institution: "",
  degree: "",
  field_of_study: "",
  start_date: "",
  end_date: "",
  gpa: "",
  details: [],
};
const EMPTY_PROJECT = {
  name: "",
  description: "",
  technologies: [],
  link: "",
  highlights: [],
};

const SAMPLE = {
  personal: {
    full_name: "Jordan Rivera",
    title: "Full-Stack Software Engineer",
    email: "jordan.rivera@example.com",
    phone: "+1 (555) 234-9812",
    location: "Austin, TX",
    website: "jordanrivera.dev",
    linkedin: "linkedin.com/in/jordanrivera",
    github: "github.com/jrivera",
  },
  summary: "",
  experience: [
    {
      company: "Brightwave Labs",
      role: "Senior Software Engineer",
      location: "Austin, TX",
      start_date: "2021",
      end_date: "Present",
      highlights: [
        "led migration of monolith to microservices, cutting deploy time by 60%",
        "mentored 4 junior engineers",
        "built internal analytics dashboard used by 200+ employees",
      ],
    },
  ],
  education: [
    {
      institution: "University of Texas at Austin",
      degree: "B.S.",
      field_of_study: "Computer Science",
      start_date: "2014",
      end_date: "2018",
      gpa: "3.8",
      details: [],
    },
  ],
  skills: ["Python", "TypeScript", "React", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"],
  projects: [
    {
      name: "OpenBudget",
      description: "an open-source personal finance tracker",
      technologies: ["React", "FastAPI", "PostgreSQL"],
      link: "github.com/jrivera/openbudget",
      highlights: ["1,200+ GitHub stars", "featured in a newsletter with 30k readers"],
    },
  ],
  achievements: ["Hackathon winner, ATX Build 2022", "Speaker at PyTexas 2023"],
  target_role: "Staff Software Engineer",
};

function blankInput() {
  return {
    personal: {
      full_name: "",
      title: "",
      email: "",
      phone: "",
      location: "",
      website: "",
      linkedin: "",
      github: "",
    },
    summary: "",
    experience: [{ ...EMPTY_EXPERIENCE }],
    education: [{ ...EMPTY_EDUCATION }],
    skills: [],
    projects: [{ ...EMPTY_PROJECT }],
    achievements: [],
    target_role: "",
  };
}

// Strip empty strings out of the line-based arrays before sending to the API.
function cleanInput(input) {
  const clean = structuredClone(input);
  const trimList = (arr) => (arr || []).map((s) => s.trim()).filter(Boolean);
  clean.achievements = trimList(clean.achievements);
  clean.experience = clean.experience
    .map((e) => ({ ...e, highlights: trimList(e.highlights) }))
    .filter((e) => e.company || e.role);
  clean.education = clean.education
    .map((e) => ({ ...e, details: trimList(e.details) }))
    .filter((e) => e.institution);
  clean.projects = clean.projects
    .map((p) => ({ ...p, highlights: trimList(p.highlights) }))
    .filter((p) => p.name);
  return clean;
}

export default function App() {
  const [input, setInput] = useState(blankInput());
  const [style, setStyle] = useState("modern");
  const [tone, setTone] = useState("professional");
  const [resume, setResume] = useState(null);
  const [previewSrc, setPreviewSrc] = useState("");
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  // Refresh the preview whenever we have a generated resume or the style changes.
  useEffect(() => {
    if (!resume) return;
    let cancelled = false;
    previewHtml(resume, style)
      .then((html) => !cancelled && setPreviewSrc(html))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [resume, style]);

  const setPersonal = (key, val) =>
    setInput((s) => ({ ...s, personal: { ...s.personal, [key]: val } }));

  const setListItem = (list, idx, key, val) =>
    setInput((s) => {
      const next = [...s[list]];
      next[idx] = { ...next[idx], [key]: val };
      return { ...s, [list]: next };
    });

  const addItem = (list, blank) =>
    setInput((s) => ({ ...s, [list]: [...s[list], { ...blank }] }));

  const removeItem = (list, idx) =>
    setInput((s) => ({ ...s, [list]: s[list].filter((_, i) => i !== idx) }));

  async function handleGenerate(e) {
    e.preventDefault();
    setError("");
    if (!input.personal.full_name.trim()) {
      setError("Please enter your full name.");
      return;
    }
    setLoading(true);
    try {
      const data = await generateResume(cleanInput(input), style, tone);
      setResume(data.resume);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload() {
    if (!resume) return;
    setError("");
    setDownloading(true);
    try {
      const blob = await renderPdf(resume, style);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const stem =
        resume.personal.full_name.replace(/[^A-Za-z0-9]+/g, "_").toLowerCase() ||
        "resume";
      a.download = `${stem}_resume.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  function loadSample() {
    setInput(structuredClone(SAMPLE));
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>AI Resume/CV Generator</h1>
          <p className="subtitle">
            Fill in your details, let AI polish them, pick a style, and download a PDF.
          </p>
        </div>
        {health && (
          <span className={`badge ${health.llm_enabled ? "on" : "off"}`}>
            {health.llm_enabled ? `AI: ${health.model}` : "AI: offline (local mode)"}
          </span>
        )}
      </header>

      <div className="layout">
        {/* ---------------- Left: form ---------------- */}
        <form className="panel form" onSubmit={handleGenerate}>
          <div className="toolbar">
            <button type="button" className="btn-ghost" onClick={loadSample}>
              Load sample data
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setInput(blankInput())}
            >
              Clear
            </button>
          </div>

          <fieldset>
            <legend>Personal information</legend>
            <div className="grid2">
              <Field label="Full name *" value={input.personal.full_name}
                onChange={(v) => setPersonal("full_name", v)} placeholder="Jane Doe" />
              <Field label="Professional title" value={input.personal.title}
                onChange={(v) => setPersonal("title", v)} placeholder="Software Engineer" />
              <Field label="Email" type="email" value={input.personal.email}
                onChange={(v) => setPersonal("email", v)} placeholder="jane@example.com" />
              <Field label="Phone" value={input.personal.phone}
                onChange={(v) => setPersonal("phone", v)} placeholder="+1 555 000 0000" />
              <Field label="Location" value={input.personal.location}
                onChange={(v) => setPersonal("location", v)} placeholder="City, Country" />
              <Field label="Website" value={input.personal.website}
                onChange={(v) => setPersonal("website", v)} placeholder="jane.dev" />
              <Field label="LinkedIn" value={input.personal.linkedin}
                onChange={(v) => setPersonal("linkedin", v)} placeholder="linkedin.com/in/jane" />
              <Field label="GitHub" value={input.personal.github}
                onChange={(v) => setPersonal("github", v)} placeholder="github.com/jane" />
            </div>
          </fieldset>

          <fieldset>
            <legend>Summary & target</legend>
            <TextArea label="Professional summary (optional — AI writes one if blank)"
              value={input.summary} onChange={(v) => setInput((s) => ({ ...s, summary: v }))}
              placeholder="A short summary in your own words…" />
            <Field label="Target role (tailors the resume)" value={input.target_role}
              onChange={(v) => setInput((s) => ({ ...s, target_role: v }))}
              placeholder="Senior Backend Engineer" />
          </fieldset>

          <fieldset>
            <legend>Experience</legend>
            <RepeatableSection title="Role" items={input.experience}
              onAdd={() => addItem("experience", EMPTY_EXPERIENCE)}
              onRemove={(i) => removeItem("experience", i)} addLabel="Add role"
              renderItem={(item, idx) => (
                <>
                  <div className="grid2">
                    <Field label="Company" value={item.company}
                      onChange={(v) => setListItem("experience", idx, "company", v)} />
                    <Field label="Role" value={item.role}
                      onChange={(v) => setListItem("experience", idx, "role", v)} />
                    <Field label="Location" value={item.location}
                      onChange={(v) => setListItem("experience", idx, "location", v)} />
                    <div className="grid2 inner">
                      <Field label="Start" value={item.start_date}
                        onChange={(v) => setListItem("experience", idx, "start_date", v)} placeholder="2021" />
                      <Field label="End" value={item.end_date}
                        onChange={(v) => setListItem("experience", idx, "end_date", v)} placeholder="Present" />
                    </div>
                  </div>
                  <LinesField label="Highlights (one per line — AI sharpens these)"
                    value={item.highlights}
                    onChange={(v) => setListItem("experience", idx, "highlights", v)}
                    placeholder={"built X that did Y\nreduced costs by 30%"} />
                </>
              )} />
          </fieldset>

          <fieldset>
            <legend>Projects</legend>
            <RepeatableSection title="Project" items={input.projects}
              onAdd={() => addItem("projects", EMPTY_PROJECT)}
              onRemove={(i) => removeItem("projects", i)} addLabel="Add project"
              renderItem={(item, idx) => (
                <>
                  <div className="grid2">
                    <Field label="Name" value={item.name}
                      onChange={(v) => setListItem("projects", idx, "name", v)} />
                    <Field label="Link" value={item.link}
                      onChange={(v) => setListItem("projects", idx, "link", v)} />
                  </div>
                  <Field label="Description" value={item.description}
                    onChange={(v) => setListItem("projects", idx, "description", v)} />
                  <TagsField label="Technologies (comma separated)" value={item.technologies}
                    onChange={(v) => setListItem("projects", idx, "technologies", v)}
                    placeholder="React, FastAPI, PostgreSQL" />
                  <LinesField label="Highlights (one per line)" value={item.highlights}
                    onChange={(v) => setListItem("projects", idx, "highlights", v)} />
                </>
              )} />
          </fieldset>

          <fieldset>
            <legend>Education</legend>
            <RepeatableSection title="Education" items={input.education}
              onAdd={() => addItem("education", EMPTY_EDUCATION)}
              onRemove={(i) => removeItem("education", i)} addLabel="Add education"
              renderItem={(item, idx) => (
                <>
                  <div className="grid2">
                    <Field label="Institution" value={item.institution}
                      onChange={(v) => setListItem("education", idx, "institution", v)} />
                    <Field label="Degree" value={item.degree}
                      onChange={(v) => setListItem("education", idx, "degree", v)} placeholder="B.S." />
                    <Field label="Field of study" value={item.field_of_study}
                      onChange={(v) => setListItem("education", idx, "field_of_study", v)} />
                    <div className="grid2 inner">
                      <Field label="Start" value={item.start_date}
                        onChange={(v) => setListItem("education", idx, "start_date", v)} />
                      <Field label="End" value={item.end_date}
                        onChange={(v) => setListItem("education", idx, "end_date", v)} />
                    </div>
                    <Field label="GPA" value={item.gpa}
                      onChange={(v) => setListItem("education", idx, "gpa", v)} />
                  </div>
                </>
              )} />
          </fieldset>

          <fieldset>
            <legend>Skills & achievements</legend>
            <TagsField label="Skills (comma separated)" value={input.skills}
              onChange={(v) => setInput((s) => ({ ...s, skills: v }))}
              placeholder="Python, React, AWS, Docker" />
            <LinesField label="Achievements (one per line)" value={input.achievements}
              onChange={(v) => setInput((s) => ({ ...s, achievements: v }))}
              placeholder={"Hackathon winner 2023\nPublished a paper on…"} />
          </fieldset>

          {error && <div className="error">{error}</div>}

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Generating…" : "Generate resume"}
          </button>
        </form>

        {/* ---------------- Right: preview + controls ---------------- */}
        <div className="panel preview-panel">
          <div className="preview-controls">
            <div className="control-group">
              <label>Style</label>
              <div className="style-picker">
                {STYLES.map((s) => (
                  <button key={s} type="button"
                    className={`style-chip ${style === s ? "active" : ""}`}
                    onClick={() => setStyle(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div className="control-group">
              <label>AI tone</label>
              <select value={tone} onChange={(e) => setTone(e.target.value)}>
                {TONES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <button type="button" className="btn-primary download"
              onClick={handleDownload} disabled={!resume || downloading}>
              {downloading ? "Preparing…" : "Download PDF"}
            </button>
          </div>

          <div className="preview-frame">
            {previewSrc ? (
              <iframe title="Resume preview" srcDoc={previewSrc} />
            ) : (
              <div className="preview-empty">
                <p>Your resume preview will appear here.</p>
                <p className="hint">
                  Fill in the form (or load sample data) and click{" "}
                  <strong>Generate resume</strong>.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
