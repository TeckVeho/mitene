# Rename to backend.tf after the state bucket exists (see ../bootstrap/).
terraform {
  backend "gcs" {
    bucket = "veho-mitene-common-terraform-state"
    prefix = "common/main"
  }
}
