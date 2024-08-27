output "docker_image" {
  description = "The Docker image used by the T2X API backend service."
  value       = google_cloud_run_v2_service.t2x.template.0.containers.0.image
}

output "cloudrun_backend_service_id" {
  description = "The ID of the T2X API backend service"
  value       = google_compute_backend_service.t2x.id

}

output "cloudrun_custom_audiences" {
  description = "The list of custom audiences used for authenticated calls to the Cloud Run service."
  value       = google_cloud_run_v2_service.t2x.custom_audiences
}
