output "artifact_registry_repository" {
  description = "Docker repository name for gcloud/docker push."
  value       = google_artifact_registry_repository.docker.name
}

output "cloud_run_url" {
  description = "HTTPS URL of the Cloud Run service."
  value       = google_cloud_run_v2_service.api.uri
}

output "cloud_run_service_name" {
  value = google_cloud_run_v2_service.api.name
}

output "web_cloud_run_url" {
  description = "HTTPS URL of the web Cloud Run service (empty if enable_web is false)."
  value       = var.enable_web ? google_cloud_run_v2_service.web[0].uri : null
}

output "web_cloud_run_service_name" {
  description = "Web service name (null if enable_web is false)."
  value       = var.enable_web ? google_cloud_run_v2_service.web[0].name : null
}

output "gcs_uploads_bucket" {
  description = "GCS bucket for file uploads (null if enable_gcs is false)."
  value       = var.enable_gcs ? google_storage_bucket.uploads[0].name : null
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name for Cloud Run / clients (null if enable_cloud_sql is false)."
  value       = var.enable_cloud_sql ? google_sql_database_instance.main[0].connection_name : null
}

output "secret_database_url_id" {
  description = "Secret Manager secret id holding DATABASE_URL (null if enable_cloud_sql is false)."
  value       = var.enable_cloud_sql ? google_secret_manager_secret.database_url[0].secret_id : null
  sensitive   = false
}

output "vpc_access_connector" {
  description = "Serverless VPC connector id (null if enable_cloud_sql is false)."
  value       = var.enable_cloud_sql ? google_vpc_access_connector.main[0].id : null
}
