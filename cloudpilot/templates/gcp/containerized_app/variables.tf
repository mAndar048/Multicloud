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

variable "container_image" {
  description = "Container image URI."
  type        = string
}

variable "container_port" {
  description = "Container port exposed by the app."
  type        = number
  default     = 8080
}

variable "min_instance_count" {
  description = "Minimum Cloud Run instances."
  type        = number
  default     = 0
}

variable "max_instance_count" {
  description = "Maximum Cloud Run instances."
  type        = number
  default     = 3
}

variable "cpu_limit" {
  description = "CPU limit for the container."
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit for the container."
  type        = string
  default     = "512Mi"
}

variable "labels" {
  description = "Additional labels to attach to resources."
  type        = map(string)
  default     = {}
}
