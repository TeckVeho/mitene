# VPC stack: shared VPC for private Cloud SQL + Serverless VPC Access subnet.
# Apply this stack before the app stack when enable_cloud_sql = true.

locals {
  network_name_effective = var.network_name != "" ? var.network_name : "mitene-vpc-${var.env_suffix}"
  subnet_connector_name  = "mitene-connector-${var.env_suffix}"
}

resource "google_project_service" "compute" {
  service = "compute.googleapis.com"
}

resource "google_project_service" "servicenetworking" {
  service = "servicenetworking.googleapis.com"
}

resource "google_compute_network" "vpc" {
  name                    = local.network_name_effective
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [
    google_project_service.compute,
  ]
}

resource "google_compute_subnetwork" "connector" {
  name          = local.subnet_connector_name
  ip_cidr_range = var.connector_subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_compute_global_address" "private_service_range" {
  name          = "mitene-psa-${var.env_suffix}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  address       = var.private_service_peering_cidr
  prefix_length = var.private_service_peering_prefix_length
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network = google_compute_network.vpc.id
  service = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [
    google_compute_global_address.private_service_range.name,
  ]

  depends_on = [
    google_project_service.servicenetworking,
  ]
}
