variable "project_id" {
  description = "The project id"
  type        = string
}

variable "company_name" {
  description = "The name of the company"
  type        = string
}

variable "data_store_id" {
  description = "The data store id"
  type        = string
}

variable "global_lb_domain" {
  description = "The global load balancer domain"
  type        = string
}

variable "location" {
  description = "The discoveryengine data store and search location"
  type        = string
}

variable "search_engine_id" {
  description = "The search engine id"
  type        = string
}
