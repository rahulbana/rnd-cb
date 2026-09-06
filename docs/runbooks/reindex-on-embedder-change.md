# Runbook — Reindex on embedder change (embedding-dimension drift)

## Why this exists

Switching `EMBEDDER_PROVIDER` can change vector dimensionality (e.g. a local
Sentence-Transformers model at 384 dims vs. an OpenAI embedder at 1536). A
vector store populated at one dimension cannot be queried with vectors of
another. This is a **documented, deliberate reindex** — never a silent break.

The `EmbeddingVector` domain model carries `dim` explicitly so the mismatch is
detectable rather than latent.

## When to run

- Any time `EMBEDDER_PROVIDER` changes to a provider/model with a different
  output dimensionality.
- Any time the embedding model version changes in a way that alters the vector
  space (even at the same dimensionality, similarity is not comparable across
  model versions).

## Procedure (target state; stages land across Phases 3–4 and 9)

1. Put ingestion into maintenance: stop accepting new uploads (or route them
   to a paused queue).
2. Record the current provider/dim and the target provider/dim in the change
   record.
3. Create a fresh vector-store namespace/collection for the new dimensionality
   (do not mutate the existing one in place).
4. Re-embed and re-index every document from its stored `ParsedDocument` /
   chunks. Raw files remain in object storage, so no re-parse is required
   unless the chunker also changed.
5. Cut reads over to the new namespace once backfill completes.
6. Delete the old namespace after a verification window.

## Guardrails

- The registry must **trigger or block** on a dimension change, not proceed
  silently. Until the automated guard lands, treat any embedder swap as
  requiring this runbook.
- Parser fallbacks (Docling → weaker parser) are logged and surfaced in the
  document's ingestion detail — never silent — for the same reason: a quiet
  quality regression is worse than a loud failure.
