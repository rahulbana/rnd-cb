import React from "react";

// Live-switchable retrieval settings sent with every chat request.
export default function Settings({ config, settings, onChange, traceDefaultOpen, onTraceDefaultOpen }) {
  if (!config) return null;
  const opts = config.options || {};
  const set = (patch) => onChange({ ...settings, ...patch });

  const TOOL_LABELS = {
    search_documents: "📄 Documents",
    get_current_time: "🕐 Current time",
    calculator: "🧮 Calculator",
    web_search: "🌐 Web search",
  };
  const allTools = (config.options && config.options.tools) || Object.keys(TOOL_LABELS);
  const toolsEnabled = settings.tools_enabled || [];
  const toggleTool = (name, on) => {
    const next = on ? [...new Set([...toolsEnabled, name])] : toolsEnabled.filter((t) => t !== name);
    set({ tools_enabled: next });
  };

  return (
    <div className="settings-body">
      <label className="field checkbox">
        <input
          type="checkbox"
          checked={!!settings.agent_enabled}
          onChange={(e) => set({ agent_enabled: e.target.checked })}
        />
        <span>Agentic mode (use tools)</span>
      </label>

      {settings.agent_enabled && (
        <div className="tools-group">
          <div className="tools-label">Tools</div>
          {allTools.map((name) => (
            <label key={name} className="field checkbox tool-row">
              <input
                type="checkbox"
                checked={toolsEnabled.includes(name)}
                onChange={(e) => toggleTool(name, e.target.checked)}
              />
              <span>{TOOL_LABELS[name] || name}</span>
            </label>
          ))}
        </div>
      )}

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

      {onTraceDefaultOpen && (
        <label className="field checkbox">
          <input
            type="checkbox"
            checked={traceDefaultOpen}
            onChange={(e) => onTraceDefaultOpen(e.target.checked)}
          />
          <span>Show thought process by default</span>
        </label>
      )}

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
