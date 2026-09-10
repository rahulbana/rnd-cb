import React, { useState } from "react";
import { api } from "../api.js";
import LangControls from "./LangControls.jsx";

// Single-text translation panel.
export default function TranslatePanel({ meta, onTranslated }) {
  const [sourceLang, setSourceLang] = useState("auto");
  const [targetLang, setTargetLang] = useState("hi");
  const [style, setStyle] = useState(meta.default_style);
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const swap = () => {
    if (sourceLang === "auto") return;
    setSourceLang(targetLang);
    setTargetLang(sourceLang);
  };

  const run = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.translate({
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
        style,
      });
      setResult(res);
      onTranslated?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const copy = () => {
    if (result) navigator.clipboard?.writeText(result.translated_text);
  };

  return (
    <div className="card">
      <LangControls
        languages={meta.languages}
        styles={meta.styles}
        sourceLang={sourceLang}
        targetLang={targetLang}
        style={style}
        onSource={setSourceLang}
        onTarget={setTargetLang}
        onStyle={setStyle}
        onSwap={swap}
      />

      <div className="io-grid">
        <div>
          <textarea
            placeholder="Enter text to translate…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <p className="hint">{text.length} characters</p>
        </div>
        <div>
          <div className="output">
            {result && (
              <button className="copy-btn" onClick={copy}>
                Copy
              </button>
            )}
            {result ? result.translated_text : <span className="hint">Translation appears here.</span>}
          </div>
          {result && result.source_lang === "auto" && (
            <p className="hint">Detected source: {result.detected_source_lang}</p>
          )}
        </div>
      </div>

      <div className="row">
        <button className="btn" onClick={run} disabled={loading || !text.trim()}>
          {loading ? "Translating…" : "Translate"}
        </button>
        <button className="btn ghost" onClick={() => { setText(""); setResult(null); setError(""); }}>
          Clear
        </button>
      </div>

      {error && <div className="error">{error}</div>}
    </div>
  );
}
