import { useEffect, useState } from "react";
import {
  fetchOptions,
  generateEmail,
  rewriteEmail,
  transformEmail,
} from "./api.js";

function titleCase(key) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function App() {
  const [options, setOptions] = useState(null);

  // Input brief
  const [intent, setIntent] = useState("");
  const [emailType, setEmailType] = useState("request");
  const [tone, setTone] = useState("professional");
  const [style, setStyle] = useState("professional");
  const [recipient, setRecipient] = useState("");
  const [sender, setSender] = useState("");

  // Generated output (editable)
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [rewriteNote, setRewriteNote] = useState("");

  const [busy, setBusy] = useState(null); // which action is running
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchOptions()
      .then(setOptions)
      .catch(() => setError("Could not reach the backend. Is it running on port 8000?"));
  }, []);

  const hasOutput = subject || body;

  async function run(action, fn) {
    setBusy(action);
    setError("");
    setCopied(false);
    try {
      const result = await fn();
      setSubject(result.subject || "");
      setBody(result.body || "");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  const onGenerate = () => {
    if (!intent.trim()) {
      setError("Describe what the email should say first.");
      return;
    }
    run("generate", () =>
      generateEmail({
        intent,
        email_type: emailType,
        tone,
        style,
        recipient: recipient || null,
        sender: sender || null,
      })
    );
  };

  const onRewrite = () =>
    run("rewrite", () =>
      rewriteEmail({ body, tone, style, instruction: rewriteNote || null })
    );

  const onTransform = (transform) =>
    run(transform, () => transformEmail({ body, transform, subject }));

  const onCopy = async () => {
    const text = subject ? `Subject: ${subject}\n\n${body}` : body;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="page">
      <header>
        <h1>✉️ AI Email Writer</h1>
        <p className="tagline">Turn a one-line instruction into a polished email.</p>
      </header>

      {error && <div className="banner error">{error}</div>}

      <div className="layout">
        {/* ---------------- Input panel ---------------- */}
        <section className="panel">
          <h2>Your brief</h2>

          <label>
            What do you want to say?
            <textarea
              rows={4}
              placeholder="e.g. Ask my manager for 2 days leave next week for a family event."
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
            />
          </label>

          <div className="row">
            <label>
              Email type
              <select value={emailType} onChange={(e) => setEmailType(e.target.value)}>
                {options &&
                  Object.keys(options.email_types).map((k) => (
                    <option key={k} value={k}>
                      {titleCase(k)}
                    </option>
                  ))}
              </select>
            </label>

            <label>
              Tone
              <select value={tone} onChange={(e) => setTone(e.target.value)}>
                {options &&
                  Object.keys(options.tones).map((k) => (
                    <option key={k} value={k}>
                      {titleCase(k)}
                    </option>
                  ))}
              </select>
            </label>
          </div>

          <div className="row">
            <label>
              Style
              <select value={style} onChange={(e) => setStyle(e.target.value)}>
                {options &&
                  Object.keys(options.styles).map((k) => (
                    <option key={k} value={k}>
                      {titleCase(k)}
                    </option>
                  ))}
              </select>
            </label>

            <label>
              Recipient <span className="hint">(optional)</span>
              <input
                type="text"
                placeholder="e.g. John"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
              />
            </label>
          </div>

          <label>
            Your name for the sign-off <span className="hint">(optional)</span>
            <input
              type="text"
              placeholder="e.g. Priya"
              value={sender}
              onChange={(e) => setSender(e.target.value)}
            />
          </label>

          <button className="primary" onClick={onGenerate} disabled={busy === "generate"}>
            {busy === "generate" ? "Writing…" : "Generate email"}
          </button>
        </section>

        {/* ---------------- Output panel ---------------- */}
        <section className="panel">
          <h2>Draft</h2>

          {!hasOutput && busy !== "generate" && (
            <p className="empty">Your generated email will appear here. It stays editable.</p>
          )}

          {(hasOutput || busy) && (
            <>
              <label>
                Subject
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Subject line"
                />
              </label>

              <label>
                Body
                <textarea
                  rows={12}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="Email body"
                />
              </label>

              <label>
                Rewrite instruction <span className="hint">(optional)</span>
                <input
                  type="text"
                  placeholder="e.g. make it warmer and mention the deadline"
                  value={rewriteNote}
                  onChange={(e) => setRewriteNote(e.target.value)}
                />
              </label>

              <div className="actions">
                <button onClick={onRewrite} disabled={!body || !!busy}>
                  {busy === "rewrite" ? "Rewriting…" : "↻ Rewrite"}
                </button>
                <button onClick={() => onTransform("shorten")} disabled={!body || !!busy}>
                  {busy === "shorten" ? "Shortening…" : "➖ Shorten"}
                </button>
                <button onClick={() => onTransform("expand")} disabled={!body || !!busy}>
                  {busy === "expand" ? "Expanding…" : "➕ Expand"}
                </button>
                <button className="copy" onClick={onCopy} disabled={!body}>
                  {copied ? "✓ Copied" : "⧉ Copy"}
                </button>
              </div>
            </>
          )}
        </section>
      </div>

      <footer>Built with FastAPI, React, and OpenAI.</footer>
    </div>
  );
}
