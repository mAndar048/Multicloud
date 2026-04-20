output "endpoint_url" {
  description = "Public URL for the App Platform app."
  value       = "https://${digitalocean_app.static.default_ingress}"
}

output "resource_id" {
  description = "Primary DigitalOcean app identifier."
  value       = digitalocean_app.static.id
}
