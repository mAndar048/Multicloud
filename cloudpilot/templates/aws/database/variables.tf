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

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "appdb"
}

variable "db_username" {
  description = "Master database username."
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "Master database password."
  type        = string
  sensitive   = true
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t3.micro"
}

variable "engine_version" {
  description = "MySQL engine version."
  type        = string
  default     = "8.0"
}

variable "allocated_storage" {
  description = "Initial storage allocation in GiB."
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Autoscaling max storage in GiB."
  type        = number
  default     = 100
}

variable "publicly_accessible" {
  description = "Whether the DB has a public endpoint."
  type        = bool
  default     = false
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment."
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection."
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot on destroy."
  type        = bool
  default     = false
}

variable "allowed_cidrs" {
  description = "CIDRs allowed to connect to MySQL."
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "tags" {
  description = "Additional tags to attach to resources."
  type        = map(string)
  default     = {}
}
