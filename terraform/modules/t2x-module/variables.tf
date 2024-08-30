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
  description = "The VPC subnet ID."
}

variable "compute_instance_name" {
  description = "The name of the Compute Engine instance."
  type        = string
}

variable "t2x_dataset_name" {
  description = "The name of the BigQuery dataset."
  type        = string
}

variable "redis_instance_name" {
  description = "The name of the Redis instance."
  type        = string
}

variable "global_lb_domain" {
  type        = string
  description = "The domain name for the global load balancer."
}
