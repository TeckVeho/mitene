# Rename to backend.tf and set bucket/prefix. Create the bucket first if needed.
terraform {
  backend "gcs" {
    bucket = "YOUR-TERRAFORM-STATE-BUCKET"
    prefix = "network/dev"
  }
}
