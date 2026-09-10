// Centralized configuration. Loads .env (if present) without adding a dependency:
// Node >=20.6 ships process.loadEnvFile().

try {
  // Loads ./.env into process.env. No-op-friendly: throws if the file is missing.
  process.loadEnvFile();
} catch {
  // No .env file — rely on the ambient environment (e.g. an exported OPENAI_API_KEY).
}

export const config = {
  port: Number(process.env.PORT ?? 3000),

  /** Model used for every summarization request. */
  model: process.env.SUMMARIZER_MODEL ?? "gpt-4o-mini",

  /**
   * Above this many input tokens we stop trying to summarize in one shot and
   * fall back to a chunked map-reduce pass. gpt-4o / gpt-4o-mini have a 128k-token
   * context window, so this default leaves room for the summary output; lower it
   * to watch the chunking path engage on smaller documents.
   */
  chunkThresholdTokens: Number(process.env.CHUNK_THRESHOLD_TOKENS ?? 100_000),

  /**
   * Approximate characters per chunk when map-reduce is used. ~4 chars/token is
   * a rough English heuristic, so ~24k tokens/chunk here — comfortably inside a
   * single request while keeping the number of chunks small.
   */
  charsPerChunk: 96_000,
} as const;
