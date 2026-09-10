import React, { useState } from "react";
import { api } from "../api.js";
import LangControls from "./LangControls.jsx";

// Batch translation panel: one line per text.
export default function BatchPanel({ meta, onTranslated }) {
  const [sourceLang, setSourceLang] = useState("auto");
  const [targetLang, setTargetLang] = useState("hi");
  const [style, setStyle] = useState(meta.default_style);
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const swap = () => {
    if (sourceLang === "auto") return;
    setSourceLang(targetLang);
    setTargetLang(sourceLang);
  };

  const lines = raw.split("\n").map((l) => l.trim()).filter(Boolean);

  const run = async () => {
    if (lines.length === 0) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.translateBatch({
        texts: lines,
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

      <textarea
        placeholder={"Enter one text per line…\nHow are you?\nWhere is the station?\nThank you very much."}
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
      />
      <p className="hint">{lines.length} item(s) to translate</p>

      <div className="row">
        <button className="btn" onClick={run} disabled={loading || lines.length === 0}>
          {loading ? "Translating…" : `Translate ${lines.length || ""} item(s)`}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div style={{ marginTop: 20 }}>
          {result.source_lang === "auto" && (
            <p className="hint">Detected source: {result.detected_source_lang}</p>
          )}
          {result.items.map((it, i) => (
            <div className="batch-result" key={i}>
              <div className="orig">{it.original}</div>
              <div>{it.translated_text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
