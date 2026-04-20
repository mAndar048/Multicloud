output "endpoint_url" {
  description = "Public URL for the static website."
  value       = "http://${google_compute_global_address.site.address}"
}

output "resource_id" {
  description = "Primary backend bucket identifier."
  value       = google_compute_backend_bucket.site.id
}

output "bucket_name" {
  description = "GCS bucket storing static assets."
  value       = google_storage_bucket.site.name
}
