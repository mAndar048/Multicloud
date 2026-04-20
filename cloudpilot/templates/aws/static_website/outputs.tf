output "endpoint_url" {
  description = "Public URL for the static website."
  value       = "https://${aws_cloudfront_distribution.site.domain_name}"
}

output "resource_id" {
  description = "Primary CloudFront distribution identifier."
  value       = aws_cloudfront_distribution.site.id
}

output "bucket_name" {
  description = "S3 bucket storing static assets."
  value       = aws_s3_bucket.site.id
}
