output "network_id" {
  description = "VPC network id (for references)."
  value       = google_compute_network.vpc.id
}

output "network_self_link" {
  description = "VPC self link — use as Cloud SQL private_network."
  value       = google_compute_network.vpc.self_link
}

output "connector_subnet_name" {
  description = "Subnet used by google_vpc_access_connector in the app stack."
  value       = google_compute_subnetwork.connector.name
}

output "connector_subnet_region" {
  description = "Region of the connector subnet (same as var.region)."
  value       = google_compute_subnetwork.connector.region
}

output "private_vpc_connection_id" {
  description = "Service Networking connection id (Private Service Access)."
  value       = google_service_networking_connection.private_vpc_connection.id
}
