# API container env: tfvars `env_vars` wins on key collisions (e.g. override GCS_BUCKET).
locals {
  api_container_env = merge(
    var.enable_gcs ? {
      GCS_BUCKET     = local.gcs_bucket_name_effective
      GCP_PROJECT_ID = var.project_id
    } : {},
    var.env_vars,
  )
}

# APIs required for Artifact Registry + Cloud Run
resource "google_project_service" "run" {
  service = "run.googleapis.com"
}

resource "google_project_service" "artifactregistry" {
  service = "artifactregistry.googleapis.com"
}

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_repo_id
  description   = "Mitene Docker images (Terraform)"
  format        = "DOCKER"

  depends_on = [
    google_project_service.artifactregistry,
  ]
}

resource "google_cloud_run_v2_service" "api" {
  name     = var.cloud_run_service_name
  location = var.region

  # depends_on must be a static list (no concat/conditionals). SQL ordering uses
  # implicit deps: template refs instance + secret; annotations tie secret_version + IAM.
  depends_on = [google_project_service.run]

  template {
    timeout                          = var.cloud_run_timeout
    max_instance_request_concurrency = var.cloud_run_max_concurrency

    dynamic "vpc_access" {
      for_each = var.enable_cloud_sql ? [1] : []
      content {
        connector = google_vpc_access_connector.main[0].id
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }

    annotations = var.enable_cloud_sql ? {
      "terraform-internal-deps" = "${google_secret_manager_secret_version.database_url[0].name}|${google_project_iam_member.cloudrun_sql_client[0].id}"
    } : {}

    dynamic "volumes" {
      for_each = var.enable_cloud_sql ? [1] : []
      content {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.main[0].connection_name]
        }
      }
    }

    containers {
      image = var.container_image

      ports {
        container_port = var.container_port
      }

      dynamic "volume_mounts" {
        for_each = var.enable_cloud_sql ? [1] : []
        content {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }

      dynamic "env" {
        for_each = local.api_container_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.enable_cloud_sql ? [1] : []
        content {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url[0].name
              version = "latest"
            }
          }
        }
      }
    }
  }

  ingress = "INGRESS_TRAFFIC_ALL"
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.allow_unauthenticated ? 1 : 0

  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "web" {
  count = var.enable_web ? 1 : 0

  name     = var.web_cloud_run_service_name
  location = var.region

  depends_on = [
    google_project_service.run,
  ]

  template {
    containers {
      image = var.web_container_image

      ports {
        container_port = var.web_container_port
      }

      dynamic "env" {
        for_each = var.web_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  ingress = "INGRESS_TRAFFIC_ALL"
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker_web" {
  count = var.enable_web && var.allow_unauthenticated_web ? 1 : 0

  name     = google_cloud_run_v2_service.web[0].name
  location = google_cloud_run_v2_service.web[0].location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}

check "web_image_when_enabled" {
  assert {
    condition     = !var.enable_web || var.web_container_image != ""
    error_message = "When enable_web is true, set web_container_image to a pushed mitene-web image (e.g. .../mitene-web:dev)."
  }
}

check "no_duplicate_database_url_env" {
  assert {
    condition     = !var.enable_cloud_sql || !contains(keys(local.api_container_env), "DATABASE_URL")
    error_message = "Remove DATABASE_URL from env_vars when enable_cloud_sql is true; it is injected from Secret Manager."
  }
}

check "network_remote_state_when_cloud_sql" {
  assert {
    condition     = !var.enable_cloud_sql || (var.network_remote_state_bucket != "" && var.network_remote_state_prefix != "")
    error_message = "When enable_cloud_sql is true, set network_remote_state_bucket and network_remote_state_prefix. Apply infra/terraform/network first."
  }
}
