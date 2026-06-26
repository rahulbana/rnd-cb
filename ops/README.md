# Observability stack (Prometheus + Grafana)

Ready-made monitoring for the Deep Search Agent backend's `/metrics` endpoint.

```
ops/
  docker-compose.yml                          Prometheus + Grafana, pre-wired
  prometheus/prometheus.yml                   scrape config (backend :8000/metrics)
  grafana/
    deep-search-dashboard.json                the dashboard (also importable manually)
    provisioning/datasources/prometheus.yml   auto-adds the Prometheus datasource
    provisioning/dashboards/dashboards.yml    auto-loads the dashboard
```

## Run it

1. Start the backend (exposes `/metrics`):
   ```bash
   cd backend && uvicorn app.main:app --port 8000
   ```
2. Start the stack:
   ```bash
   cd ops && docker compose up -d
   ```
3. Open Grafana at <http://localhost:3000> (admin / admin). The
   **Deep Search Agent — Observability** dashboard is under the *Deep Search*
   folder. Prometheus is at <http://localhost:9090>.

## Manual import (no Docker)

If you already run Prometheus + Grafana, just import the dashboard:
**Grafana → Dashboards → New → Import →** upload
`grafana/deep-search-dashboard.json`, then pick your Prometheus data source when
prompted. Make sure Prometheus scrapes the backend `/metrics` endpoint
(see `prometheus/prometheus.yml` for a sample scrape job).

## What the dashboard shows

| Section | Panels |
| --- | --- |
| Overview | runs in progress, completed runs, success rate %, HTTP in-flight |
| Agent | run rate by outcome, run duration p50/p95/p99, per-node duration p95, sources/run avg & p95 |
| Providers | search calls by provider/status, search results, LLM calls by kind + tokens/s |
| HTTP | request rate by status, request latency p50/p95/p99 |
