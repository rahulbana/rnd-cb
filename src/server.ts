import express, { type Request, type Response } from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { config } from "./config.js";
import { countTokens, MODEL } from "./anthropic.js";
import { buildSystemPrompt, buildUserPrompt } from "./prompts.js";
import { extractStructured, summarizeStreaming } from "./summarizer.js";
import {
  SUMMARY_FORMATS,
  SUMMARY_LENGTHS,
  SUMMARY_STYLES,
  type StreamEvent,
  type SummarizeOptions,
  type SummaryFormat,
  type SummaryLength,
  type SummaryStyle,
} from "./types.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(here, "..", "public");

const app = express();
// Documents can be large; allow generous JSON bodies.
app.use(express.json({ limit: "25mb" }));
app.use(express.static(publicDir));

const MAX_INPUT_CHARS = 5_000_000; // ~1.25M tokens — a hard guard against runaway inputs

/** Validate and normalize the request body into SummarizeOptions. */
function parseOptions(body: unknown): SummarizeOptions | { error: string } {
  const b = (body ?? {}) as Record<string, unknown>;
  const text = typeof b.text === "string" ? b.text : "";
  if (!text.trim()) return { error: "No text provided." };
  if (text.length > MAX_INPUT_CHARS) {
    return { error: `Input too large (${text.length} chars; max ${MAX_INPUT_CHARS}).` };
  }

  const length = (b.length as SummaryLength) ?? "medium";
  const style = (b.style as SummaryStyle) ?? "neutral";
  const format = (b.format as SummaryFormat) ?? "paragraph";

  if (!SUMMARY_LENGTHS.includes(length)) return { error: `Invalid length: ${length}` };
  if (!SUMMARY_STYLES.includes(style)) return { error: `Invalid style: ${style}` };
  if (!SUMMARY_FORMATS.includes(format)) return { error: `Invalid format: ${format}` };

  const focus = typeof b.focus === "string" ? b.focus : undefined;
  return { text, length, style, format, focus };
}

/** Expose the option vocabulary and active model so the UI can render itself. */
app.get("/api/config", (_req: Request, res: Response) => {
  res.json({
    model: MODEL,
    lengths: SUMMARY_LENGTHS,
    styles: SUMMARY_STYLES,
    formats: SUMMARY_FORMATS,
  });
});

/** Token estimate for the exact request that would be sent, without running it. */
app.post("/api/count-tokens", async (req: Request, res: Response) => {
  const parsed = parseOptions(req.body);
  if ("error" in parsed) {
    res.status(400).json({ error: parsed.error });
    return;
  }
  try {
    const system = buildSystemPrompt(parsed);
    const user = buildUserPrompt(parsed.text);
    const inputTokens = await countTokens(system, user);
    res.json({ inputTokens, model: MODEL });
  } catch (err) {
    res.status(500).json({ error: errorMessage(err) });
  }
});

/** Streaming summary. Emits newline-delimited JSON (NDJSON) StreamEvents. */
app.post("/api/summarize", async (req: Request, res: Response) => {
  const parsed = parseOptions(req.body);
  if ("error" in parsed) {
    res.status(400).json({ error: parsed.error });
    return;
  }

  res.setHeader("Content-Type", "application/x-ndjson; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("X-Accel-Buffering", "no");

  const emit = (event: StreamEvent) => {
    res.write(JSON.stringify(event) + "\n");
  };

  try {
    await summarizeStreaming(parsed, emit);
  } catch (err) {
    emit({ type: "error", message: errorMessage(err) });
  } finally {
    res.end();
  }
});

/** Structured JSON extraction (non-streaming). */
app.post("/api/extract", async (req: Request, res: Response) => {
  const b = (req.body ?? {}) as Record<string, unknown>;
  const text = typeof b.text === "string" ? b.text : "";
  if (!text.trim()) {
    res.status(400).json({ error: "No text provided." });
    return;
  }
  if (text.length > MAX_INPUT_CHARS) {
    res.status(400).json({ error: "Input too large." });
    return;
  }
  try {
    const structured = await extractStructured(text);
    res.json(structured);
  } catch (err) {
    res.status(500).json({ error: errorMessage(err) });
  }
});

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

app.listen(config.port, () => {
  console.log(`AI Text Summarizer running at http://localhost:${config.port}`);
  console.log(`Model: ${MODEL}`);
});
