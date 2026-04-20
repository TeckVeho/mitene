# Custom domains for Cloud Run (DNS at your registrar — add TXT/CNAME per mapping status after apply).
# FQDN may be apex (example.com) or subdomain (api.example.com); mapping resource is the same.

locals {
  api_custom_domain_fqdn = lower(trimspace(split("/", replace(replace(trimspace(var.api_custom_domain), "https://", ""), "http://", ""))[0]))
  web_custom_domain_fqdn = lower(trimspace(split("/", replace(replace(trimspace(var.web_custom_domain), "https://", ""), "http://", ""))[0]))
}

resource "google_cloud_run_domain_mapping" "api" {
  count = local.api_custom_domain_fqdn != "" ? 1 : 0

  location = var.region
  name     = local.api_custom_domain_fqdn

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.api.name
  }

  depends_on = [
    google_cloud_run_v2_service.api,
  ]
}

resource "google_cloud_run_domain_mapping" "web" {
  count = var.enable_web && local.web_custom_domain_fqdn != "" ? 1 : 0

  location = var.region
  name     = local.web_custom_domain_fqdn

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.web[0].name
  }

  depends_on = [
    google_cloud_run_v2_service.web,
  ]
}

check "web_custom_domain_requires_web" {
  assert {
    condition     = trimspace(var.web_custom_domain) == "" || var.enable_web
    error_message = "web_custom_domain is set but enable_web is false. Enable the web service or clear web_custom_domain."
  }
}
