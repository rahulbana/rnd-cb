export type SummaryLength = "short" | "medium" | "detailed";
export type SummaryStyle =
  | "neutral"
  | "executive"
  | "technical"
  | "academic"
  | "casual"
  | "eli5";
export type SummaryFormat = "paragraph" | "bullets" | "key-points" | "structured";

export interface SummarizeOptions {
  text: string;
  length: SummaryLength;
  style: SummaryStyle;
  format: SummaryFormat;
  focus?: string;
}

export interface AppConfig {
  model: string;
  lengths: SummaryLength[];
  styles: SummaryStyle[];
  formats: SummaryFormat[];
}

export interface StructuredSummary {
  title: string;
  summary: string;
  keyPoints: string[];
  decisions: string[];
  actionItems: string[];
  entities: string[];
}

/** NDJSON events streamed from the backend over a single POST. */
export type StreamEvent =
  | { type: "status"; message: string }
  | {
      type: "meta";
      inputTokens: number;
      strategy: "single-pass" | "map-reduce";
      chunks?: number;
    }
  | { type: "delta"; text: string }
  | { type: "done"; outputTokens: number; inputTokens: number }
  | { type: "error"; message: string };
