output "api_url" {
  value = module.api.uri
}

output "frontend_url" {
  value = module.frontend.uri
}

output "image_base" {
  description = "Artifact Registry base path for pushing images."
  value       = module.artifact_registry.image_base
}

output "cloud_sql_connection_name" {
  value = module.cloud_sql.connection_name
}
