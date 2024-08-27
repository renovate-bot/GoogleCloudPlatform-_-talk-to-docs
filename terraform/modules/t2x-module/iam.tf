resource "google_service_account" "t2x_service_account" {
  account_id   = "t2x-app"
  description  = "T2X app GCE host-attached service account."
  display_name = "T2X App Service Account"
}

resource "google_project_iam_member" "t2x_service_account" {
  for_each = toset(local.t2x_iam_roles)
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.t2x_service_account.email}"
}
