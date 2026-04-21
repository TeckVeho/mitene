# API / web env: URL overrides only from custom-domain strings (never from Cloud Run *.uri here — avoids Terraform cycles with env on the same services).
locals {
  # Merged after var.env_vars / var.web_env_vars so custom domains align app URLs with mappings.
  public_url_env_api = merge(
    trimspace(var.api_custom_domain) != "" ? {
      API_URL = "https://${local.api_custom_domain_fqdn}"
    } : {},
    var.enable_web && trimspace(var.web_custom_domain) != "" ? {
      FRONTEND_URL         = "https://${local.web_custom_domain_fqdn}"
      CORS_ALLOWED_ORIGINS = "https://${local.web_custom_domain_fqdn}"
    } : {},
  )

  public_url_env_web = var.enable_web ? merge(
    trimspace(var.web_custom_domain) != "" ? {
      NEXT_PUBLIC_BASE_URL = "https://${local.web_custom_domain_fqdn}/"
    } : {},
    trimspace(var.api_custom_domain) != "" ? {
      NEXT_PUBLIC_API_URL = "https://${local.api_custom_domain_fqdn}/api"
    } : {},
  ) : {}

  # API と Cloud Run Job worker で共通（worker のテンプレ env にも使う。JOB_DISPATCH は含めない）
  api_container_env_base = merge(
    var.enable_gcs ? {
      GCS_BUCKET     = local.gcs_bucket_name_effective
      GCP_PROJECT_ID = var.project_id
    } : {},
    merge(var.env_vars, local.public_url_env_api),
  )

  api_worker_dispatch_env = var.enable_cloud_run_worker ? {
    JOB_DISPATCH_MODE         = "cloud_run_job"
    CLOUD_RUN_WORKER_JOB_NAME = google_cloud_run_v2_job.worker[0].name
    CLOUD_RUN_REGION          = var.region
    GCP_PROJECT_ID            = var.project_id
  } : {}

  api_container_env = merge(local.api_container_env_base, local.api_worker_dispatch_env)

  web_container_env = merge(var.web_env_vars, local.public_url_env_web)
}

# APIs required for Artifact Registry + Cloud Run
resource "google_project_service" "run" {
  service = "run.googleapis.com"
}

# Also required for Cloud Functions Gen2 (sql_schedule.tf) when images are stored in this project's Artifact Registry.
resource "google_project_service" "artifactregistry" {
  count   = var.create_artifact_registry || (var.enable_cloud_sql && var.enable_sql_night_weekend_schedule) ? 1 : 0
  service = "artifactregistry.googleapis.com"
}

resource "google_artifact_registry_repository" "docker" {
  count = var.create_artifact_registry ? 1 : 0

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
  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_iam_member.cloudrun_secret_accessor,
  ]

  template {
    scaling {
      min_instance_count = var.cloud_run_api_min_instances
      max_instance_count = var.cloud_run_api_max_instances
    }

    max_instance_request_concurrency = var.cloud_run_api_concurrency
    timeout                          = var.cloud_run_api_timeout

    dynamic "vpc_access" {
      for_each = var.enable_cloud_sql ? [1] : []
      content {
        network_interfaces {
          network    = data.terraform_remote_state.network[0].outputs.network_id
          subnetwork = data.terraform_remote_state.network[0].outputs.connector_subnet_name
        }
        egress = "PRIVATE_RANGES_ONLY"
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

      resources {
        limits = {
          cpu    = var.cloud_run_api_cpu
          memory = var.cloud_run_api_memory
        }
        cpu_idle = true
      }

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
        for_each = var.api_secret_env_from_sm
        content {
          name = env.value.env_name
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = env.value.version
            }
          }
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
    google_secret_manager_secret_iam_member.cloudrun_secret_accessor,
  ]

  template {
    scaling {
      min_instance_count = var.cloud_run_web_min_instances
      max_instance_count = var.cloud_run_web_max_instances
    }

    max_instance_request_concurrency = var.cloud_run_web_concurrency
    timeout                          = var.cloud_run_web_timeout

    containers {
      image = var.web_container_image

      resources {
        limits = {
          cpu    = var.cloud_run_web_cpu
          memory = var.cloud_run_web_memory
        }
        cpu_idle = true
      }

      ports {
        container_port = var.web_container_port
      }

      dynamic "env" {
        for_each = local.web_container_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.web_secret_env_from_sm
        content {
          name = env.value.env_name
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = env.value.version
            }
          }
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

check "api_env_no_overlap_with_sm_secrets" {
  assert {
    condition = length(setintersection(
      toset(keys(var.env_vars)),
      toset([for s in var.api_secret_env_from_sm : s.env_name])
    )) == 0
    error_message = "env_vars must not define the same keys as api_secret_env_from_sm env_name values."
  }
}

check "web_env_no_overlap_with_sm_secrets" {
  assert {
    condition = !var.enable_web || length(setintersection(
      toset(keys(var.web_env_vars)),
      toset([for s in var.web_secret_env_from_sm : s.env_name])
    )) == 0
    error_message = "web_env_vars must not define the same keys as web_secret_env_from_sm env_name values."
  }
}
