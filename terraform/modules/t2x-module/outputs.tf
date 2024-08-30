output "bigquery_dataset_id" {
  description = "The ID of the BigQuery dataset."
  value       = google_bigquery_dataset.dataset.dataset_id
}

output "bigquery_table_ids" {
  description = "The BigQuery tables."
  value       = [for table in google_bigquery_table.tables : table.table_id]
}

output "t2x_service_account_email" {
  description = "The T2X instance-attached service account email address"
  value       = google_service_account.t2x_service_account.email
}

output "redis_host" {
  description = "The IP address of the Redis instance."
  value       = google_redis_instance.default.host
}

output "redis_instance_name" {
  description = "The name of the Redis instance."
  value       = var.redis_instance_name
}

output "redis_dns_name" {
  description = "The DNS name of the Redis instance."
  value       = google_dns_record_set.redis.name
}

output "compute_instance_name" {
  description = "The name of the Compute Engine instance."
  value       = var.compute_instance_name
}

output "compute_instance_id" {
  description = "The number of the Compute Engine instance."
  value       = google_compute_instance.dev_instance.instance_id

}
