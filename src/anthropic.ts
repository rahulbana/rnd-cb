import Anthropic from "@anthropic-ai/sdk";
import { config } from "./config.js";

// A single shared client. The zero-arg constructor resolves credentials from
// ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or an `ant auth login` profile.
export const client = new Anthropic();

export const MODEL = config.model;

/**
 * Count the input tokens a request would consume, before sending it. This is the
 * heart of "context handling": it lets us decide between a single pass and a
 * chunked map-reduce, and lets the UI show real numbers instead of guesses.
 */
export async function countTokens(
  system: string,
  userContent: string,
): Promise<number> {
  const res = await client.messages.countTokens({
    model: MODEL,
    system,
    messages: [{ role: "user", content: userContent }],
  });
  return res.input_tokens;
}
