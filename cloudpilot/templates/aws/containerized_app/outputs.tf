output "endpoint_url" {
  description = "Public URL for the ECS service."
  value       = "http://${aws_lb.app.dns_name}"
}

output "resource_id" {
  description = "Primary resource identifier for the deployment."
  value       = aws_ecs_service.app.id
}

output "cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.app.name
}
