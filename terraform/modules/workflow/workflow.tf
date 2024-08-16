locals {
  workflow_iam_roles = [
    "roles/logging.logWriter",
    "roles/run.invoker",
  ]
}

resource "google_service_account" "doc_ingestion_workflow" {
  account_id   = "doc-ingestion-workflow"
  description  = "Document Ingestion Workflow service account."
  display_name = "Document Ingestion Workflow Service Account"
}

resource "google_project_iam_member" "doc_ingestion_workflow" {
  for_each = toset(local.workflow_iam_roles)
  project  = var.project_id
  role     = each.key
  member   = google_service_account.doc_ingestion_workflow.member
}

resource "google_workflows_workflow" "document_ingestion" {
  name            = "t2x-doc-ingestion-workflow"
  description     = "Workflow to ingest documets to the Agent Builder Data Store"
  service_account = google_service_account.doc_ingestion_workflow.email
  source_contents = file("${path.module}/workflow.yaml")
  user_env_vars = {
    COMPANY_NAME     = var.company_name
    DATA_STORE_ID    = var.data_store_id
    GLOBAL_LB_DOMAIN = var.global_lb_domain
    LOCATION         = var.location
    SEARCH_ENGINE_ID = var.search_engine_id
  }
}
