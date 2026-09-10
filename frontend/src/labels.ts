import type { SummaryFormat, SummaryLength, SummaryStyle } from "./types";

export const LENGTH_LABELS: Record<SummaryLength, string> = {
  short: "Short",
  medium: "Medium",
  detailed: "Detailed",
};

export const STYLE_LABELS: Record<SummaryStyle, string> = {
  neutral: "Neutral",
  executive: "Executive",
  technical: "Technical",
  academic: "Academic",
  casual: "Casual",
  eli5: "Simple (ELI5)",
};

export const FORMAT_LABELS: Record<SummaryFormat, string> = {
  paragraph: "Paragraph",
  bullets: "Bullet points",
  "key-points": "Key points",
  structured: "Structured report",
};
