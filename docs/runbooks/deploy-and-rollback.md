# Runbook — Deploy & Rollback

## Pipeline (automatic)
`.github/workflows/deploy.yml` runs on merge to `main`:

1. **Gate** — `ruff`, `mypy`, `pytest -q`, then the **RAG eval gate**
   (`pytest -m eval`). A red gate blocks the build; nothing ships.
2. **Build & push** — api / worker / frontend images to Artifact Registry,
   tagged with the commit SHA (`${GITHUB_SHA::12}`).
3. **Deploy** — `gcloud run deploy` each service to the new image.
4. **Smoke test** — poll the API `/api/v1/health` until healthy (fails the job
   otherwise).

Auth uses Workload Identity Federation — no long-lived JSON keys. Required repo
config is documented at the top of `deploy.yml`.

## Provisioning infrastructure (first time / infra changes)
```bash
cd infra/terraform/envs/prod        # or envs/dev
cp terraform.tfvars.example terraform.tfvars   # fill in project_id, secrets
terraform init
terraform plan
terraform apply
```
`terraform apply` creates Artifact Registry, Cloud SQL (HA), Memorystore, GCS,
Secret Manager, the VPC + connector, and the three Cloud Run services. The
deploy workflow only updates the **image** on existing services.

## Manual deploy (break-glass)
```bash
TAG=$(git rev-parse --short=12 HEAD)
BASE=us-central1-docker.pkg.dev/$PROJECT/rag-platform
for svc in api worker frontend; do
  docker build -f backend/Dockerfile.$svc -t $BASE/$svc:$TAG backend 2>/dev/null || \
  docker build -f frontend/Dockerfile   -t $BASE/frontend:$TAG frontend
  docker push $BASE/$svc:$TAG
  gcloud run deploy rag-prod-$svc --image $BASE/$svc:$TAG --region us-central1
done
```

## Rollback
Cloud Run keeps every revision. Rolling back is a traffic shift — no rebuild:

```bash
# List revisions (newest first).
gcloud run revisions list --service rag-prod-api --region us-central1

# Send 100% of traffic back to the previous good revision.
gcloud run services update-traffic rag-prod-api \
  --region us-central1 --to-revisions rag-prod-api-00042-abc=100
```
Roll back `api`, `worker`, and `frontend` together if the bad change spanned
them. A schema migration is **not** auto-reverted: if the bad release ran an
Alembic upgrade, decide whether to `alembic downgrade` or restore Postgres
(see `backup-and-restore.md`) before shifting traffic.

## Post-deploy verification
- `GET /api/v1/ready` returns 200 with `database: ok` (and `redis: ok` in prod).
- `GET /api/v1/providers` shows the expected active adapters.
- Cloud Run metrics: request error rate < 1%, no restart loop.
- Trigger one ingestion + one chat; confirm the answer is cited.
