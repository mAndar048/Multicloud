output "endpoint_url" {
  description = "Database endpoint and MySQL port."
  value       = "${google_sql_database_instance.db.first_ip_address}:3306"
}

output "resource_id" {
  description = "Primary Cloud SQL instance identifier."
  value       = google_sql_database_instance.db.id
}

output "connection_name" {
  description = "Cloud SQL connection name."
  value       = google_sql_database_instance.db.connection_name
}
