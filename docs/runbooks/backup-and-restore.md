# Runbook — Backup & Restore

Covers the two stateful stores: **Postgres** (source of truth: users, documents,
jobs, conversations, citations) and the **vector store** (derived embeddings).
Object storage (GCS) is covered by bucket versioning + lifecycle rules.

## What must survive a disaster

| Store | Contains | Recoverable from |
|---|---|---|
| Postgres | All primary records | Automated backups + PITR; on-demand exports |
| Vector store (Chroma/pgvector) | Embeddings + chunk metadata | Restore snapshot **or** re-index from Postgres |
| GCS bucket | Raw uploaded files | Object versioning (30-day window) |

The vector store is **derived data**: every chunk traces back to a document in
Postgres and a file in GCS. If Postgres and GCS are intact, the vector index can
always be rebuilt by re-running ingestion — so the vector store's RPO is relaxed.

## Postgres (Cloud SQL)

### Backups (automated)
Terraform enables daily automated backups (`03:00`) with 7 retained backups and
**point-in-time recovery** (`point_in_time_recovery_enabled = true`). This gives
an RPO of a few minutes (WAL replay) and 7-day coverage.

### On-demand logical export (before risky migrations)
```bash
gcloud sql export sql rag-prod-pg \
  gs://<project>-rag-backups/pg/$(date +%F-%H%M).sql.gz \
  --database=rag
```

### Restore — point in time
```bash
# Clone the instance to a timestamp (non-destructive: creates a new instance).
gcloud sql instances clone rag-prod-pg rag-prod-pg-restore \
  --point-in-time '2026-09-07T12:00:00Z'
# Verify, then repoint DATABASE_URL (Secret Manager) at the restored instance.
```

### Restore — from a logical export
```bash
gcloud sql import sql rag-prod-pg-restore \
  gs://<project>-rag-backups/pg/2026-09-07-1200.sql.gz --database=rag
```

### Local / compose
```bash
# Backup
docker compose -f infra/docker-compose.prod.yml exec postgres \
  pg_dump -U rag rag | gzip > backup-$(date +%F).sql.gz
# Restore
gunzip -c backup-2026-09-07.sql.gz | \
  docker compose -f infra/docker-compose.prod.yml exec -T postgres psql -U rag rag
```

## Vector store

### Option A — restore a snapshot (fast)
- **Chroma (compose/self-hosted):** the index lives on the `chromadata` volume.
  ```bash
  docker run --rm -v rag-platform-prod_chromadata:/data -v "$PWD":/backup \
    alpine tar czf /backup/chroma-$(date +%F).tar.gz -C /data .
  # restore: tar xzf into the volume before starting the chroma service.
  ```
- **pgvector:** embeddings are rows in Postgres — covered by the Postgres backup
  above. Nothing extra to do.

### Option B — rebuild from source of truth (authoritative)
Use when the snapshot is stale, corrupt, or the embedder/model changed. This
re-runs ingestion for every document; because ingestion is idempotent
(checksum-keyed) it is safe to run against a live system.
```bash
# Admin endpoint re-enqueues an idempotent ingestion job per document.
# Reprocess all documents (script loops POST /api/v1/admin/documents/{id}/reprocess).
python -m app.scripts.reindex_all   # or drive the admin API
```
See also `docs/runbooks/reindex-on-embedder-change.md` for the
embedding-dimension-drift guardrail when the embedder changes.

## Restore drill (quarterly)
1. Clone Postgres to a scratch instance from last night's PITR.
2. Point a staging API at it; run `pytest -m eval` against the restored corpus.
3. Rebuild the vector index (Option B) and confirm retrieval recall matches the
   scorecard baseline.
4. Tear down the scratch instance. Record the wall-clock RTO.
