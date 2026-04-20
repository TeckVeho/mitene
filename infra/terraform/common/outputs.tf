output "artifact_registry_repository_id" {
  description = "Repository id segment (for IAM / references)."
  value       = google_artifact_registry_repository.docker.repository_id
}

output "artifact_registry_repository_name" {
  description = "Full resource name (projects/.../repositories/...)."
  value       = google_artifact_registry_repository.docker.name
}

output "docker_repository_url_prefix" {
  description = "Prefix for container_image in app tfvars, e.g. REGION-docker.pkg.dev/PROJECT/REPO"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}
