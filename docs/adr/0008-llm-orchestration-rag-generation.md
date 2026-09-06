# ADR 0008 — LLM orchestration & RAG generation

- Status: Accepted
- Date: 2026-09-06
- Phase: 7

## Context

The retrieval spine (Phases 1-6) produces a token-budgeted, citation-tagged
context. Phase 7 turns that into grounded, cited, streamed answers from any of
four LLM backends interchangeably, with conversation memory and a cost/latency
trail.

## Decision

Four **LLMProvider** adapters behind the port — `ollama` (default, local),
`openai`, `anthropic`, `gemini` — each mapping the provider-neutral
`ChatMessage`/`LLMResponse` to/from the vendor payload. Provider SDKs import
lazily (Ollama needs only httpx); construction never opens a connection, so the
registry resolves any provider and CI runs without SDKs. Selection is one env
var (`LLM_PROVIDER`).

The `ChatService` pipeline: retrieve → rerank → assemble context → **sanitize**
(redact prompt-injection phrasings) → render a **versioned Jinja2 prompt**
(`PROMPT_VERSION`; the system prompt enforces grounding, `[n]` citations,
treat-context-as-untrusted-data, and the explicit "not found" fallback) →
generate or **stream over SSE** → persist the turn.

**Conversation memory** keeps a sliding window of recent turns verbatim and
summarizes older turns into one synthetic system message (via the LLM). Every
turn is persisted (`messages`) with citations, provider, token counts and
latency — the full cost/latency trail; cost is estimated from a per-provider
price table and logged per request. Context packing uses the **active
provider's `count_tokens`** so budgeting matches its real tokenizer.

Endpoints: `POST /api/v1/chat` (sync), `POST /api/v1/chat/stream` (SSE: a
`meta` event with citations, then token events, then `done`), and conversation
history reads. A migration seeds a default system user so conversations have a
valid owner until auth arrives in Phase 8.

## Consequences

- Real LLM adapters need network + keys, so their live calls are out of scope
  for unit tests; the fake provider drives the deterministic end-to-end
  streamed-cited-answer path, and the registry swap proves provider selection.
- Exit: the same query streams a cited answer, and one env var
  (`LLM_PROVIDER`) selects Ollama / OpenAI / Anthropic / Gemini at an identical
  call site — `tests/test_chat_swap.py`, `tests/test_llm_providers.py`.
- Message ordering uses a strictly-monotonic timestamp so turns stay ordered
  even under second-resolution clocks.
