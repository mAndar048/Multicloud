output "endpoint_url" {
  description = "Database endpoint and port."
  value       = "${aws_db_instance.db.address}:${aws_db_instance.db.port}"
}

output "resource_id" {
  description = "Primary RDS instance identifier."
  value       = aws_db_instance.db.id
}

output "db_instance_arn" {
  description = "ARN for the RDS instance."
  value       = aws_db_instance.db.arn
}
