resource "google_cloud_run_v2_service" "t2x" {
  name         = var.service_name
  location     = var.region
  launch_stage = "GA"
  ingress      = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  custom_audiences = [
    "https://${var.global_lb_domain}/${var.service_name}",
  ]

  template {
    service_account       = var.t2x_service_account
    timeout               = "300s"
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"

    containers {
      image = var.docker_image

      resources {
        limits = {
          cpu    = "1"
          memory = "2Gi"
        }
      }

      startup_probe {
        timeout_seconds   = 30
        period_seconds    = 180
        failure_threshold = 1
        tcp_socket {
          port = 8080
        }
      }

    }

    scaling {
      min_instance_count = 1
      max_instance_count = 100
    }

    vpc_access {
      network_interfaces {
        network    = var.vpc_network_id
        subnetwork = var.vpc_subnet_id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }
}

# Create a resrouce-level IAM binding to allow the data mover service account to invoke the Cloud Run service.
resource "google_cloud_run_service_iam_member" "t2x_data_mover_invoker" {
  count   = var.cloud_run_invoker_service_account != null ? 1 : 0
  service = google_cloud_run_v2_service.t2x.name
  role    = "roles/run.invoker"
  member  = "serviceAccount:${var.cloud_run_invoker_service_account}"
}

# Allow the IAP Service Agent to invoke the Cloud Run service.
resource "google_cloud_run_service_iam_member" "iap_sa" {
  service = google_cloud_run_v2_service.t2x.name
  role    = "roles/run.invoker"
  member  = var.iap_service_agent_member
}

resource "google_compute_region_network_endpoint_group" "t2x" {
  name                  = var.service_name
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.t2x.name
  }
}

resource "google_compute_backend_service" "t2x" {
  name        = var.service_name
  description = "talk-to-docs"

  protocol                        = "HTTPS"
  port_name                       = "http"
  connection_draining_timeout_sec = 0

  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.t2x.id
  }

  # Identity-Aware Proxy (IAP) requires manual configuration - ignore those changes
  lifecycle {
    ignore_changes = [iap]
  }
}
