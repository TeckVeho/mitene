# Optional Cloud SQL (MySQL) + Secret Manager DATABASE_URL + Cloud Run unix socket.
# Enable with enable_cloud_sql = true after enabling billing and APIs.

resource "google_project_service" "sqladmin" {
  count   = var.enable_cloud_sql ? 1 : 0
  service = "sqladmin.googleapis.com"
}

resource "google_project_service" "secretmanager" {
  count   = var.enable_cloud_sql ? 1 : 0
  service = "secretmanager.googleapis.com"
}

resource "random_password" "sql_app" {
  count = var.enable_cloud_sql ? 1 : 0

  length = 24
  # Cloud SQL password_validation_policy (COMPLEXITY_DEFAULT) requires lower, upper, numeric, and special.
  lower       = true
  upper       = true
  numeric     = true
  special     = true
  min_lower   = 1
  min_upper   = 1
  min_numeric = 1
  min_special = 1
}

# Root password is required when password_validation_policy is enabled (not embedded in app DATABASE_URL).
resource "random_password" "sql_root" {
  count = var.enable_cloud_sql ? 1 : 0

  length      = 24
  lower       = true
  upper       = true
  numeric     = true
  special     = true
  min_lower   = 1
  min_upper   = 1
  min_numeric = 1
  min_special = 1
}

locals {
  # Wiki: {service}-mysql-{env} → mitene-mysql-dev. Set var.sql_instance_name to keep an older instance id.
  sql_instance_name_effective = substr(
    replace(
      lower(var.sql_instance_name != "" ? var.sql_instance_name : "mitene-mysql-${var.env_suffix}"),
      "_",
      "-",
    ),
    0,
    96,
  )
}

resource "google_sql_database_instance" "main" {
  count = var.enable_cloud_sql ? 1 : 0

  name             = local.sql_instance_name_effective
  database_version = "MYSQL_8_0"
  region           = var.region
  root_password    = random_password.sql_root[0].result

  settings {
    tier              = local.sql_tier_effective
    disk_size         = local.sql_disk_size_gb_effective
    disk_type         = local.sql_disk_type_effective
    activation_policy = "ALWAYS"
    ip_configuration {
      ipv4_enabled    = false
      private_network = data.terraform_remote_state.network[0].outputs.network_self_link
      ssl_mode        = "ENCRYPTED_ONLY"
      # Org policy sql.restrictPublicIp: no public IPv4; Cloud Run uses unix socket + Direct VPC for private path.
    }

    password_validation_policy {
      enable_password_policy      = true
      min_length                  = 8
      complexity                  = "COMPLEXITY_DEFAULT"
      disallow_username_substring = true
    }

    dynamic "database_flags" {
      for_each = var.enable_sql_audit ? [1] : []
      content {
        name  = "cloudsql_mysql_audit"
        value = "ON"
      }
    }

    backup_configuration {
      enabled                        = var.sql_backup_enabled
      start_time                     = var.sql_backup_start_time
      point_in_time_recovery_enabled = var.sql_backup_enabled && var.sql_point_in_time_recovery_enabled
    }
  }

  deletion_protection = var.sql_deletion_protection

  # Cloud Scheduler may set NEVER overnight; do not revert on the next terraform apply.
  lifecycle {
    ignore_changes = [settings[0].activation_policy]
  }

  depends_on = [
    google_project_service.sqladmin,
  ]
}

resource "google_sql_database" "app" {
  count = var.enable_cloud_sql ? 1 : 0

  name     = var.sql_database_name
  instance = google_sql_database_instance.main[0].name
}

resource "google_sql_user" "app" {
  count = var.enable_cloud_sql ? 1 : 0

  name     = var.sql_user_name
  instance = google_sql_database_instance.main[0].name
  password = random_password.sql_app[0].result
}

resource "google_secret_manager_secret" "database_url" {
  count = var.enable_cloud_sql ? 1 : 0

  secret_id = "mitene-database-url-${var.env_suffix}"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "database_url" {
  count = var.enable_cloud_sql ? 1 : 0

  secret = google_secret_manager_secret.database_url[0].id
  secret_data = format(
    "mysql://%s:%s@localhost/%s?socket=/cloudsql/%s",
    var.sql_user_name,
    urlencode(random_password.sql_app[0].result),
    var.sql_database_name,
    google_sql_database_instance.main[0].connection_name,
  )
}

resource "google_secret_manager_secret_iam_member" "cloudrun_database_url" {
  count = var.enable_cloud_sql ? 1 : 0

  project   = var.project_id
  secret_id = google_secret_manager_secret.database_url[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.cloud_run_service_account}"
}

resource "google_project_iam_member" "cloudrun_sql_client" {
  count = var.enable_cloud_sql ? 1 : 0

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${local.cloud_run_service_account}"
}
