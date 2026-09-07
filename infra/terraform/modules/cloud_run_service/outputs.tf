output "uri" {
  description = "The service URL (empty for internal-only services)."
  value       = google_cloud_run_v2_service.this.uri
}

output "name" {
  value = google_cloud_run_v2_service.this.name
}
