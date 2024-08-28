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

variable "iap_service_agent_member" {
  description = "The IAP Service Agent in the form 'serviceAccount:{email_address}."
  type        = string
}

variable "backend_services" {
  type = list(object({
    paths               = list(string)
    service             = string
    path_prefix_rewrite = optional(string, "/")
  }))
  description = "The backend services to be used in the URL map"
}
