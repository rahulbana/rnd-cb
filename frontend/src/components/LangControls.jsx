import React from "react";

// Source/target language selectors with a swap button, plus style chips.
export default function LangControls({
  languages,
  styles,
  sourceLang,
  targetLang,
  style,
  onSource,
  onTarget,
  onStyle,
  onSwap,
}) {
  const targetLanguages = languages.filter((l) => l.code !== "auto");
  return (
    <>
      <div className="controls">
        <div className="field">
          <label>Source language</label>
          <select value={sourceLang} onChange={(e) => onSource(e.target.value)}>
            {languages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </div>

        <button
          className="swap-btn"
          title="Swap languages"
          onClick={onSwap}
          disabled={sourceLang === "auto"}
        >
          ⇄
        </button>

        <div className="field">
          <label>Target language</label>
          <select value={targetLang} onChange={(e) => onTarget(e.target.value)}>
            {targetLanguages.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="styles">
        {styles.map((s) => (
          <button
            key={s}
            className={`style-chip ${s === style ? "active" : ""}`}
            onClick={() => onStyle(s)}
          >
            {s}
          </button>
        ))}
      </div>
    </>
  );
}
