terraform {
  backend "gcs" {
    prefix = "main"
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
