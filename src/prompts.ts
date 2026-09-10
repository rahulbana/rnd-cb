import type {
  SummarizeOptions,
  SummaryFormat,
  SummaryLength,
  SummaryStyle,
} from "./types.js";

// ---------------------------------------------------------------------------
// Prompt engineering lives here. The system prompt is assembled from small,
// composable instruction fragments — one per length, style, and format — so the
// behavior of each knob is explicit and easy to tune in isolation.
// ---------------------------------------------------------------------------

const LENGTH_GUIDANCE: Record<SummaryLength, string> = {
  short:
    "Length: SHORT. Distill to the essential message in 2–4 sentences (or 3–5 bullets). Ruthlessly cut detail; keep only what a reader needs to grasp the core.",
  medium:
    "Length: MEDIUM. Aim for one to three tight paragraphs (or 5–9 bullets). Cover the main points and the most important supporting detail, nothing more.",
  detailed:
    "Length: DETAILED. Produce a thorough, well-organized summary that preserves the key arguments, evidence, caveats, and structure of the source. Use multiple paragraphs or sections. Still summarize — do not reproduce the text verbatim.",
};

const STYLE_GUIDANCE: Record<SummaryStyle, string> = {
  neutral:
    "Style: NEUTRAL. Clear, plain, objective language. No jargon unless the source requires it.",
  executive:
    "Style: EXECUTIVE. Write for a busy decision-maker. Lead with conclusions and implications, quantify where possible, and foreground risks, costs, and recommended actions.",
  technical:
    "Style: TECHNICAL. Precise and detail-oriented. Preserve technical terms, mechanisms, parameters, and trade-offs accurately. Assume a knowledgeable reader.",
  academic:
    "Style: ACADEMIC. Formal and measured. Note methodology, evidence, and limitations; distinguish claims from findings.",
  casual:
    "Style: CASUAL. Friendly, conversational, and approachable, as if explaining to a smart friend. Keep it accurate.",
  eli5:
    "Style: SIMPLE (ELI5). Explain as if to a curious beginner. Use everyday words and short sentences; unpack jargon into plain language.",
};

const FORMAT_GUIDANCE: Record<SummaryFormat, string> = {
  paragraph:
    "Format: PARAGRAPH. Write flowing prose. Do not use bullet points or headings.",
  bullets:
    "Format: BULLET POINTS. Return a single markdown bullet list ('- '). Each bullet is one self-contained idea. No introductory or closing sentence.",
  "key-points":
    "Format: KEY POINTS. Extract the most important takeaways as a markdown bullet list, ordered by importance (most important first). Each point must be specific and stand on its own.",
  structured:
    [
      "Format: STRUCTURED EXECUTIVE REPORT. Use these markdown H2 sections, in this order, and omit any section with no relevant content:",
      "## Executive Summary — 2–4 sentences capturing the essence.",
      "## Key Findings — bullet list of the most important facts, results, or arguments.",
      "## Important Decisions — bullet list of decisions made or proposed (omit if none).",
      "## Action Items — bullet list of concrete next steps, each starting with a verb (omit if none).",
    ].join("\n"),
};

const BASE_SYSTEM = [
  "You are an expert text summarizer. You read a source document and produce a faithful, useful summary.",
  "",
  "Rules:",
  "- Be accurate. Never invent facts, figures, names, or conclusions that are not supported by the source.",
  "- Preserve the source's meaning and intent; do not inject your own opinions.",
  "- If the source is ambiguous or incomplete, summarize what is there rather than guessing.",
  "- Write in the same language as the source document.",
  "- Output only the summary itself — no preamble like 'Here is the summary', no meta-commentary.",
].join("\n");

/** Build the system prompt for a normal (single-document) summary request. */
export function buildSystemPrompt(
  opts: Pick<SummarizeOptions, "length" | "style" | "format" | "focus">,
): string {
  const parts = [
    BASE_SYSTEM,
    "",
    "Apply the following constraints:",
    LENGTH_GUIDANCE[opts.length],
    STYLE_GUIDANCE[opts.style],
    FORMAT_GUIDANCE[opts.format],
  ];
  if (opts.focus && opts.focus.trim()) {
    parts.push(
      `Focus: The reader specifically wants you to emphasize: ${opts.focus.trim()}`,
    );
  }
  return parts.join("\n");
}

/** Wrap the source text with clear delimiters so instructions can't be confused with content. */
export function buildUserPrompt(text: string): string {
  return [
    "Summarize the document below, delimited by <document> tags.",
    "",
    "<document>",
    text,
    "</document>",
  ].join("\n");
}

// ---------------------------------------------------------------------------
// Map-reduce prompts, used when a document is too large for a single pass.
// ---------------------------------------------------------------------------

/** "Map" step: neutrally condense one chunk while keeping detail for later synthesis. */
export function buildMapSystemPrompt(): string {
  return [
    "You are summarizing ONE section of a larger document that has been split into parts.",
    "Condense this section faithfully, preserving all key facts, figures, names, decisions, and action items.",
    "Do not add conclusions about the whole document — you are only seeing one part.",
    "Return a compact but information-dense summary as markdown bullet points.",
    "Output only the bullets, no preamble.",
  ].join("\n");
}

export function buildMapUserPrompt(
  chunk: string,
  index: number,
  total: number,
): string {
  return [
    `This is section ${index} of ${total}.`,
    "",
    "<section>",
    chunk,
    "</section>",
  ].join("\n");
}

/** "Reduce" step: synthesize the per-chunk summaries into the final requested summary. */
export function buildReduceSystemPrompt(
  opts: Pick<SummarizeOptions, "length" | "style" | "format" | "focus">,
): string {
  const parts = [
    "You are synthesizing a final summary from ordered section summaries of a single large document.",
    "Treat the section summaries as your source material. Merge overlapping points, resolve redundancy, and produce one coherent summary of the whole document.",
    "Do not mention that the document was split into sections.",
    "",
    "Apply the following constraints:",
    LENGTH_GUIDANCE[opts.length],
    STYLE_GUIDANCE[opts.style],
    FORMAT_GUIDANCE[opts.format],
  ];
  if (opts.focus && opts.focus.trim()) {
    parts.push(
      `Focus: The reader specifically wants you to emphasize: ${opts.focus.trim()}`,
    );
  }
  parts.push("", "Output only the summary itself — no preamble.");
  return parts.join("\n");
}

export function buildReduceUserPrompt(sectionSummaries: string[]): string {
  const joined = sectionSummaries
    .map((s, i) => `### Section ${i + 1}\n${s}`)
    .join("\n\n");
  return [
    "Here are the ordered section summaries of the document:",
    "",
    "<sections>",
    joined,
    "</sections>",
    "",
    "Write the final summary of the entire document.",
  ].join("\n");
}
