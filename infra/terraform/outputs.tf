output "artifact_registry_repository" {
  description = "Docker repository resource name when create_artifact_registry is true; null if using a common registry."
  value       = var.create_artifact_registry ? google_artifact_registry_repository.docker[0].name : null
}

output "resource_tier" {
  description = "Optional wiki tier label from var.resource_tier (empty string if unset)."
  value       = var.resource_tier
}

output "gcp_project_labels" {
  description = "Project labels when manage_gcp_project_labels is true; null otherwise."
  value       = try(google_project.wiki_labels[0].labels, null)
}

output "cloud_sql_instance_name" {
  description = "Cloud SQL instance id used by this stack (wiki default: mitene-mysql-{env_suffix})."
  value       = var.enable_cloud_sql ? google_sql_database_instance.main[0].name : null
}

output "cloud_run_url" {
  description = "HTTPS URL of the Cloud Run service (default *.run.app hostname)."
  value       = google_cloud_run_v2_service.api.uri
}

output "cloud_run_worker_job_name" {
  description = "Cloud Run Job name for NotebookLM video worker when enable_cloud_run_worker is true; null otherwise."
  value       = var.enable_cloud_run_worker ? google_cloud_run_v2_job.worker[0].name : null
}

output "api_public_base_url" {
  description = "Effective public HTTPS base for the API: custom domain if api_custom_domain is set, else the default Cloud Run URL."
  value       = local.api_custom_domain_fqdn != "" ? "https://${local.api_custom_domain_fqdn}" : (google_cloud_run_v2_service.api.uri != null ? trimsuffix(google_cloud_run_v2_service.api.uri, "/") : null)
}

output "web_public_base_url" {
  description = "Effective public HTTPS base for the web when enable_web is true; custom domain if web_custom_domain is set, else Cloud Run URL. Null if enable_web is false."
  value       = !var.enable_web ? null : (local.web_custom_domain_fqdn != "" ? "https://${local.web_custom_domain_fqdn}" : (google_cloud_run_v2_service.web[0].uri != null ? trimsuffix(google_cloud_run_v2_service.web[0].uri, "/") : null))
}

output "api_domain_mapping_status" {
  description = "Cloud Run domain mapping status for api_custom_domain (null if unset). Use resource_records / conditions to configure DNS at your registrar."
  value       = length(google_cloud_run_domain_mapping.api) > 0 ? google_cloud_run_domain_mapping.api[0].status : null
}

output "web_domain_mapping_status" {
  description = "Cloud Run domain mapping status for web_custom_domain (null if unset or enable_web is false)."
  value       = length(google_cloud_run_domain_mapping.web) > 0 ? google_cloud_run_domain_mapping.web[0].status : null
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

output "sql_schedule_function_url" {
  description = "HTTPS URL of the Cloud Functions Gen2 SQL schedule (null if enable_sql_night_weekend_schedule is false)."
  value       = var.enable_cloud_sql && var.enable_sql_night_weekend_schedule ? google_cloudfunctions2_function.sql_activation[0].url : null
}

output "sql_scheduler_job_stop" {
  description = "Cloud Scheduler job id/name for SQL stop (null if schedule disabled)."
  value       = var.enable_cloud_sql && var.enable_sql_night_weekend_schedule ? google_cloud_scheduler_job.sql_stop[0].name : null
}

output "sql_scheduler_job_start" {
  description = "Cloud Scheduler job id/name for SQL start (null if schedule disabled)."
  value       = var.enable_cloud_sql && var.enable_sql_night_weekend_schedule ? google_cloud_scheduler_job.sql_start[0].name : null
}
