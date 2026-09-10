// The brief captures the four core inputs: topic, audience, style, length.

const STYLES = [
  "informative and engaging",
  "casual and conversational",
  "professional and authoritative",
  "witty and playful",
  "technical and detailed",
];

const LENGTHS = [
  { value: "short", label: "Short (~500 words)" },
  { value: "medium", label: "Medium (~1000 words)" },
  { value: "long", label: "Long (~1800 words)" },
];

export default function BriefForm({ brief, setBrief, disabled }) {
  const update = (key) => (e) => setBrief({ ...brief, [key]: e.target.value });

  return (
    <div className="card">
      <h2>1. Describe your article</h2>
      <label>
        Topic
        <input
          type="text"
          value={brief.topic}
          onChange={update("topic")}
          placeholder="e.g. Generative AI for Beginners"
          disabled={disabled}
        />
      </label>

      <label>
        Target audience
        <input
          type="text"
          value={brief.audience}
          onChange={update("audience")}
          placeholder="e.g. complete beginners with no coding background"
          disabled={disabled}
        />
      </label>

      <div className="row">
        <label>
          Writing style
          <input
            type="text"
            list="style-options"
            value={brief.style}
            onChange={update("style")}
            disabled={disabled}
          />
          <datalist id="style-options">
            {STYLES.map((s) => (
              <option key={s} value={s} />
            ))}
          </datalist>
        </label>

        <label>
          Article length
          <select value={brief.length} onChange={update("length")} disabled={disabled}>
            {LENGTHS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
