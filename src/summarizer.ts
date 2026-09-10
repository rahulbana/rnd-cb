import type OpenAI from "openai";
import { getClient, countTokens, MODEL } from "./openai.js";
import { config } from "./config.js";
import { chunkText } from "./chunking.js";
import {
  buildMapSystemPrompt,
  buildMapUserPrompt,
  buildReduceSystemPrompt,
  buildReduceUserPrompt,
  buildSystemPrompt,
  buildUserPrompt,
} from "./prompts.js";
import type { SummarizeOptions, StreamEvent } from "./types.js";

type Emit = (event: StreamEvent) => void;

const STREAM_MAX_TOKENS = 4_096; // generous ceiling for a streamed summary
const MAP_MAX_TOKENS = 1_500; // per-chunk condensations stay compact
const SUMMARY_TEMPERATURE = 0.3; // focused, low-variance summaries

type ChatMessage = OpenAI.Chat.Completions.ChatCompletionMessageParam;

/**
 * Summarize `opts.text`, streaming the result out through `emit`. Chooses a
 * single-pass request when the input fits comfortably, and a chunked map-reduce
 * pass when it does not.
 */
export async function summarizeStreaming(
  opts: SummarizeOptions,
  emit: Emit,
): Promise<void> {
  const system = buildSystemPrompt(opts);
  const user = buildUserPrompt(opts.text);

  emit({ type: "status", message: "Counting tokens…" });
  const inputTokens = countTokens(system, user);

  if (inputTokens <= config.chunkThresholdTokens) {
    emit({ type: "meta", inputTokens, strategy: "single-pass" });
    await singlePass(system, user, inputTokens, emit);
  } else {
    await mapReduce(opts, inputTokens, emit);
  }
}

/** Stream one chat completion, emitting text deltas. Returns output token count. */
async function streamSummary(
  messages: ChatMessage[],
  emit: Emit,
): Promise<number> {
  const stream = await getClient().chat.completions.create({
    model: MODEL,
    messages,
    temperature: SUMMARY_TEMPERATURE,
    max_tokens: STREAM_MAX_TOKENS,
    stream: true,
    stream_options: { include_usage: true },
  });

  let outputTokens = 0;
  for await (const chunk of stream) {
    const text = chunk.choices[0]?.delta?.content;
    if (text) emit({ type: "delta", text });
    // The final chunk carries usage (choices is empty there).
    if (chunk.usage) outputTokens = chunk.usage.completion_tokens;
  }
  return outputTokens;
}

async function singlePass(
  system: string,
  user: string,
  inputTokens: number,
  emit: Emit,
): Promise<void> {
  emit({ type: "status", message: "Generating summary…" });
  const outputTokens = await streamSummary(
    [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
    emit,
  );
  emit({ type: "done", outputTokens, inputTokens });
}

async function mapReduce(
  opts: SummarizeOptions,
  inputTokens: number,
  emit: Emit,
): Promise<void> {
  const chunks = chunkText(opts.text, config.charsPerChunk);
  emit({
    type: "meta",
    inputTokens,
    strategy: "map-reduce",
    chunks: chunks.length,
  });
  emit({
    type: "status",
    message: `Document is large (~${inputTokens.toLocaleString()} tokens). Splitting into ${chunks.length} sections.`,
  });

  // MAP: condense each chunk. These are throwaway intermediate summaries, so
  // favor speed with a low temperature and a tight output cap.
  const mapSystem = buildMapSystemPrompt();
  const sectionSummaries: string[] = [];
  for (let i = 0; i < chunks.length; i++) {
    emit({
      type: "status",
      message: `Summarizing section ${i + 1} of ${chunks.length}…`,
    });
    const res = await getClient().chat.completions.create({
      model: MODEL,
      temperature: 0.2,
      max_tokens: MAP_MAX_TOKENS,
      messages: [
        { role: "system", content: mapSystem },
        {
          role: "user",
          content: buildMapUserPrompt(chunks[i], i + 1, chunks.length),
        },
      ],
    });
    sectionSummaries.push(res.choices[0]?.message?.content ?? "");
  }

  // REDUCE: synthesize the final, formatted summary from the section summaries,
  // streaming the result to the client.
  emit({ type: "status", message: "Synthesizing final summary…" });
  const outputTokens = await streamSummary(
    [
      { role: "system", content: buildReduceSystemPrompt(opts) },
      { role: "user", content: buildReduceUserPrompt(sectionSummaries) },
    ],
    emit,
  );
  emit({ type: "done", outputTokens, inputTokens });
}

// ---------------------------------------------------------------------------
// Structured extraction: a non-streaming request that returns machine-readable
// JSON. Uses OpenAI Structured Outputs (response_format json_schema, strict),
// which guarantees the model's output conforms to the schema.
// ---------------------------------------------------------------------------

export interface StructuredSummary {
  title: string;
  summary: string;
  keyPoints: string[];
  decisions: string[];
  actionItems: string[];
  entities: string[];
}

const EXTRACT_SYSTEM =
  "You extract structured information from a document. Base every field strictly on the document; never invent content. Use empty arrays where nothing applies.";

// JSON Schema for Structured Outputs. `strict: true` requires every property to
// be listed in `required` and additionalProperties to be false.
const EXTRACT_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    title: { type: "string", description: "A concise title for the document." },
    summary: { type: "string", description: "A 2-4 sentence overview." },
    keyPoints: {
      type: "array",
      items: { type: "string" },
      description: "Most important takeaways, ordered by importance.",
    },
    decisions: {
      type: "array",
      items: { type: "string" },
      description: "Decisions made or proposed (empty if none).",
    },
    actionItems: {
      type: "array",
      items: { type: "string" },
      description: "Concrete next steps, each starting with a verb (empty if none).",
    },
    entities: {
      type: "array",
      items: { type: "string" },
      description: "Notable people, orgs, products, or places mentioned.",
    },
  },
  required: [
    "title",
    "summary",
    "keyPoints",
    "decisions",
    "actionItems",
    "entities",
  ],
} as const;

/** Extract a structured summary object from text (non-streaming). */
export async function extractStructured(
  text: string,
): Promise<StructuredSummary> {
  const res = await getClient().chat.completions.create({
    model: MODEL,
    temperature: 0.2,
    max_tokens: 2_000,
    response_format: {
      type: "json_schema",
      json_schema: {
        name: "structured_summary",
        strict: true,
        schema: EXTRACT_SCHEMA,
      },
    },
    messages: [
      { role: "system", content: EXTRACT_SYSTEM },
      {
        role: "user",
        content: [
          "Extract structured information from the document below.",
          "",
          "<document>",
          text,
          "</document>",
        ].join("\n"),
      },
    ],
  });

  const raw = res.choices[0]?.message?.content ?? "";
  let parsed: Partial<StructuredSummary>;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("Model did not return valid JSON for structured extraction.");
  }

  const asStringArray = (v: unknown): string[] =>
    Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];

  return {
    title: typeof parsed.title === "string" ? parsed.title : "Untitled",
    summary: typeof parsed.summary === "string" ? parsed.summary : "",
    keyPoints: asStringArray(parsed.keyPoints),
    decisions: asStringArray(parsed.decisions),
    actionItems: asStringArray(parsed.actionItems),
    entities: asStringArray(parsed.entities),
  };
}
