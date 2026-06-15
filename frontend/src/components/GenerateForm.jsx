import React, { useState } from "react";

const PLATFORMS = [
  { value: "linkedin", label: "LinkedIn Post" },
  { value: "website", label: "Website Article" },
  { value: "blog", label: "Blog Post" },
];

const TONES = [
  "professional",
  "casual",
  "friendly",
  "authoritative",
  "inspirational",
  "witty",
];

const LENGTHS = [
  { value: "short", label: "Short" },
  { value: "medium", label: "Medium" },
  { value: "long", label: "Long" },
];

export default function GenerateForm({ onGenerate, loading }) {
  const [form, setForm] = useState({
    topic: "",
    platform: "linkedin",
    tone: "professional",
    length: "medium",
    audience: "",
    preferences: "",
  });

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = (e) => {
    e.preventDefault();
    onGenerate(form);
  };

  return (
    <form className="card form" onSubmit={submit}>
      <h2 className="form-title">Create content</h2>
      <p className="form-sub">
        Leave the topic blank to let the research agent pick a trending angle from the last 24 hours.
      </p>

      <label className="field">
        <span>Topic / interest</span>
        <input
          type="text"
          placeholder="e.g. AI in healthcare, remote work culture…"
          value={form.topic}
          onChange={update("topic")}
        />
      </label>

      <div className="grid-2">
        <label className="field">
          <span>Platform</span>
          <select value={form.platform} onChange={update("platform")}>
            {PLATFORMS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Length</span>
          <select value={form.length} onChange={update("length")}>
            {LENGTHS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="field">
        <span>Tone</span>
        <div className="chips">
          {TONES.map((t) => (
            <button
              type="button"
              key={t}
              className={`chip ${form.tone === t ? "chip-active" : ""}`}
              onClick={() => setForm({ ...form, tone: t })}
            >
              {t}
            </button>
          ))}
        </div>
      </label>

      <label className="field">
        <span>Target audience</span>
        <input
          type="text"
          placeholder="e.g. startup founders, marketing managers…"
          value={form.audience}
          onChange={update("audience")}
        />
      </label>

      <label className="field">
        <span>Extra preferences (optional)</span>
        <textarea
          rows={3}
          placeholder="Any specific instructions, angle, or things to avoid…"
          value={form.preferences}
          onChange={update("preferences")}
        />
      </label>

      <button className="btn-primary" type="submit" disabled={loading}>
        {loading ? "Generating…" : "✨ Generate content"}
      </button>
    </form>
  );
}
