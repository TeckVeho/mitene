# Rename to backend.tf after the GCS state bucket exists (see bootstrap/ or manual creation).
# Use a distinct prefix per stack instance (dev / stg / prod); same bucket as network/common.
terraform {
  backend "gcs" {
    bucket = "dx-kumu-common-terraform-state"
    prefix = "app/dev"
  }
}

# Other environments: copy backend.tf per workspace or change prefix only:
#   prefix = "app/stg"
#   prefix = "app/prod"
