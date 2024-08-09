# README step Automate Deployments with Cloud Build - step 2:
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

    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">=5.25.0"
    }

    random = {
      source  = "hashicorp/random"
      version = ">=3.6.2"
    }
  }
  required_version = ">= 0.13"
}
