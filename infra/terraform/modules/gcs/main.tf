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
variable "bucket_name" { type = string }
variable "force_destroy" {
  type    = bool
  default = false
}
variable "versioning" {
  type    = bool
  default = true
}
variable "object_admin_member" {
  description = "Service account (as member string) granted objectAdmin on the bucket."
  type        = string
  default     = null
}

# Object storage for uploaded documents (the GCS ObjectStorage adapter target).
resource "google_storage_bucket" "objects" {
  project                     = var.project_id
  name                        = var.bucket_name
  location                    = var.region
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true

  versioning {
    enabled = var.versioning
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
    # Applies to noncurrent versions only (see with_state) -- keeps a 30-day
    # recovery window for overwritten/deleted objects, then reclaims them.
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket_iam_member" "object_admin" {
  count  = var.object_admin_member == null ? 0 : 1
  bucket = google_storage_bucket.objects.name
  role   = "roles/storage.objectAdmin"
  member = var.object_admin_member
}

output "bucket_name" {
  value = google_storage_bucket.objects.name
}
