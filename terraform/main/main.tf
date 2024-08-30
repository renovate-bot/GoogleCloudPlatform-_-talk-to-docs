locals {
  config           = yamldecode(file("../../gen_ai/llm.yaml"))
  global_lb_domain = coalesce(var.global_lb_domain, try(module.loadbalancer.global_lb_domain, null))
}

resource "google_project_service_identity" "iap_sa" {
  provider = google-beta
  service  = "iap.googleapis.com"
}

module "vpc" {
  source           = "../modules/vpc"
  vpc_network_name = var.vpc_network_name
  vpc_subnet_name  = var.vpc_subnet_name
  vpc_subnet_cidr  = var.vpc_subnet_cidr
  nat_router_name  = var.nat_router_name
  nat_gateway_name = var.nat_gateway_name
}

module "loadbalancer" {
  source                   = "../modules/loadbalancer"
  project_id               = var.project_id
  global_lb_domain         = var.global_lb_domain
  iap_service_agent_member = google_project_service_identity.iap_sa.member

  backend_services = [
    {
      paths   = ["/t2x-api/*"]
      service = module.cloud_run_api.cloudrun_backend_service_id
    },
    {
      paths   = ["/t2x-ui/*"]
      service = module.cloud_run_ui.cloudrun_backend_service_id
    }
  ]
}

module "t2x" {
  source                = "../modules/t2x-module"
  project_id            = var.project_id
  vpc_network_id        = module.vpc.vpc_network_id
  vpc_subnet_id         = module.vpc.vpc_subnet_id
  compute_instance_name = local.config.terraform_instance_name
  t2x_dataset_name      = local.config.dataset_name
  redis_instance_name   = local.config.terraform_redis_name
  global_lb_domain      = local.global_lb_domain
}

module "cloud_run_api" {
  source                            = "../modules/cloud-run"
  project_id                        = var.project_id
  vpc_network_id                    = module.vpc.vpc_network_id
  vpc_subnet_id                     = module.vpc.vpc_subnet_id
  region                            = var.region
  global_lb_domain                  = local.global_lb_domain
  t2x_service_account               = module.t2x.t2x_service_account_email
  iap_service_agent_member          = google_project_service_identity.iap_sa.member
  cloud_run_invoker_service_account = var.cloud_run_invoker_service_account
  service_name                      = "t2x-api"
  docker_image                      = var.docker_image
}

module "cloud_run_ui" {
  source                   = "../modules/cloud-run"
  project_id               = var.project_id
  vpc_network_id           = module.vpc.vpc_network_id
  vpc_subnet_id            = module.vpc.vpc_subnet_id
  region                   = var.region
  global_lb_domain         = local.global_lb_domain
  t2x_service_account      = module.t2x.t2x_service_account_email
  iap_service_agent_member = google_project_service_identity.iap_sa.member
  service_name             = "t2x-ui"
  docker_image             = var.docker_image_ui
}

module "discovery_engine" {
  source = "../modules/discoveryengine"
  discovery_engines = {
    t2x-uhg = {
      location         = local.config.vais_location
      data_store_id    = local.config.vais_data_store
      search_engine_id = local.config.vais_engine_id
      company_name     = local.config.customer_name
    }
  }
}

module "workflow" {
  source           = "../modules/workflow"
  project_id       = var.project_id
  company_name     = local.config.customer_name
  data_store_id    = local.config.vais_data_store
  global_lb_domain = local.global_lb_domain
  location         = local.config.vais_location
  search_engine_id = local.config.vais_engine_id
}
