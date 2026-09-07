terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

# Reusable Cloud Run v2 service. Runs the API (public HTTP), the frontend
# (public HTTP), and the Celery worker (internal, CPU always allocated,
# min_instances=1 so it keeps draining the queue).
resource "google_cloud_run_v2_service" "this" {
  name     = var.name
  location = var.region
  project  = var.project_id
  ingress  = var.ingress

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    max_instance_request_concurrency = var.concurrency

    dynamic "vpc_access" {
      for_each = var.vpc_connector == null ? [] : [var.vpc_connector]
      content {
        connector = vpc_access.value
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }

    containers {
      image   = var.image
      command = var.command
      args    = var.args

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle          = !var.cpu_always_allocated
        startup_cpu_boost = true
      }

      ports {
        container_port = var.container_port
      }

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = env.value.version
            }
          }
        }
      }

      dynamic "startup_probe" {
        for_each = var.startup_probe_path == null ? [] : [var.startup_probe_path]
        content {
          initial_delay_seconds = 10
          period_seconds        = 10
          failure_threshold     = 6
          timeout_seconds       = 5
          http_get {
            path = startup_probe.value
            port = var.container_port
          }
        }
      }

      dynamic "liveness_probe" {
        for_each = var.startup_probe_path == null ? [] : [var.startup_probe_path]
        content {
          period_seconds    = 30
          failure_threshold = 3
          http_get {
            path = startup_probe.value
            port = var.container_port
          }
        }
      }
    }
  }
}

# Public services (api, frontend) allow unauthenticated invocation; the worker
# stays private.
resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_public ? 1 : 0
  name     = google_cloud_run_v2_service.this.name
  location = var.region
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}
