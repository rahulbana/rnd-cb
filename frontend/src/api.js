// Thin wrapper around the backend API. Requests go through Vite's /api proxy.

export async function uploadTranscript(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/upload", { method: "POST", body: form });
  if (!res.ok) {
    const { detail } = await res.json().catch(() => ({}));
    throw new Error(detail || "Upload failed.");
  }
  return res.json();
}

export async function generateNotes(transcript, meetingTitle) {
  const res = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript, meeting_title: meetingTitle || null }),
  });
  if (!res.ok) {
    const { detail } = await res.json().catch(() => ({}));
    throw new Error(detail || "Failed to generate notes.");
  }
  return res.json();
}
