variable "project_id" {
  description = "The project ID."
  type        = string
}

variable "vpc_network_id" {
  type        = string
  description = "The VPC network ID."
}

variable "vpc_subnet_id" {
  type        = string
  description = "The VPC subnetwork ID."
}

variable "region" {
  type        = string
  description = "The region."
}

variable "global_lb_domain" {
  type        = string
  description = "The domain name for the global load balancer."
}

variable "t2x_service_account" {
  description = "The T2X instance-attached service account email address."
  type        = string
}

variable "cloud_run_invoker_service_account" {
  description = "The service account that can invoke a Cloud Run service."
  type        = string
  nullable    = true
  default     = null
}

variable "iap_service_agent_member" {
  description = "The IAP Service Agent in the form 'serviceAccount:{email_address}."
  type        = string
}

variable "service_name" {
  description = "The name of the Cloud Run service."
  type        = string
}

variable "docker_image" {
  description = "Docker Image for the T2X Cloud Run service."
  type        = string
}
