# Cloud Run Job: NotebookLM 動画パイプライン（API は JOB_DISPATCH_MODE=cloud_run_job で RunJob を起動）
# ローカル / EC2 では enable_cloud_run_worker=false（既定）のまま。

locals {
  cloud_run_worker_job_name_effective = trimspace(var.cloud_run_worker_job_name) != "" ? var.cloud_run_worker_job_name : "mitene-worker-${var.env_suffix}"
  # api_container_env_base に JOB_DISPATCH を含めない（循環回避）。worker は常に inline。
  worker_plain_env = merge(local.api_container_env_base, { JOB_DISPATCH_MODE = "inline" })
}

resource "google_cloud_run_v2_job" "worker" {
  count = var.enable_cloud_run_worker ? 1 : 0

  name     = local.cloud_run_worker_job_name_effective
  location = var.region
  project  = var.project_id

  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_iam_member.cloudrun_secret_accessor,
  ]

  template {
    parallelism = 1
    task_count  = 1

    template {
      timeout     = var.cloud_run_worker_timeout
      max_retries = 0

      service_account = local.cloud_run_service_account

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
        image   = var.container_image
        command = ["python", "-m", "app.services.worker_entrypoint"]

        resources {
          limits = {
            cpu    = var.cloud_run_worker_cpu
            memory = var.cloud_run_worker_memory
          }
        }

        dynamic "volume_mounts" {
          for_each = var.enable_cloud_sql ? [1] : []
          content {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }

        dynamic "env" {
          for_each = local.worker_plain_env
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
  }
}

resource "google_cloud_run_v2_job_iam_member" "api_sa_run_worker" {
  count = var.enable_cloud_run_worker ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_job.worker[0].location
  name     = google_cloud_run_v2_job.worker[0].name
  role     = "roles/run.jobsExecutorWithOverrides"
  member   = "serviceAccount:${local.cloud_run_service_account}"
}
