import React, { useEffect, useState } from "react";

// Slide-over panel for editing the active conversation's system prompt and
// temperature. Saves on demand via onSave(payload).
export default function SettingsPanel({
  conversation,
  temperatureSupported,
  model,
  onSave,
  onClose,
}) {
  const [systemPrompt, setSystemPrompt] = useState("");
  const [temperature, setTemperature] = useState(1.0);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (conversation) {
      setSystemPrompt(conversation.system_prompt || "");
      setTemperature(
        typeof conversation.temperature === "number"
          ? conversation.temperature
          : 1.0
      );
    }
  }, [conversation]);

  async function handleSave() {
    await onSave({ system_prompt: systemPrompt, temperature });
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  }

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Conversation settings</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="settings-body">
          <label className="settings-field">
            <span>System prompt</span>
            <textarea
              value={systemPrompt}
              rows={6}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="Instructions that steer the assistant's behavior…"
            />
          </label>

          <label className="settings-field">
            <span>
              Temperature: <strong>{temperature.toFixed(2)}</strong>
            </span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
            />
            <small className="field-hint">
              Lower = more focused, higher = more creative.
            </small>
            {!temperatureSupported && (
              <small className="field-warning">
                Note: the active model (<code>{model}</code>) does not support
                temperature — this value is saved but not applied. Use a model
                like <code>claude-haiku-4-5</code> to enable it.
              </small>
            )}
          </label>

          <div className="settings-meta">
            <span>Model</span>
            <code>{model}</code>
          </div>
        </div>

        <div className="settings-footer">
          <button className="save-btn" onClick={handleSave}>
            {saved ? "Saved ✓" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
