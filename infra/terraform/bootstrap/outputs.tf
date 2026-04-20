output "state_bucket_name" {
  description = "Pass this value to backend \"gcs\" bucket in other stacks."
  value       = google_storage_bucket.terraform_state.name
}

output "state_bucket_url" {
  value = google_storage_bucket.terraform_state.url
}
