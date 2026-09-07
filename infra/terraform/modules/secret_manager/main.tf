terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

variable "project_id" { type = string }

variable "secrets" {
  description = <<-EOT
    Map of logical name => value. Terraform creates a Secret Manager secret per
    entry and (when the value is non-empty) a first version. Leave a value empty
    ("") to create the container only and populate the version out of band
    (recommended for real credentials -- keep them out of tfstate/tfvars where
    possible).
  EOT
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "accessor_member" {
  description = "Service account (member string) granted secretAccessor on all secrets."
  type        = string
  default     = null
}

resource "google_secret_manager_secret" "this" {
  for_each  = var.secrets
  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "this" {
  for_each    = { for k, v in var.secrets : k => v if v != "" }
  secret      = google_secret_manager_secret.this[each.key].id
  secret_data = each.value
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each  = var.accessor_member == null ? {} : google_secret_manager_secret.this
  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = var.accessor_member
}

output "secret_ids" {
  description = "Map of logical name => Secret Manager secret_id (for value_source refs)."
  value       = { for k, s in google_secret_manager_secret.this : k => s.secret_id }
}
