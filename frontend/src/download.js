// Client-side download helpers — lightweight, no extra dependencies.

function triggerDownload(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function slug(plan) {
  const r = plan.request;
  return `study-plan-${r.subject}-${r.topic}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function downloadMarkdown(plan) {
  triggerDownload(`${slug(plan)}.md`, plan.markdown, "text/markdown");
}

export function downloadJSON(plan) {
  triggerDownload(
    `${slug(plan)}.json`,
    JSON.stringify(plan, null, 2),
    "application/json"
  );
}

// "Download" as PDF via the browser's print dialog (Save as PDF).
export function downloadPDF() {
  window.print();
}
