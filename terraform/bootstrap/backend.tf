# README step Bootstrap - 6a:
# Set the target remote state bucket and the service account email you created with gcloud.
terraform {
  backend "gcs" {
    bucket                      = "terraform-state-my-project-id" # example only
    impersonate_service_account = "terraform-service-account@my-project-id.iam.gserviceaccount.com" # example only
    prefix                      = "bootstrap"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">=5.25.0"
    }
  }
  required_version = ">= 0.13"
}
