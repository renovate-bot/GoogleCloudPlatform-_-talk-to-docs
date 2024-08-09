output "doc_ingestion_workflow_service_account" {
  description = "The service account email for the document ingestion workflow."
  value       = google_service_account.doc_ingestion_workflow.email
}
