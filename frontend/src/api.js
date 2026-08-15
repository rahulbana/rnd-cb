// REST + WebSocket helpers. Relative paths are proxied to the backend by Vite.

function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}${path}`;
}

export async function getConfig() {
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error("Failed to load config");
  return res.json();
}

export async function listSources() {
  const res = await fetch("/api/sources");
  return res.json();
}

export async function deleteSource(source) {
  const res = await fetch(`/api/sources/${encodeURIComponent(source)}`, {
    method: "DELETE",
  });
  return res.json();
}

// Upload a file, then stream ingestion progress over a WebSocket.
// onEvent receives each parsed event object.
export async function ingestFile(file, onEvent) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  const { job_id } = await res.json();
  return streamIngest(job_id, onEvent);
}

export async function ingestText(text, name, onEvent) {
  const res = await fetch("/api/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, name }),
  });
  if (!res.ok) throw new Error("Text upload failed");
  const { job_id } = await res.json();
  return streamIngest(job_id, onEvent);
}

function streamIngest(jobId, onEvent) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl(`/ws/ingest/${jobId}`));
    ws.onmessage = (ev) => {
      const event = JSON.parse(ev.data);
      onEvent(event);
      if (event.type === "done") {
        ws.close();
        resolve();
      } else if (event.type === "error") {
        ws.close();
        reject(new Error(event.detail || "Ingestion error"));
      }
    };
    ws.onerror = () => reject(new Error("WebSocket error during ingestion"));
  });
}

// A persistent chat socket. Returns a controller with `ask` and `close`.
export function openChatSocket({ onEvent, onOpen, onClose }) {
  const ws = new WebSocket(wsUrl("/ws/chat"));
  ws.onopen = () => onOpen && onOpen();
  ws.onclose = () => onClose && onClose();
  ws.onmessage = (ev) => onEvent(JSON.parse(ev.data));
  return {
    ask(query, options) {
      ws.send(JSON.stringify({ query, options }));
    },
    close() {
      ws.close();
    },
    get ready() {
      return ws.readyState === WebSocket.OPEN;
    },
    socket: ws,
  };
}
