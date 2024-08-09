output "project_id" {
  value = var.project_id
}

output "vpc_network_id" {
  description = "The ID of the VPC created by the aa_network module"
  value       = module.vpc.vpc_network_id
}

output "vpc_subnet_id" {
  description = "The ID of the subnetwork created by the aa_network module"
  value       = module.vpc.vpc_subnet_id
}

output "vpc_subnet_cidr" {
  description = "The CIDR of the subnetwork created by the aa_network module"
  value       = module.vpc.vpc_subnet_cidr
}

output "nat_router_id" {
  value       = module.vpc.nat_router_id
  description = "The ID of the NAT router."
}

output "nat_gateway_id" {
  value       = module.vpc.nat_gateway_id
  description = "The ID of the NAT gateway."
}

output "lb_ip_address" {
  description = "The IP address of the load balancer"
  value       = module.loadbalancer.lb_ip_address
}

output "global_lb_domain" {
  description = "The domain of the global load balancer"
  value       = module.loadbalancer.global_lb_domain
}

output "cert_name" {
  description = "The ID of the managed certificate"
  value       = module.loadbalancer.cert_name
}

output "bigquery_dataset_id" {
  description = "The ID of the BigQuery dataset."
  value       = module.t2x.bigquery_dataset_id
}

output "bigquery_table_ids" {
  description = "The BigQuery tables."
  value       = [for table_id in module.t2x.bigquery_table_ids : table_id]
}

output "t2x_service_account_email" {
  description = "The T2X instance-attached service account email address"
  value       = module.t2x.t2x_service_account_email
}

output "redis_host" {
  description = "The IP address of the Redis instance."
  value       = module.t2x.redis_host
}

output "redis_instance_name" {
  description = "The name of the Redis instance."
  value       = module.t2x.redis_instance_name
}

output "redis_dns_name" {
  description = "The DNS name of the Redis instance."
  value       = module.t2x.redis_dns_name

}

output "data_store_id" {
  description = "The ID of the Agent Builder data store."
  value       = module.discovery_engine.data_store_id
}

output "search_engine_id" {
  description = "The ID of the Agent Builder search engine."
  value       = module.discovery_engine.search_engine_id
}

output "docker_image" {
  description = "The Docker image used by the T2X API backend service."
  value       = module.cloud_run_api.docker_image
}

output "backend_id" {
  description = "The ID of the T2X Cloud run API backend service"
  value       = module.cloud_run_api.cloudrun_backend_service_id

}

output "docker_image_ui" {
  description = "The Docker image used by the T2X API backend service."
  value       = module.cloud_run_ui.docker_image
}

output "backend_id_ui" {
  description = "The ID of the T2X Cloud run UI backend service"
  value       = module.cloud_run_ui.cloudrun_backend_service_id

}

output "doc_ingestion_workflow_service_account" {
  description = "The service account email for the document ingestion workflow."
  value       = module.workflow.doc_ingestion_workflow_service_account
}
