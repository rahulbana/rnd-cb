variable "name" {
  description = "Cloud Run service name."
  type        = string
}

variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "image" {
  description = "Fully-qualified container image (Artifact Registry path + tag/digest)."
  type        = string
}

variable "service_account_email" {
  description = "Runtime service account for the service."
  type        = string
}

variable "command" {
  description = "Optional container entrypoint override."
  type        = list(string)
  default     = null
}

variable "args" {
  description = "Optional container args override."
  type        = list(string)
  default     = null
}

variable "env" {
  description = "Plain environment variables."
  type        = map(string)
  default     = {}
}

variable "secret_env" {
  description = "Env vars sourced from Secret Manager: name => {secret_id, version}."
  type = map(object({
    secret_id = string
    version   = string
  }))
  default = {}
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 10
}

variable "concurrency" {
  description = "Max concurrent requests per instance."
  type        = number
  default     = 80
}

variable "cpu_always_allocated" {
  description = "Keep the CPU allocated outside requests (required for a background worker)."
  type        = bool
  default     = false
}

variable "allow_public" {
  description = "Grant roles/run.invoker to allUsers (public HTTP ingress)."
  type        = bool
  default     = false
}

variable "ingress" {
  description = "Ingress setting: INGRESS_TRAFFIC_ALL | INGRESS_TRAFFIC_INTERNAL_ONLY."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "vpc_connector" {
  description = "Serverless VPC connector id for private egress (null to skip)."
  type        = string
  default     = null
}

variable "startup_probe_path" {
  description = "HTTP path for the startup/readiness probe (null for a non-HTTP service like the worker)."
  type        = string
  default     = null
}

variable "container_port" {
  type    = number
  default = 8080
}
