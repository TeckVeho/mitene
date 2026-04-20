# Optional project-level IAM for Google Groups / SAs (internal wiki §5). Keep empty if managed elsewhere.

resource "google_project_iam_member" "extra" {
  for_each = {
    for i, m in var.project_iam_members : tostring(i) => m
  }

  project = var.project_id
  role    = each.value.role
  member  = each.value.member
}
