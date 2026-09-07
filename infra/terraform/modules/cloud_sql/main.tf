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
variable "tier" {
  type    = string
  default = "db-custom-1-3840"
}
variable "network_id" {
  description = "VPC network id for private IP (from the networking module)."
  type        = string
}
variable "private_vpc_connection" {
  description = "Service networking connection to depend on."
  type        = string
}
variable "db_name" {
  type    = string
  default = "rag"
}
variable "db_user" {
  type    = string
  default = "rag"
}
variable "db_password" {
  type      = string
  sensitive = true
}
variable "availability_type" {
  description = "ZONAL (dev) | REGIONAL (prod HA)."
  type        = string
  default     = "ZONAL"
}
variable "deletion_protection" {
  type    = bool
  default = true
}

resource "google_sql_database_instance" "postgres" {
  project             = var.project_id
  name                = var.name
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = var.deletion_protection

  depends_on = [var.private_vpc_connection]

  settings {
    tier              = var.tier
    availability_type = var.availability_type
    disk_autoresize   = true
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
    }

    insights_config {
      query_insights_enabled = true
    }
  }
}

resource "google_sql_database" "db" {
  project  = var.project_id
  name     = var.db_name
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "user" {
  project  = var.project_id
  name     = var.db_user
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

output "private_ip" {
  value = google_sql_database_instance.postgres.private_ip_address
}

output "connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "database_url" {
  description = "SQLAlchemy URL (private IP)."
  value       = "postgresql+psycopg://${var.db_user}:${var.db_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/${var.db_name}"
  sensitive   = true
}
