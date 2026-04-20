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

variable "container_image" {
  description = "Container image URI."
  type        = string
}

variable "container_port" {
  description = "Container port exposed by the app."
  type        = number
  default     = 8080
}

variable "desired_count" {
  description = "Desired ECS task count."
  type        = number
  default     = 1
}

variable "task_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512
}

variable "health_check_path" {
  description = "HTTP health check path."
  type        = string
  default     = "/"
}

variable "tags" {
  description = "Additional tags to attach to resources."
  type        = map(string)
  default     = {}
}
