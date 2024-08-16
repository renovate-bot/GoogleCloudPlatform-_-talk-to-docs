output "data_store_id" {
  description = "The ID of the Agent Builder data store."
  value       = { for k, v in google_discovery_engine_data_store.t2x : k => v.data_store_id }
}

output "search_engine_id" {
  description = "The ID of the Agent Builder search engine."
  value       = { for k, v in google_discovery_engine_search_engine.t2x : k => v.engine_id }
}
