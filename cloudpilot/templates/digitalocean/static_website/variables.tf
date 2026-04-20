variable "project_name" {
  description = "Project identifier used for resource naming."
  type        = string
}

variable "region" {
  description = "DigitalOcean app region."
  type        = string
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}

variable "instance_size_slug" {
  description = "App Platform instance size."
  type        = string
  default     = "basic-xxs"
}

variable "container_port" {
  description = "Container port exposed by the app."
  type        = number
  default     = 80
}

variable "image_repository" {
  description = "Public Docker image repository for static serving."
  type        = string
  default     = "nginx"
}

variable "image_tag" {
  description = "Docker image tag."
  type        = string
  default     = "latest"
}
