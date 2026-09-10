// Text-processing helpers for context-window management.
//
// When a document is too large to summarize in a single request, we split it
// into chunks on natural boundaries (paragraphs, then sentences, then a hard
// character cut as a last resort), summarize each, and combine the results.

/** Rough token estimate for English text (~4 chars/token). Used only for cheap, local decisions. */
export function approxTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

/**
 * Split text into chunks no larger than `maxChars`, preferring paragraph breaks,
 * then sentence breaks, and only hard-splitting a run of text that has neither.
 */
export function chunkText(text: string, maxChars: number): string[] {
  const trimmed = text.trim();
  if (trimmed.length <= maxChars) return [trimmed];

  const paragraphs = trimmed.split(/\n\s*\n/);
  const chunks: string[] = [];
  let current = "";

  const flush = () => {
    if (current.trim()) chunks.push(current.trim());
    current = "";
  };

  for (const para of paragraphs) {
    if (para.length > maxChars) {
      // A single oversized paragraph: flush what we have, then break it down.
      flush();
      for (const piece of splitLargeBlock(para, maxChars)) chunks.push(piece);
      continue;
    }
    if (current.length + para.length + 2 > maxChars) {
      flush();
    }
    current += (current ? "\n\n" : "") + para;
  }
  flush();

  return chunks;
}

/** Break an oversized block on sentence boundaries, falling back to a hard cut. */
function splitLargeBlock(block: string, maxChars: number): string[] {
  const sentences = block.match(/[^.!?]+[.!?]+[\])'"`]*\s*|[^.!?]+$/g) ?? [block];
  const out: string[] = [];
  let current = "";

  for (const sentence of sentences) {
    if (sentence.length > maxChars) {
      if (current.trim()) out.push(current.trim());
      current = "";
      for (let i = 0; i < sentence.length; i += maxChars) {
        out.push(sentence.slice(i, i + maxChars));
      }
      continue;
    }
    if (current.length + sentence.length > maxChars) {
      out.push(current.trim());
      current = "";
    }
    current += sentence;
  }
  if (current.trim()) out.push(current.trim());
  return out;
}
