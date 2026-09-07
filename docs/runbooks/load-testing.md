# Runbook — Load Testing

Load profile lives in `infra/loadtest/k6-rag.js` ([k6](https://k6.io)). It ramps
to 25 sustained virtual users exercising `/health`, `/retrieve`, and `/chat`, and
enforces SLOs as k6 **thresholds** — a breach exits non-zero, so the same script
is a pass/fail performance gate in CI against a staging deploy.

## SLOs (thresholds)
| Metric | Target |
|---|---|
| Error rate (`http_req_failed`) | < 1% |
| Chat p95 latency | < 8s (retrieval + rerank + LLM) |
| Retrieve p95 latency | < 1.5s |
| Health p95 latency | < 300ms |

Tune the numbers to the deployed LLM: a hosted model (OpenAI/Anthropic) and a
local Ollama have very different chat latencies.

## Run it
```bash
# Install k6 (macOS: brew install k6; linux: see k6.io/docs).
BASE_URL=https://rag-dev-api-xxxx.run.app \
EMAIL=loadtester@example.com PASSWORD='<pw>' \
k6 run infra/loadtest/k6-rag.js
```

Against the local prod stack:
```bash
docker compose -f infra/docker-compose.prod.yml --env-file infra/prod.env up -d
BASE_URL=http://localhost:8080 k6 run infra/loadtest/k6-rag.js
```

## Reading the results
- `http_req_duration{endpoint:chat}` — end-to-end generation latency.
- `chat_latency_ms` — custom trend, p95 gated above.
- `iterations` / `vus` — throughput at the sustained plateau.

## Capacity & autoscaling notes
- Cloud Run `max_instance_request_concurrency` is **40** for the API; each
  Gunicorn instance runs `WEB_CONCURRENCY` Uvicorn workers. Raise `max_instances`
  (the cost guardrail) if the plateau saturates instances before the SLO breaks.
- The worker scales on queue depth, not HTTP; load-test ingestion separately by
  bulk-uploading a zip and watching `GET /api/v1/admin/queue`.
- Watch Cloud SQL CPU and Memorystore memory during the run — the first
  bottleneck under load is usually the database connection pool, not the API.
