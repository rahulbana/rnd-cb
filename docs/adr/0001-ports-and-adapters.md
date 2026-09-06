# ADR 0001 — Ports & Adapters (Hexagonal) core

- Status: Accepted
- Date: 2026-09-06
- Phase: 1

## Context

The platform must let every pluggable capability — parser, chunker, embedder,
vector store, reranker, LLM, retriever, object storage, task queue — be a
config change rather than a code change. We need swap-without-rewrite from
day one, and testability without network calls.

## Decision

Every capability with more than one reasonable implementation is defined once
as a Python `Protocol` (a **port**) under `app/domain/interfaces/`. Concrete
providers (**adapters**) live under `app/adapters/<port>/` and implement the
port structurally. A **registry** (`app/core/registry.py`) — the only module
allowed to import concrete adapters — maps a name to an adapter class and
resolves it via `get_*()` factories, driven entirely by Pydantic Settings.

Routes, services, and workers depend only on the `get_*` factories (injected
through FastAPI `Depends`), never on a provider class or SDK. Provider-specific
request/response shapes never cross the adapter boundary; only the
provider-agnostic domain models in `app/domain/models/` do.

## Consequences

- Adding a provider later is a one-line registry entry plus an adapter file.
  No consumer changes.
- Flipping one `.env` value swaps an implementation with zero code changes,
  proven by `tests/test_registry_swap.py`.
- Tests register fakes in the same registry, so every route and service is
  testable offline. Phase 1 ships one fake per port (two for the embedder, to
  prove the swap).
- The dependency direction is correct: adapters depend on the domain ports;
  the domain depends on nothing outward.
