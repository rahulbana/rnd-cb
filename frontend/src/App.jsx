import { useEffect, useState } from "react";
import { generateJSON, getHealth } from "./api";

const EXAMPLE_PROMPT = `Create a customer named Rahul,
email rahul@example.com,
age 35,
and city Delhi.`;

const EXAMPLE_SCHEMA = `{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "email": { "type": "string", "format": "email" },
    "age": { "type": "integer", "minimum": 0 },
    "city": { "type": "string" }
  },
  "required": ["name", "email", "age", "city"],
  "additionalProperties": false
}`;

export default function App() {
  const [prompt, setPrompt] = useState(EXAMPLE_PROMPT);
  const [schemaText, setSchemaText] = useState(EXAMPLE_SCHEMA);
  const [useSchema, setUseSchema] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: "down", configured: false }));
  }, []);

  function parseSchema() {
    if (!useSchema) return null;
    const trimmed = schemaText.trim();
    if (!trimmed) return null;
    return JSON.parse(trimmed); // throws on bad JSON; caught by caller
  }

  async function handleGenerate() {
    setError("");
    setResult(null);
    let schema;
    try {
      schema = parseSchema();
    } catch {
      setError("Your JSON Schema is not valid JSON. Please fix it.");
      return;
    }

    setLoading(true);
    try {
      const data = await generateJSON(prompt, schema);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleDownload() {
    if (!result?.data) return;
    const blob = new Blob([JSON.stringify(result.data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "generated.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleCopy() {
    if (!result?.data) return;
    navigator.clipboard.writeText(JSON.stringify(result.data, null, 2));
  }

  const configured = health?.configured;

  return (
    <div className="app">
      <header className="header">
        <h1>AI JSON Generator</h1>
        <p>Convert natural language into validated JSON.</p>
        {health && !configured && (
          <div className="banner warn">
            ⚠️ The backend has no OpenAI API key configured. Add one to{" "}
            <code>backend/.env</code> to enable generation.
          </div>
        )}
      </header>

      <main className="grid">
        <section className="panel">
          <label className="field">
            <span className="field-label">Natural-language input</span>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={6}
              placeholder="Describe the data you want as JSON..."
            />
          </label>

          <label className="checkbox">
            <input
              type="checkbox"
              checked={useSchema}
              onChange={(e) => setUseSchema(e.target.checked)}
            />
            <span>Constrain output with a custom JSON Schema</span>
          </label>

          {useSchema && (
            <label className="field">
              <span className="field-label">JSON Schema</span>
              <textarea
                className="mono"
                value={schemaText}
                onChange={(e) => setSchemaText(e.target.value)}
                rows={12}
                spellCheck={false}
              />
            </label>
          )}

          <button
            className="primary"
            onClick={handleGenerate}
            disabled={loading || !prompt.trim()}
          >
            {loading ? "Generating…" : "Generate JSON"}
          </button>

          {error && <div className="banner error">{error}</div>}
        </section>

        <section className="panel">
          <div className="output-header">
            <span className="field-label">Output</span>
            {result?.data && (
              <div className="actions">
                <button onClick={handleCopy}>Copy</button>
                <button onClick={handleDownload}>Download</button>
              </div>
            )}
          </div>

          {result ? (
            <>
              <div className="status-row">
                <span className={`pill ${result.valid ? "ok" : "bad"}`}>
                  {result.valid ? "✓ Valid" : "✗ Invalid"}
                </span>
                <span className="pill neutral">
                  {result.attempts} attempt{result.attempts === 1 ? "" : "s"}
                </span>
              </div>

              <pre className="output">
                {JSON.stringify(result.data, null, 2)}
              </pre>

              {result.errors?.length > 0 && (
                <div className="banner error">
                  <strong>Remaining validation errors:</strong>
                  <ul>
                    {result.errors.map((err, i) => (
                      <li key={i}>
                        <code>{err.path}</code>: {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="placeholder">
              Generated JSON will appear here.
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        API: <code>POST /api/generate</code> · <code>POST /api/validate</code> ·{" "}
        <code>GET /api/health</code>
      </footer>
    </div>
  );
}
