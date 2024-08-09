output "vpc_network_id" {
  value       = google_compute_network.vpc_network.id
  description = "The ID of the VPC network."
}

output "vpc_subnet_id" {
  value       = google_compute_subnetwork.vpc_subnetwork.id
  description = "The ID of the VPC subnetwork."
}

output "vpc_subnet_cidr" {
  value       = google_compute_subnetwork.vpc_subnetwork.ip_cidr_range
  description = "The CIDR of the VPC subnetwork."
}

output "nat_router_id" {
  value       = google_compute_router.nat_router.id
  description = "The ID of the NAT router."
}

output "nat_gateway_id" {
  value       = google_compute_router_nat.nat_gateway.id
  description = "The ID of the NAT gateway."
}
