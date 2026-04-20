variable "project_id" {
  type        = string
  description = "GCP project where the state bucket will be created (typically the common / shared project)."
}

variable "region" {
  type        = string
  default     = "asia-northeast1"
  description = "Bucket location."
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique GCS bucket name for Terraform state (e.g. my-project-common-terraform-state)."
}
