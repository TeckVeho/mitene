# Serverless VPC Access — required for Cloud Run → private IP Cloud SQL.

resource "google_project_service" "vpcaccess" {
  count   = var.enable_cloud_sql ? 1 : 0
  service = "vpcaccess.googleapis.com"
}

resource "google_vpc_access_connector" "main" {
  count = var.enable_cloud_sql ? 1 : 0

  name    = "mitene-conn-${var.env_suffix}"
  region  = var.region
  project = var.project_id

  subnet {
    name = data.terraform_remote_state.network[0].outputs.connector_subnet_name
  }

  min_throughput = 200
  max_throughput = 300

  depends_on = [google_project_service.vpcaccess]
}
