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
variable "name" { type = string }
variable "network_id" {
  description = "VPC network id for private service access."
  type        = string
}
variable "private_vpc_connection" {
  description = "Service networking connection to depend on."
  type        = string
}
variable "memory_size_gb" {
  type    = number
  default = 1
}
variable "tier" {
  description = "BASIC (dev) | STANDARD_HA (prod)."
  type        = string
  default     = "BASIC"
}

# Redis instance: Celery broker + result backend.
resource "google_redis_instance" "redis" {
  project            = var.project_id
  name               = var.name
  region             = var.region
  tier               = var.tier
  memory_size_gb     = var.memory_size_gb
  authorized_network = var.network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  redis_version      = "REDIS_7_0"

  depends_on = [var.private_vpc_connection]
}

output "host" {
  value = google_redis_instance.redis.host
}

output "port" {
  value = google_redis_instance.redis.port
}

output "redis_url" {
  value = "redis://${google_redis_instance.redis.host}:${google_redis_instance.redis.port}/0"
}
