# Security

## Authentication & authorization
- JWT bearer tokens (`app/security/auth.py`), pbkdf2_sha256 password hashing (no
  native build dependency).
- Optional auth: anonymous callers get `user_id = None`; authenticated callers
  are scoped to their own data.
- `require_user_id` protects account endpoints; `get_optional_user_id` scopes
  trip access.

## Data isolation
- `TripRepository` refuses to return or mutate a trip owned by a different user
  (`row.user_id not in (None, user_id)`), enforcing per-user isolation.
- Soft deletion (`is_deleted`) instead of hard deletes.

## Input validation
- All request bodies are Pydantic-validated. LLM output is validated against
  Pydantic schemas before entering business logic (never trusted raw).

## Secrets
- All secrets come from environment variables; `.env` is gitignored and
  `.env.example` documents the shape. API keys never reach the frontend — the
  browser only ever talks to our API.

## Prompt-injection defense (section 28)
- The system treats all external/tool content as **untrusted data**, not
  instructions. Agents consume tool results as structured data fields, not as
  directives.
- The web-search tool returns an explicit empty result rather than fabricating
  citations; when a real backend is wired in, its output must stay on the data
  side of the trust boundary:

```
User input → sanitize → LLM → tool call (validated args) → external data
           → validate → LLM   (external text is data, never commands)
```

- Tool arguments are constructed by our code from validated fields, not passed
  through from raw model text.

## Transport & CORS
- CORS origins are configurable (lock down in production via `CORS_ORIGINS`).
- A per-request ID is attached (`X-Request-ID`) for traceability.

## Hardening checklist for production
- [ ] Set a strong `JWT_SECRET` and restrict `CORS_ORIGINS`.
- [ ] Put the API behind TLS and a rate limiter (Redis is wired for this).
- [ ] Use Alembic migrations; least-privilege DB credentials.
- [ ] Enable `LOG_JSON=true` and ship logs/metrics to your observability stack.
- [ ] Rotate keys via a secrets manager.
