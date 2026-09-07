# ADR 0011 — Production hardening & cloud deployment

- Status: Accepted
- Date: 2026-09-07
- Phase: 10

## Context

The platform is feature-complete but built for a laptop: single-stage dev
images, secrets as plain env vars, no cloud footprint, no deploy pipeline, and
no story for backups or load. Phase 10 makes it deployable to GCP Cloud Run
without a rewrite — the same ports-and-adapters seams that swap a provider now
swap a *runtime environment*.

## Decision

**Multi-stage images.** `Dockerfile.api`, `Dockerfile.worker`, and the frontend
`Dockerfile` split into a fat `builder` (venv / node build, throwaway) and a
slim, **non-root** `runtime`. The API runs Gunicorn managing Uvicorn workers;
the frontend is static assets served by nginx (which also reverse-proxies
`/api` and streams SSE unbuffered). Each image carries a container `HEALTHCHECK`.

**Probes.** `/api/v1/health` is liveness (process only — a DB blip can't trigger
a restart loop). `/api/v1/ready` is readiness: it checks Postgres, and Redis when
Celery is the queue, returning **503** so the orchestrator stops routing to an
instance that can't serve. Both are wired as Cloud Run startup/liveness probes.

**Secrets abstraction (new port).** `SecretProvider` with `env` (default) and
`gcp_secret_manager` (lazy SDK) adapters, resolved by the registry from
`SECRET_PROVIDER` — the same one-env-var swap as every other capability. Cloud
Run also injects `SECRET_KEY`/`DATABASE_URL`/`REDIS_URL` as secret-backed env
vars from Secret Manager, so no credential is baked into an image or tfstate
value the app reads at rest.

**Terraform.** `infra/terraform/modules/*` (artifact_registry, gcs,
secret_manager, cloud_sql, memorystore, networking, and a reusable
`cloud_run_service`) composed by `envs/dev` and `envs/prod`. Dev is disposable
(scale-to-zero, ZONAL, no deletion protection); prod is HA (REGIONAL Cloud SQL,
STANDARD_HA Redis, API kept warm, always-on worker). Cloud Run reaches Cloud SQL
and Memorystore over **private IP** through a Serverless VPC connector.

**CI/CD (`deploy.yml`).** On merge to `main`: a **gate** job runs lint, types,
tests, and the **RAG eval suite** (`pytest -m eval`) — a red gate blocks the
build. Then build → push (SHA-tagged) → `gcloud run deploy` → health smoke test.
Auth is Workload Identity Federation (no long-lived keys). `security.yml` adds
`pip-audit`, `npm audit`, and gitleaks; `infra.yml` runs `terraform fmt/validate`
and validates the prod compose file.

**Local prod parity.** `infra/docker-compose.prod.yml` boots the same topology
(hardened images, reverse-proxied frontend, resource limits, secrets from a
git-ignored env file) so prod is reproducible on a laptop.

**Ops.** k6 load test with SLO thresholds (`infra/loadtest/k6-rag.js`); runbooks
for backup/restore (Cloud SQL PITR; vector store restored *or* rebuilt from
Postgres as the source of truth), deploy/rollback (Cloud Run revision traffic
shift), and load testing.

## Consequences

- The vector store is treated as **derived data**: its disaster-recovery path is
  re-indexing from Postgres + GCS, which relaxes its RPO and keeps backups cheap.
- GCP SDKs (`google-cloud-secret-manager`, `google-cloud-storage`) are lazy and
  behind the `gcp` extra; the registry resolves the `env` secret default and CI
  runs without them installed — consistent with every prior phase.
- Autoscaling ceilings (`max_instances`) double as cost guardrails; min instances
  trade cost for cold-start latency (prod keeps the API + worker warm).
- Exit: `docker compose -f infra/docker-compose.prod.yml config` validates the
  prod topology, `terraform validate` passes for both envs, and the deploy
  pipeline gates on the eval suite before shipping to Cloud Run.
