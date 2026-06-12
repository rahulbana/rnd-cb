// Nano Banana Photo Editor — zero-dependency Node.js server.
// Serves the static frontend and proxies image edit/generate requests
// to the Gemini API so the API key never reaches the browser.

import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(__dirname, "public");

const PORT = process.env.PORT || 3000;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
// "Nano Banana" is the nickname of Gemini's image generation/editing model.
const MODEL = process.env.GEMINI_IMAGE_MODEL || "gemini-2.5-flash-image";
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`;

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

// Max request body: base64-encoded images get big, allow ~25 MB.
const MAX_BODY_BYTES = 25 * 1024 * 1024;

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error("Request body too large (max 25 MB)"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

async function callGemini(parts) {
  if (!GEMINI_API_KEY) {
    const err = new Error(
      "GEMINI_API_KEY is not set. Get a key at https://aistudio.google.com/apikey and run: GEMINI_API_KEY=your-key npm start"
    );
    err.status = 500;
    throw err;
  }

  const response = await fetch(GEMINI_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": GEMINI_API_KEY,
    },
    body: JSON.stringify({
      contents: [{ parts }],
      generationConfig: { responseModalities: ["IMAGE", "TEXT"] },
    }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = new Error(data?.error?.message || `Gemini API error (HTTP ${response.status})`);
    err.status = response.status;
    throw err;
  }

  const candidate = data?.candidates?.[0];
  const outParts = candidate?.content?.parts || [];
  const imagePart = outParts.find((p) => p.inlineData?.data);
  const textPart = outParts.find((p) => typeof p.text === "string");

  if (!imagePart) {
    const reason = candidate?.finishReason;
    const err = new Error(
      textPart?.text ||
        (reason ? `Model returned no image (finish reason: ${reason})` : "Model returned no image")
    );
    err.status = 502;
    throw err;
  }

  return {
    mimeType: imagePart.inlineData.mimeType || "image/png",
    data: imagePart.inlineData.data,
    text: textPart?.text || null,
  };
}

// POST /api/edit   { prompt, image: { mimeType, data } }
// POST /api/generate { prompt }
async function handleApi(req, res, route) {
  let payload;
  try {
    payload = JSON.parse((await readBody(req)).toString("utf-8"));
  } catch (e) {
    return sendJson(res, 400, { error: e.message || "Invalid JSON body" });
  }

  const prompt = (payload.prompt || "").trim();
  if (!prompt) return sendJson(res, 400, { error: "A prompt is required" });

  const parts = [{ text: prompt }];
  if (route === "edit") {
    const image = payload.image;
    if (!image?.data || !image?.mimeType) {
      return sendJson(res, 400, { error: "An image ({ mimeType, data }) is required for editing" });
    }
    parts.push({ inlineData: { mimeType: image.mimeType, data: image.data } });
  }

  try {
    const result = await callGemini(parts);
    sendJson(res, 200, { image: { mimeType: result.mimeType, data: result.data }, text: result.text });
  } catch (e) {
    sendJson(res, e.status && e.status >= 400 ? e.status : 500, { error: e.message });
  }
}

async function serveStatic(res, urlPath) {
  const safePath = path.normalize(urlPath === "/" ? "/index.html" : urlPath).replace(/^(\.\.[/\\])+/, "");
  const filePath = path.join(PUBLIC_DIR, safePath);
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403).end("Forbidden");
    return;
  }
  try {
    const content = await readFile(filePath);
    res.writeHead(200, { "Content-Type": MIME_TYPES[path.extname(filePath)] || "application/octet-stream" });
    res.end(content);
  } catch {
    res.writeHead(404).end("Not found");
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === "POST" && url.pathname === "/api/edit") return handleApi(req, res, "edit");
  if (req.method === "POST" && url.pathname === "/api/generate") return handleApi(req, res, "generate");
  if (req.method === "GET" && url.pathname === "/api/health") {
    return sendJson(res, 200, { ok: true, model: MODEL, keyConfigured: Boolean(GEMINI_API_KEY) });
  }
  if (req.method === "GET" || req.method === "HEAD") return serveStatic(res, url.pathname);

  sendJson(res, 405, { error: "Method not allowed" });
});

server.listen(PORT, () => {
  console.log(`🍌 Nano Banana Photo Editor running at http://localhost:${PORT}`);
  console.log(`   Model: ${MODEL}`);
  if (!GEMINI_API_KEY) {
    console.warn("   ⚠ GEMINI_API_KEY is not set — API calls will fail until you provide one.");
    console.warn("     Get a key at https://aistudio.google.com/apikey");
  }
});
