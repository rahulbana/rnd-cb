import { useCallback, useEffect, useRef, useState } from "react";

const MAX_FILE_BYTES = 15 * 1024 * 1024;

const PRESETS = [
  { label: "Remove background", prompt: "Remove the background completely and replace it with a plain white background" },
  { label: "Enhance", prompt: "Enhance this photo: improve lighting, sharpness, color balance and overall quality" },
  { label: "Black & white", prompt: "Convert this photo to black and white with rich contrast" },
  { label: "Vintage", prompt: "Make this photo look like a vintage film photograph from the 1970s with warm faded tones" },
  { label: "Watercolor", prompt: "Turn this photo into a watercolor painting" },
  { label: "Anime style", prompt: "Turn this photo into a Studio Ghibli style anime illustration" },
  { label: "Restore old photo", prompt: "Restore this old photo: fix scratches, tears and fading, and improve clarity" },
];

function fileToImage(file) {
  return new Promise((resolve, reject) => {
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      reject(new Error("Please choose a PNG, JPEG or WebP image."));
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      reject(new Error("Image is too large (max 15 MB)."));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      resolve({ mimeType: file.type, data: dataUrl.split(",")[1], dataUrl });
    };
    reader.onerror = () => reject(new Error("Could not read the file."));
    reader.readAsDataURL(file);
  });
}

async function callApi(route, payload) {
  const response = await fetch(route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = data.detail || data.error;
    // FastAPI validation errors return detail as a list of error objects.
    if (Array.isArray(message)) message = message.map((e) => e.msg || JSON.stringify(e)).join("; ");
    throw new Error(message || `Request failed (HTTP ${response.status})`);
  }
  return data;
}

export default function App() {
  const [tab, setTab] = useState("edit");
  const [source, setSource] = useState(null); // { mimeType, data, dataUrl }
  const [editPrompt, setEditPrompt] = useState("");
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null); // { message, kind: "loading" | "error" }
  const [result, setResult] = useState(null); // { image, text, beforeDataUrl }
  const [health, setHealth] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef(null);
  const resultRef = useRef(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => {});
  }, []);

  const loadFile = useCallback(async (file) => {
    if (!file) return;
    try {
      setSource(await fileToImage(file));
      setStatus(null);
    } catch (e) {
      setStatus({ message: e.message, kind: "error" });
    }
  }, []);

  // Paste an image anywhere on the page
  useEffect(() => {
    const onPaste = (e) => {
      const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
      if (item) {
        setTab("edit");
        loadFile(item.getAsFile());
      }
    };
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [loadFile]);

  async function run(route, payload, beforeDataUrl) {
    setBusy(true);
    setStatus({
      message:
        route === "/api/edit"
          ? "Editing your photo… this usually takes a few seconds."
          : "Generating your image… this usually takes a few seconds.",
      kind: "loading",
    });
    try {
      const data = await callApi(route, payload);
      setResult({ ...data, beforeDataUrl });
      setStatus(null);
      requestAnimationFrame(() =>
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
      );
    } catch (e) {
      setStatus({ message: e.message, kind: "error" });
    } finally {
      setBusy(false);
    }
  }

  function runEdit(promptOverride) {
    const prompt = (promptOverride ?? editPrompt).trim();
    if (!source) return setStatus({ message: "Add a photo first.", kind: "error" });
    if (!prompt) return setStatus({ message: "Describe the edit you want.", kind: "error" });
    run("/api/edit", { prompt, image: { mimeType: source.mimeType, data: source.data } }, source.dataUrl);
  }

  function runGenerate() {
    const prompt = generatePrompt.trim();
    if (!prompt) return setStatus({ message: "Describe the image you want to create.", kind: "error" });
    run("/api/generate", { prompt }, null);
  }

  function applyPreset(preset) {
    setEditPrompt(preset.prompt);
    if (source && !busy) runEdit(preset.prompt);
  }

  function continueEditing() {
    if (!result) return;
    const { image } = result;
    setSource({
      mimeType: image.mimeType,
      data: image.data,
      dataUrl: `data:${image.mimeType};base64,${image.data}`,
    });
    setTab("edit");
    setEditPrompt("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const resultDataUrl = result ? `data:${result.image.mimeType};base64,${result.image.data}` : null;
  const downloadExt = result
    ? (result.image.mimeType.split("/")[1] || "png").replace("jpeg", "jpg")
    : "png";

  return (
    <>
      <header>
        <h1>🍌 Nano Banana Photo Editor</h1>
        <p className="subtitle">Edit photos and create images with the Gemini image model</p>
        {health && !health.keyConfigured && (
          <div className="key-warning">
            ⚠ No API key configured on the server. Set <code>GEMINI_API_KEY</code> and restart.
          </div>
        )}
      </header>

      <main>
        <nav className="tabs">
          <button className={`tab ${tab === "edit" ? "active" : ""}`} onClick={() => setTab("edit")}>
            Edit a photo
          </button>
          <button className={`tab ${tab === "generate" ? "active" : ""}`} onClick={() => setTab("generate")}>
            Generate an image
          </button>
        </nav>

        {tab === "edit" && (
          <section className="panel">
            <div
              className={`dropzone ${dragOver ? "dragover" : ""}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragEnter={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={(e) => { e.preventDefault(); setDragOver(false); }}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); loadFile(e.dataTransfer.files[0]); }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                hidden
                onChange={(e) => loadFile(e.target.files[0])}
              />
              {source ? (
                <img className="source-preview" src={source.dataUrl} alt="Source" />
              ) : (
                <div>
                  <p className="drop-icon">🖼️</p>
                  <p><strong>Drop a photo here</strong> or click to browse</p>
                  <p className="hint">PNG, JPEG or WebP — up to 15 MB. You can also paste an image.</p>
                </div>
              )}
            </div>

            <div className="presets">
              <span className="presets-label">Quick edits:</span>
              {PRESETS.map((p) => (
                <button key={p.label} className="preset" onClick={() => applyPreset(p)}>
                  {p.label}
                </button>
              ))}
            </div>

            <div className="prompt-row">
              <textarea
                rows={2}
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                onKeyDown={(e) => (e.metaKey || e.ctrlKey) && e.key === "Enter" && runEdit()}
                placeholder='Describe your edit… e.g. "add a sunset sky", "put a party hat on the cat", "remove the person on the left"'
              />
              <button className="primary" disabled={busy || !source} onClick={() => runEdit()}>
                ✨ Apply edit
              </button>
            </div>
          </section>
        )}

        {tab === "generate" && (
          <section className="panel">
            <div className="prompt-row">
              <textarea
                rows={3}
                value={generatePrompt}
                onChange={(e) => setGeneratePrompt(e.target.value)}
                onKeyDown={(e) => (e.metaKey || e.ctrlKey) && e.key === "Enter" && runGenerate()}
                placeholder='Describe the image you want… e.g. "a photorealistic banana astronaut floating above Earth"'
              />
              <button className="primary" disabled={busy} onClick={runGenerate}>
                🎨 Generate
              </button>
            </div>
          </section>
        )}

        {status && <div className={`status ${status.kind}`}>{status.message}</div>}

        {result && (
          <section className="result" ref={resultRef}>
            <div className={`result-grid ${result.beforeDataUrl ? "" : "single"}`}>
              {result.beforeDataUrl && (
                <figure>
                  <figcaption>Before</figcaption>
                  <img src={result.beforeDataUrl} alt="Original" />
                </figure>
              )}
              <figure>
                <figcaption>After</figcaption>
                <img src={resultDataUrl} alt="Result" />
              </figure>
            </div>
            {result.text && <p className="model-note">{result.text}</p>}
            <div className="result-actions">
              <a className="primary" href={resultDataUrl} download={`nano-banana-result.${downloadExt}`}>
                ⬇ Download
              </a>
              <button onClick={continueEditing}>↪ Keep editing this result</button>
            </div>
          </section>
        )}
      </main>

      <footer>
        Powered by Gemini <span>{health?.model || "image model"}</span> (a.k.a. Nano Banana)
      </footer>
    </>
  );
}
