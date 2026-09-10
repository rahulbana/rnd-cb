import OpenAI from "openai";
import { encodingForModel, getEncoding, type Tiktoken } from "js-tiktoken";
import { config } from "./config.js";

// A single lazily-constructed client. The zero-arg constructor reads
// OPENAI_API_KEY from the environment (set OPENAI_BASE_URL to target a compatible
// endpoint). We build it lazily so the server can still boot and serve the UI —
// and count tokens locally — even when no key is configured; only real API calls
// then fail, with a clear error.
let _client: OpenAI | null = null;
export function getClient(): OpenAI {
  if (!_client) _client = new OpenAI();
  return _client;
}

export const MODEL = config.model;

// The OpenAI API has no pre-send token-count endpoint, so we count locally with
// tiktoken. Build the encoder once; fall back to o200k_base (the encoding used by
// the gpt-4o / gpt-4.1 families) for models tiktoken doesn't recognize.
let encoder: Tiktoken;
try {
  encoder = encodingForModel(MODEL as Parameters<typeof encodingForModel>[0]);
} catch {
  encoder = getEncoding("o200k_base");
}

/**
 * Estimate the input tokens a request would consume, before sending it. This is
 * the heart of "context handling": it lets us decide between a single pass and a
 * chunked map-reduce, and lets the UI show real numbers instead of guesses.
 *
 * This counts the prompt text only and ignores the small per-message chat
 * overhead, so treat it as a close estimate rather than exact billing.
 */
export function countTokens(system: string, userContent: string): number {
  return encoder.encode(system).length + encoder.encode(userContent).length;
}
