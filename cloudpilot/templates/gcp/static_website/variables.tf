variable "project_name" {
  description = "Project identifier used for resource naming."
  type        = string
}

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for deployment resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}

variable "main_page_suffix" {
  description = "Website index document."
  type        = string
  default     = "index.html"
}

variable "not_found_page" {
  description = "Website not found document."
  type        = string
  default     = "404.html"
}

variable "force_destroy" {
  description = "Whether to delete bucket objects on destroy."
  type        = bool
  default     = false
}

variable "labels" {
  description = "Additional labels to attach to resources."
  type        = map(string)
  default     = {}
}
