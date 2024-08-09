output "docker_image" {
  description = "The Docker image used by the T2X API backend service."
  value       = google_cloud_run_v2_service.t2x.template.0.containers.0.image
}

output "cloudrun_backend_service_id" {
  description = "The ID of the T2X API backend service"
  value       = google_compute_backend_service.t2x.id

}
