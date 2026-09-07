terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "repository_id" {
  type    = string
  default = "rag-platform"
}

# Docker repository holding the api / worker / frontend images.
resource "google_artifact_registry_repository" "docker" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repository_id
  description   = "RAG platform container images"
  format        = "DOCKER"

  docker_config {
    immutable_tags = false
  }
}

output "repository_id" {
  value = google_artifact_registry_repository.docker.repository_id
}

output "registry_host" {
  value = "${var.region}-docker.pkg.dev"
}

output "image_base" {
  description = "Base path for images: <host>/<project>/<repo>."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}
