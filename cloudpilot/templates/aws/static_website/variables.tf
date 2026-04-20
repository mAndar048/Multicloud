variable "project_name" {
  description = "Project identifier used for resource naming."
  type        = string
}

variable "region" {
  description = "AWS region for deployment."
  type        = string
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}

variable "price_class" {
  description = "CloudFront price class."
  type        = string
  default     = "PriceClass_100"
}

variable "force_destroy" {
  description = "Whether the bucket should be force deleted."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags to attach to resources."
  type        = map(string)
  default     = {}
}
