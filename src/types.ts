// Shared option vocabulary for the summarizer. Kept in one place so the server,
// the prompt builder, and the frontend all agree on the same strings.

export type SummaryLength = "short" | "medium" | "detailed";

export type SummaryStyle =
  | "neutral"
  | "executive"
  | "technical"
  | "academic"
  | "casual"
  | "eli5";

export type SummaryFormat =
  | "paragraph" // flowing prose
  | "bullets" // concise bullet points
  | "key-points" // extracted key takeaways
  | "structured"; // executive report: Summary / Key Findings / Decisions / Action Items

export interface SummarizeOptions {
  text: string;
  length: SummaryLength;
  style: SummaryStyle;
  format: SummaryFormat;
  /** Optional free-text steer, e.g. "focus on the security implications". */
  focus?: string;
}

export const SUMMARY_LENGTHS: SummaryLength[] = ["short", "medium", "detailed"];
export const SUMMARY_STYLES: SummaryStyle[] = [
  "neutral",
  "executive",
  "technical",
  "academic",
  "casual",
  "eli5",
];
export const SUMMARY_FORMATS: SummaryFormat[] = [
  "paragraph",
  "bullets",
  "key-points",
  "structured",
];

/** NDJSON events streamed from the server to the browser over a single POST. */
export type StreamEvent =
  | { type: "status"; message: string }
  | { type: "meta"; inputTokens: number; strategy: "single-pass" | "map-reduce"; chunks?: number }
  | { type: "delta"; text: string }
  | { type: "done"; outputTokens: number; inputTokens: number }
  | { type: "error"; message: string };
