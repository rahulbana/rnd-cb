// Nano Banana Photo Editor — frontend logic.

const $ = (id) => document.getElementById(id);

const els = {
  tabs: { edit: $("tab-edit"), generate: $("tab-generate") },
  panels: { edit: $("panel-edit"), generate: $("panel-generate") },
  dropzone: $("dropzone"),
  dropzoneEmpty: $("dropzone-empty"),
  fileInput: $("file-input"),
  sourcePreview: $("source-preview"),
  editPrompt: $("edit-prompt"),
  editBtn: $("edit-btn"),
  generatePrompt: $("generate-prompt"),
  generateBtn: $("generate-btn"),
  status: $("status"),
  resultSection: $("result-section"),
  resultGrid: document.querySelector(".result-grid"),
  beforeFigure: $("before-figure"),
  beforeImg: $("before-img"),
  afterImg: $("after-img"),
  modelNote: $("model-note"),
  downloadBtn: $("download-btn"),
  continueBtn: $("continue-btn"),
  keyWarning: $("key-warning"),
  modelName: $("model-name"),
};

const MAX_FILE_BYTES = 15 * 1024 * 1024;

// Currently loaded source image: { mimeType, data (base64), dataUrl }
let sourceImage = null;
// Last result image, same shape, for "keep editing".
let resultImage = null;
let busy = false;

// ---- Server health / key check ----
fetch("/api/health")
  .then((r) => r.json())
  .then((h) => {
    if (!h.keyConfigured) els.keyWarning.classList.remove("hidden");
    if (h.model) els.modelName.textContent = h.model;
  })
  .catch(() => {});

// ---- Tabs ----
function switchTab(name) {
  for (const key of ["edit", "generate"]) {
    els.tabs[key].classList.toggle("active", key === name);
    els.panels[key].classList.toggle("hidden", key !== name);
  }
}
els.tabs.edit.addEventListener("click", () => switchTab("edit"));
els.tabs.generate.addEventListener("click", () => switchTab("generate"));

// ---- Image loading ----
function loadFile(file) {
  if (!file) return;
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
    showStatus("Please choose a PNG, JPEG or WebP image.", "error");
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    showStatus("Image is too large (max 15 MB).", "error");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const dataUrl = reader.result;
    setSourceImage({
      mimeType: file.type,
      data: dataUrl.split(",")[1],
      dataUrl,
    });
  };
  reader.readAsDataURL(file);
}

function setSourceImage(img) {
  sourceImage = img;
  els.sourcePreview.src = img.dataUrl;
  els.sourcePreview.classList.remove("hidden");
  els.dropzoneEmpty.classList.add("hidden");
  updateEditButton();
  hideStatus();
}

els.dropzone.addEventListener("click", () => els.fileInput.click());
els.fileInput.addEventListener("change", () => loadFile(els.fileInput.files[0]));

["dragover", "dragenter"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.remove("dragover");
  })
);
els.dropzone.addEventListener("drop", (e) => loadFile(e.dataTransfer.files[0]));

// Paste an image anywhere on the page
document.addEventListener("paste", (e) => {
  const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
  if (item) {
    switchTab("edit");
    loadFile(item.getAsFile());
  }
});

// ---- Presets ----
$("presets").addEventListener("click", (e) => {
  const btn = e.target.closest(".preset");
  if (!btn) return;
  els.editPrompt.value = btn.dataset.prompt;
  if (sourceImage && !busy) runEdit();
});

// ---- Status helpers ----
function showStatus(message, kind) {
  els.status.textContent = message;
  els.status.className = "status" + (kind ? " " + kind : "");
  els.status.classList.remove("hidden");
}

function hideStatus() {
  els.status.classList.add("hidden");
}

function setBusy(value) {
  busy = value;
  els.generateBtn.disabled = value;
  updateEditButton();
}

function updateEditButton() {
  els.editBtn.disabled = busy || !sourceImage;
}

// ---- API calls ----
async function callApi(route, payload) {
  const response = await fetch(route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (HTTP ${response.status})`);
  return data;
}

function showResult({ image, text }, beforeDataUrl) {
  const dataUrl = `data:${image.mimeType};base64,${image.data}`;
  resultImage = { mimeType: image.mimeType, data: image.data, dataUrl };

  if (beforeDataUrl) {
    els.beforeImg.src = beforeDataUrl;
    els.beforeFigure.classList.remove("hidden");
    els.resultGrid.classList.remove("single");
  } else {
    els.beforeFigure.classList.add("hidden");
    els.resultGrid.classList.add("single");
  }

  els.afterImg.src = dataUrl;
  els.downloadBtn.href = dataUrl;
  const ext = (image.mimeType.split("/")[1] || "png").replace("jpeg", "jpg");
  els.downloadBtn.download = `nano-banana-result.${ext}`;

  els.modelNote.classList.toggle("hidden", !text);
  els.modelNote.textContent = text || "";

  els.resultSection.classList.remove("hidden");
  els.resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  hideStatus();
}

async function runEdit() {
  const prompt = els.editPrompt.value.trim();
  if (!sourceImage) return showStatus("Add a photo first.", "error");
  if (!prompt) return showStatus("Describe the edit you want.", "error");

  setBusy(true);
  showStatus("Editing your photo… this usually takes a few seconds.", "loading");
  try {
    const data = await callApi("/api/edit", {
      prompt,
      image: { mimeType: sourceImage.mimeType, data: sourceImage.data },
    });
    showResult(data, sourceImage.dataUrl);
  } catch (e) {
    showStatus(e.message, "error");
  } finally {
    setBusy(false);
  }
}

async function runGenerate() {
  const prompt = els.generatePrompt.value.trim();
  if (!prompt) return showStatus("Describe the image you want to create.", "error");

  setBusy(true);
  showStatus("Generating your image… this usually takes a few seconds.", "loading");
  try {
    const data = await callApi("/api/generate", { prompt });
    showResult(data, null);
  } catch (e) {
    showStatus(e.message, "error");
  } finally {
    setBusy(false);
  }
}

els.editBtn.addEventListener("click", runEdit);
els.generateBtn.addEventListener("click", runGenerate);

// Ctrl/Cmd+Enter submits from either textarea
els.editPrompt.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") runEdit();
});
els.generatePrompt.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") runGenerate();
});

// "Keep editing this result" feeds the output back in as the new source
els.continueBtn.addEventListener("click", () => {
  if (!resultImage) return;
  setSourceImage(resultImage);
  switchTab("edit");
  els.editPrompt.value = "";
  els.editPrompt.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
