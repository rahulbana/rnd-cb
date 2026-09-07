variable "project_id" {
  description = "GCP project id."
  type        = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "image_tag" {
  description = "Container image tag/digest to deploy (CI passes the built digest)."
  type        = string
  default     = "latest"
}

variable "secret_key" {
  description = "Application SECRET_KEY (JWT signing). Store the real value in tfvars (git-ignored) or seed the secret version out of band."
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Cloud SQL password for the rag user."
  type        = string
  sensitive   = true
}

variable "llm_provider" {
  type    = string
  default = "ollama"
}
