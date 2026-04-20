output "endpoint_url" {
  description = "Public URL for the Cloud Run service."
  value       = google_cloud_run_v2_service.app.uri
}

output "resource_id" {
  description = "Primary Cloud Run service identifier."
  value       = google_cloud_run_v2_service.app.id
}

output "service_name" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.app.name
}
