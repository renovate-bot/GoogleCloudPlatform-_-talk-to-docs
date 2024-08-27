variable "project_id" {
  description = "The project ID"
  type        = string
  nullable    = true
  default     = null
}

variable "terraform_service_account" {
  type        = string
  description = "The service account to impersonate"
  nullable    = true
  default     = null
}

variable "region" {
  type        = string
  description = "The region"
  default     = "us-central1"
}

variable "services" {
  type        = list(string)
  description = "The services to deploy"
}

variable "data_mover_service_account" {
  type        = string
  description = "The service account to impersonate for data migration"
  nullable    = true
  default     = null
}
variable "cloudbuild_iam_roles" {
  type        = list(string)
  description = "The IAM roles to assign to the Cloud Build service account"
}

variable "cloudbuild_sa_name" {
  type        = string
  description = "The name of the Cloud Build service account"
}

variable "staging_bucket_prefix" {
  type        = string
  description = "The prefix for the staging bucket"
}
