variable "project_name" {
  description = "Project identifier used for resource naming."
  type        = string
}

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for deployment."
  type        = string
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "Application database username."
  type        = string
  default     = "appuser"
}

variable "db_password" {
  description = "Application database password."
  type        = string
  sensitive   = true
}

variable "instance_tier" {
  description = "Cloud SQL machine tier."
  type        = string
  default     = "db-f1-micro"
}

variable "availability_type" {
  description = "Cloud SQL availability type."
  type        = string
  default     = "ZONAL"
}

variable "ipv4_enabled" {
  description = "Whether to enable public IPv4."
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Enable deletion protection on the SQL instance."
  type        = bool
  default     = true
}

variable "labels" {
  description = "Additional labels to attach to resources."
  type        = map(string)
  default     = {}
}
