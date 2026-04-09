variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  default     = "asia-northeast1"
  description = "Region for regional subnet (VPC connector + Cloud Run / SQL must align)."
}

variable "env_suffix" {
  type        = string
  default     = "dev"
  description = "Suffix for resource names (e.g. dev, prod)."

  validation {
    condition     = can(regex("^[a-z0-9-]{1,16}$", var.env_suffix))
    error_message = "env_suffix must be lowercase letters, digits, hyphens, max 16 chars."
  }
}

variable "network_name" {
  type        = string
  default     = ""
  description = "VPC name. If empty, derived as mitene-vpc-<env_suffix>."
}

variable "connector_subnet_cidr" {
  type        = string
  default     = "10.8.0.0/28"
  description = "Regional subnet for Serverless VPC Access (Cloud Run). Must not overlap the private service peering range."
}

variable "private_service_peering_cidr" {
  type        = string
  default     = "10.247.0.0"
  description = "Start of reserved range for Google managed services (Cloud SQL private IP). /16 prefix; must not overlap any subnet in this VPC."
}

variable "private_service_peering_prefix_length" {
  type        = number
  default     = 16
  description = "Prefix length for the VPC peering range allocated to servicenetworking.googleapis.com."
}
