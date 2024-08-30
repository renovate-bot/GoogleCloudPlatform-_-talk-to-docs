variable "project_id" {
  type        = string
  description = "The ID of the project"
}

variable "global_lb_domain" {
  type        = string
  description = "The domain of the global load balancer"
  nullable    = true
  default     = null
}

variable "backend_services" {
  type = map(object({
    paths               = list(string)
    service             = string
    path_prefix_rewrite = optional(string, "/")
  }))
  description = "The backend services to be used in the URL map"
}
