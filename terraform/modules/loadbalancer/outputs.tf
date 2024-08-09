output "lb_ip_address" {
  description = "The IP address of the load balancer"
  value       = google_compute_global_address.t2x_lb_global_address.address
}

output "global_lb_domain" {
  description = "The domain of the global load balancer"
  value       = local.t2x_lb_domain
}

output "cert_name" {
  description = "The ID of the managed certificate"
  value       = google_compute_managed_ssl_certificate.cert.name
}
