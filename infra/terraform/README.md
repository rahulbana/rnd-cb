# Terraform — GCP deployment for the RAG platform

Infrastructure as code for the production topology on Google Cloud:

| Module | Resource | Purpose |
|---|---|---|
| `artifact_registry` | Artifact Registry (Docker) | Holds the api / worker / frontend images |
| `gcs` | Cloud Storage bucket | Object storage (uploaded documents) |
| `secret_manager` | Secret Manager secrets | `SECRET_KEY`, DB password, provider API keys |
| `cloud_sql` | Cloud SQL (Postgres 16) | Primary database, private IP |
| `memorystore` | Memorystore (Redis) | Celery broker/backend |
| `networking` | VPC + Serverless VPC connector | Private egress from Cloud Run to SQL/Redis |
| `cloud_run_service` | Cloud Run v2 service | Reusable: runs the api, the worker, and the frontend |

## Layout

```
modules/                 reusable building blocks
envs/
  dev/                   dev composition (small instances, scale-to-zero)
  prod/                  prod composition (HA, always-on worker, guardrails)
```

## Usage

```bash
cd infra/terraform/envs/dev            # or envs/prod
cp terraform.tfvars.example terraform.tfvars   # fill in project_id etc.
terraform init
terraform plan
terraform apply
```

State is stored in a GCS backend (see `backend.tf`); create the state bucket
once, out of band, before `terraform init`. Secret *values* are never committed
— Terraform creates the secret containers; versions are populated from
`*.tfvars` (git-ignored) or by CI from the pipeline's own secret store.

The CI/CD pipeline (`.github/workflows/deploy.yml`) builds and pushes images to
Artifact Registry, then updates each Cloud Run service to the new image digest.
The RAG eval gate must pass before the deploy job runs.
