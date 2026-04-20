# Partial GCS backend — bucket/prefix nằm trong backend.tf.dev hoặc backend.tf.prod.
# Init (chọn một):
#   terraform init -reconfigure -backend-config=backend.tf.dev
#   terraform init -reconfigure -backend-config=backend.tf.prod
terraform {
  backend "gcs" {}
}
