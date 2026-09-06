# ADR 0009 — Auth, API hardening & enterprise frontend core

- Status: Accepted
- Date: 2026-09-06
- Phase: 8

## Context

The API needs real authentication and per-tenant enforcement, and the platform
needs the first working slice of the enterprise React app so a real user can
log in, ingest documents, and hold a cited conversation through the UI.

## Decision

**Backend auth.** JWT access + refresh tokens (typed `access`/`refresh`
claims), **Argon2id** password hashing, and SHA-256-hashed **API keys** for
service-to-service auth. `get_current_user` accepts either a bearer JWT or an
`X-API-Key`; `require_admin` gates admin-only routes. The first registered user
bootstraps as `admin`; everyone else is `user` (single shared org today).

**Enforcement.** Every data route (`documents`, `jobs`, `retrieve`, `chat`,
`conversations`) now requires auth and derives `org_id`/`owner_id` from the
authenticated user instead of a constant — the multi-tenant hook is now
enforced, not just shaped. Documents, jobs, and conversations are checked for
ownership before access. Health stays public. Login has its own rate limiter;
error responses stay structured (Phase 1 handlers).

**Frontend core** (`frontend/`): React + TS + Vite + Tailwind, React Query for
server state, Zustand for the auth store (JWT persisted to localStorage, silent
refresh on 401). Protected routing (react-router). Screens: login/register,
a **document manager** (multi-file upload with live per-job progress, list,
delete, status badges by format/state), and a **chat UI** with SSE streaming,
inline citations, and a conversation-history sidebar. The API client reads SSE
over `fetch` so it can send the bearer token.

## Consequences

- Tests authenticate through the real register/login flow (a shared fixture
  sets the bearer header); protected routes return 401 without it.
- The browser end-to-end journey can't run in CI, so an API-level journey test
  is the exit proxy: register → login → bulk-upload a mixed batch → watch jobs
  complete → hold a streamed, cited conversation — `tests/test_user_journey.py`.
- A long `SECRET_KEY` is required in production (HS256); the default placeholder
  is for dev only.
- Full multi-tenant isolation (separate orgs per signup) is a later policy
  change — the enforcement points now exist.
