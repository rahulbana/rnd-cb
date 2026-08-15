import React from "react";

// Live-switchable retrieval settings sent with every chat request.
export default function Settings({ config, settings, onChange }) {
  if (!config) return null;
  const opts = config.options || {};
  const set = (patch) => onChange({ ...settings, ...patch });

  return (
    <div className="settings-body">
      <label className="field">
        <span>Retrieval technique</span>
        <select
          value={settings.retrieval_strategy}
          onChange={(e) => set({ retrieval_strategy: e.target.value })}
        >
          {(opts.retrieval_strategy || ["simple", "hybrid"]).map((s) => (
            <option key={s} value={s}>
              {s === "hybrid" ? "Hybrid (vector + BM25)" : "Simple (vector)"}
            </option>
          ))}
        </select>
      </label>

      <label className="field checkbox">
        <input
          type="checkbox"
          checked={settings.rerank_enabled}
          onChange={(e) => set({ rerank_enabled: e.target.checked })}
        />
        <span>Re-ranker (cross-encoder)</span>
      </label>

      <label className="field">
        <span>LLM provider</span>
        <select
          value={settings.llm_provider}
          onChange={(e) => set({ llm_provider: e.target.value })}
        >
          {(opts.llm_provider || ["openai", "ollama"]).map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </label>

      <div className="field-row">
        <label className="field">
          <span>Candidates (top_k)</span>
          <input
            type="number"
            min={1}
            max={100}
            value={settings.top_k}
            onChange={(e) => set({ top_k: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span>Final passages</span>
          <input
            type="number"
            min={1}
            max={20}
            value={settings.final_top_k}
            onChange={(e) => set({ final_top_k: Number(e.target.value) })}
          />
        </label>
      </div>

      {settings.llm_provider === "openai" && !config.openai_configured && (
        <div className="warn-text">
          OpenAI key not set on the server — set RAG_OPENAI_API_KEY or switch to Ollama.
        </div>
      )}
    </div>
  );
}
