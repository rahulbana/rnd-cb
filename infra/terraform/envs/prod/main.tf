# Prod composition: HA Cloud SQL (REGIONAL) + STANDARD_HA Redis, deletion
# protection on, the API kept warm (min 1) and the worker always-on. Autoscaling
# ceilings act as cost guardrails: max_instances bounds the monthly spend.

locals {
  env         = "prod"
  name_prefix = "rag-prod"
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "${local.name_prefix}-run"
  display_name = "RAG platform (prod) Cloud Run runtime"
}

module "networking" {
  source      = "../../modules/networking"
  project_id  = var.project_id
  region      = var.region
  name_prefix = local.name_prefix
}

module "artifact_registry" {
  source     = "../../modules/artifact_registry"
  project_id = var.project_id
  region     = var.region
}

module "gcs" {
  source              = "../../modules/gcs"
  project_id          = var.project_id
  region              = var.region
  bucket_name         = "${var.project_id}-rag-objects-prod"
  force_destroy       = false
  versioning          = true
  object_admin_member = "serviceAccount:${google_service_account.runtime.email}"
}

module "cloud_sql" {
  source                 = "../../modules/cloud_sql"
  project_id             = var.project_id
  region                 = var.region
  name                   = "${local.name_prefix}-pg"
  tier                   = "db-custom-2-7680"
  availability_type      = "REGIONAL" # HA: synchronous standby in another zone
  deletion_protection    = true
  network_id             = module.networking.network_id
  private_vpc_connection = module.networking.private_vpc_connection
  db_password            = var.db_password
}

module "memorystore" {
  source                 = "../../modules/memorystore"
  project_id             = var.project_id
  region                 = var.region
  name                   = "${local.name_prefix}-redis"
  tier                   = "STANDARD_HA" # replicated with automatic failover
  memory_size_gb         = 2
  network_id             = module.networking.network_id
  private_vpc_connection = module.networking.private_vpc_connection
}

module "secrets" {
  source          = "../../modules/secret_manager"
  project_id      = var.project_id
  accessor_member = "serviceAccount:${google_service_account.runtime.email}"
  secrets = {
    SECRET_KEY   = var.secret_key
    DATABASE_URL = module.cloud_sql.database_url
    REDIS_URL    = module.memorystore.redis_url
  }
}

locals {
  image_base = module.artifact_registry.image_base

  backend_env = {
    ENV                   = local.env
    DEBUG                 = "false"
    LOG_JSON              = "true"
    CHROMA_MODE           = "http"
    STORAGE_PROVIDER      = "gcs"
    GCS_BUCKET            = module.gcs.bucket_name
    TASK_QUEUE_PROVIDER   = "celery"
    LLM_PROVIDER          = var.llm_provider
    SECRET_PROVIDER       = "gcp_secret_manager"
    GCP_PROJECT_ID        = var.project_id
    VECTOR_STORE_PROVIDER = "pgvector"
    TRACER_PROVIDER       = "otel"
  }

  backend_secret_env = {
    SECRET_KEY   = { secret_id = module.secrets.secret_ids["SECRET_KEY"], version = "latest" }
    DATABASE_URL = { secret_id = module.secrets.secret_ids["DATABASE_URL"], version = "latest" }
    REDIS_URL    = { secret_id = module.secrets.secret_ids["REDIS_URL"], version = "latest" }
  }
}

module "api" {
  source                = "../../modules/cloud_run_service"
  name                  = "${local.name_prefix}-api"
  project_id            = var.project_id
  region                = var.region
  image                 = "${local.image_base}/api:${var.image_tag}"
  service_account_email = google_service_account.runtime.email
  env                   = local.backend_env
  secret_env            = local.backend_secret_env
  cpu                   = "2"
  memory                = "2Gi"
  min_instances         = 1  # keep one warm: no cold-start latency
  max_instances         = 10 # cost guardrail
  concurrency           = 40
  allow_public          = true
  vpc_connector         = module.networking.connector_id
  startup_probe_path    = "/api/v1/ready"
}

module "worker" {
  source                = "../../modules/cloud_run_service"
  name                  = "${local.name_prefix}-worker"
  project_id            = var.project_id
  region                = var.region
  image                 = "${local.image_base}/worker:${var.image_tag}"
  service_account_email = google_service_account.runtime.email
  env                   = local.backend_env
  secret_env            = local.backend_secret_env
  cpu                   = "2"
  memory                = "4Gi"
  min_instances         = 1
  max_instances         = 6 # cost guardrail
  concurrency           = 1
  cpu_always_allocated  = true
  allow_public          = false
  ingress               = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  vpc_connector         = module.networking.connector_id
}

module "frontend" {
  source                = "../../modules/cloud_run_service"
  name                  = "${local.name_prefix}-frontend"
  project_id            = var.project_id
  region                = var.region
  image                 = "${local.image_base}/frontend:${var.image_tag}"
  service_account_email = google_service_account.runtime.email
  cpu                   = "1"
  memory                = "256Mi"
  min_instances         = 1
  max_instances         = 4
  allow_public          = true
  startup_probe_path    = "/healthz"
}
