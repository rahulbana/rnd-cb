// Thin API client for the resume-rating backend.

async function handle(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore JSON parse errors and keep the default message
    }
    throw new Error(detail);
  }
  return res.json();
}

// Rate a resume supplied as plain text.
export async function rateText(resume, jobDescription) {
  const res = await fetch("/api/rate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume, job_description: jobDescription }),
  });
  return handle(res);
}

// Rate a resume supplied as an uploaded file (PDF or text).
export async function rateFile(file, jobDescription) {
  const form = new FormData();
  form.append("resume_file", file);
  form.append("job_description", jobDescription);
  const res = await fetch("/api/rate-file", { method: "POST", body: form });
  return handle(res);
}
