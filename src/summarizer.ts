import { client, countTokens, MODEL } from "./anthropic.js";
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

const STREAM_MAX_TOKENS = 64_000; // generous ceiling for streamed output
const MAP_MAX_TOKENS = 8_000; // per-chunk condensations stay compact

/** Pull the concatenated text out of a non-streaming message response. */
function textOf(message: { content: Array<{ type: string }> }): string {
  return (message.content as Array<{ type: string; text?: string }>)
    .filter((b) => b.type === "text")
    .map((b) => b.text ?? "")
    .join("");
}

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
  const inputTokens = await countTokens(system, user);

  if (inputTokens <= config.chunkThresholdTokens) {
    emit({ type: "meta", inputTokens, strategy: "single-pass" });
    await singlePass(system, user, inputTokens, emit);
  } else {
    await mapReduce(opts, inputTokens, emit);
  }
}

async function singlePass(
  system: string,
  user: string,
  inputTokens: number,
  emit: Emit,
): Promise<void> {
  emit({ type: "status", message: "Generating summary…" });

  const stream = client.messages.stream({
    model: MODEL,
    max_tokens: STREAM_MAX_TOKENS,
    output_config: { effort: "medium" },
    system,
    messages: [{ role: "user", content: user }],
  });

  for await (const event of stream) {
    if (
      event.type === "content_block_delta" &&
      event.delta.type === "text_delta"
    ) {
      emit({ type: "delta", text: event.delta.text });
    }
  }

  const final = await stream.finalMessage();
  emit({
    type: "done",
    outputTokens: final.usage.output_tokens,
    inputTokens,
  });
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

  // MAP: condense each chunk. Runs at low effort — these are throwaway
  // intermediate summaries, so favor speed and cost.
  const mapSystem = buildMapSystemPrompt();
  const sectionSummaries: string[] = [];
  for (let i = 0; i < chunks.length; i++) {
    emit({
      type: "status",
      message: `Summarizing section ${i + 1} of ${chunks.length}…`,
    });
    const res = await client.messages.create({
      model: MODEL,
      max_tokens: MAP_MAX_TOKENS,
      output_config: { effort: "low" },
      system: mapSystem,
      messages: [
        { role: "user", content: buildMapUserPrompt(chunks[i], i + 1, chunks.length) },
      ],
    });
    sectionSummaries.push(textOf(res));
  }

  // REDUCE: synthesize the final, formatted summary from the section summaries,
  // streaming the result to the client.
  emit({ type: "status", message: "Synthesizing final summary…" });
  const reduceSystem = buildReduceSystemPrompt(opts);
  const reduceUser = buildReduceUserPrompt(sectionSummaries);

  const stream = client.messages.stream({
    model: MODEL,
    max_tokens: STREAM_MAX_TOKENS,
    output_config: { effort: "medium" },
    system: reduceSystem,
    messages: [{ role: "user", content: reduceUser }],
  });

  for await (const event of stream) {
    if (
      event.type === "content_block_delta" &&
      event.delta.type === "text_delta"
    ) {
      emit({ type: "delta", text: event.delta.text });
    }
  }

  const final = await stream.finalMessage();
  emit({
    type: "done",
    outputTokens: final.usage.output_tokens,
    inputTokens,
  });
}

// ---------------------------------------------------------------------------
// Structured extraction: a non-streaming request that returns machine-readable
// JSON. Demonstrates coaxing structured output from the model via a strict
// prompt contract, then parsing it defensively.
// ---------------------------------------------------------------------------

export interface StructuredSummary {
  title: string;
  summary: string;
  keyPoints: string[];
  decisions: string[];
  actionItems: string[];
  entities: string[];
}

const EXTRACT_SYSTEM = [
  "You extract structured information from a document and return it as JSON.",
  "Respond with a SINGLE JSON object and nothing else — no markdown fences, no prose.",
  "The object must match exactly this shape:",
  "{",
  '  "title": string,            // a concise title for the document',
  '  "summary": string,          // 2-4 sentence overview',
  '  "keyPoints": string[],      // most important takeaways, ordered by importance',
  '  "decisions": string[],      // decisions made or proposed (empty array if none)',
  '  "actionItems": string[],    // concrete next steps, each starting with a verb (empty if none)',
  '  "entities": string[]        // notable people, orgs, products, or places mentioned',
  "}",
  "Base every field strictly on the document; never invent content. Use empty arrays where nothing applies.",
].join("\n");

/** Extract a structured summary object from text (non-streaming). */
export async function extractStructured(
  text: string,
): Promise<StructuredSummary> {
  const res = await client.messages.create({
    model: MODEL,
    max_tokens: 8_000,
    output_config: { effort: "medium" },
    system: EXTRACT_SYSTEM,
    messages: [
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

  return parseStructured(textOf(res));
}

/** Parse the model's JSON defensively, tolerating stray fences or surrounding text. */
function parseStructured(raw: string): StructuredSummary {
  let jsonText = raw.trim();

  // Strip ```json ... ``` fences if the model added them despite instructions.
  const fence = jsonText.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) jsonText = fence[1].trim();

  // Otherwise, grab the outermost {...} span.
  if (!jsonText.startsWith("{")) {
    const start = jsonText.indexOf("{");
    const end = jsonText.lastIndexOf("}");
    if (start !== -1 && end !== -1) jsonText = jsonText.slice(start, end + 1);
  }

  let parsed: Partial<StructuredSummary>;
  try {
    parsed = JSON.parse(jsonText);
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
