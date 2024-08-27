variable "project_id" {
  description = "The project ID"
  type        = string
}

variable "terraform_service_account" {
  type        = string
  description = "The service account to impersonate"
}

variable "region" {
  type        = string
  description = "The region"
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "The zone"
  default     = "us-central1-a"
}

variable "vpc_network_name" {
  type        = string
  description = "The VPC network name"
}

variable "vpc_subnet_name" {
  type        = string
  description = "The VPC subnet name"
}

variable "vpc_subnet_cidr" {
  type        = string
  description = "The VPC subnet CIDR"
}

variable "nat_router_name" {
  type        = string
  description = "The NAT router name"
}

variable "nat_gateway_name" {
  type        = string
  description = "The NAT gateway name"
}

variable "global_lb_domain" {
  description = "The domain name for the global load balancer"
  type        = string
  default     = null
  nullable    = true
}

variable "cloud_run_invoker_service_account" {
  description = "The service account to authenticate requests to Cloud Run services."
  type        = string
  nullable    = true
  default     = null
}

variable "docker_image" {
  description = "Docker Image for the T2X Cloud Run service."
  type        = string
}

variable "docker_image_ui" {
  description = "Docker Image for the T2X Cloud Run service in UI mode."
  type        = string
  nullable    = true
  default     = null
}
