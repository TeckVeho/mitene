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

  length  = 24
  special = false # keep MySQL URL in Secret Manager safe without extra encoding
}

locals {
  sql_instance_name_effective = substr(
    replace(lower("${var.project_id}-mitene-sql-${var.env_suffix}"), "_", "-"),
    0,
    96
  )
}

resource "google_sql_database_instance" "main" {
  count = var.enable_cloud_sql ? 1 : 0

  name             = local.sql_instance_name_effective
  database_version = "MYSQL_8_0"
  region           = var.region

  settings {
    tier      = var.sql_tier
    disk_size = var.sql_disk_size_gb
    disk_type = "PD_SSD"
    ip_configuration {
      ipv4_enabled    = false
      private_network = data.terraform_remote_state.network[0].outputs.network_self_link
      # Org policy sql.restrictPublicIp: no public IPv4; Cloud Run uses unix socket + VPC connector for private path.
    }
  }

  deletion_protection = var.sql_deletion_protection

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
    random_password.sql_app[0].result,
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
