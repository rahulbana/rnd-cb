import React, { useState } from "react";

const SECTIONS = [
  { key: "title", label: "Product Title", type: "text" },
  { key: "short_description", label: "Short Description", type: "text" },
  { key: "detailed_description", label: "Detailed Description", type: "text" },
  { key: "key_features", label: "Key Features", type: "list" },
  { key: "benefits", label: "Benefits", type: "list" },
  { key: "seo_keywords", label: "SEO Keywords", type: "tags" },
  { key: "meta_description", label: "Meta Description", type: "text" },
];

function Section({ label, value, type, onRegenerate }) {
  const [busy, setBusy] = useState(false);

  async function handle() {
    setBusy(true);
    try {
      await onRegenerate();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="section">
      <div className="section-head">
        <h4>{label}</h4>
        <button className="regen" onClick={handle} disabled={busy} title="Regenerate this section">
          {busy ? "…" : "↻ Regenerate"}
        </button>
      </div>
      {type === "list" && (
        <ul>
          {(value || []).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
      {type === "tags" && (
        <div className="tags">
          {(value || []).map((item, i) => (
            <span className="tag" key={i}>
              {item}
            </span>
          ))}
        </div>
      )}
      {type === "text" && <p>{value}</p>}
    </div>
  );
}

export default function ResultCard({ index, total, data, onRegenerate }) {
  return (
    <div className="card">
      {total > 1 && <div className="variant-badge">Variant {index + 1}</div>}
      {SECTIONS.map((s) => (
        <Section
          key={s.key}
          label={s.label}
          value={data[s.key]}
          type={s.type}
          onRegenerate={() => onRegenerate(s.key)}
        />
      ))}
    </div>
  );
}
