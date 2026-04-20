terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  instance_name = "${var.project_name}-${var.environment}-sql"

  common_labels = merge(
    {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
    },
    var.labels
  )
}

resource "google_sql_database_instance" "db" {
  name             = local.instance_name
  region           = var.region
  database_version = "MYSQL_8_0"
  deletion_protection = var.deletion_protection

  settings {
    tier              = var.instance_tier
    availability_type = var.availability_type

    ip_configuration {
      ipv4_enabled = var.ipv4_enabled
    }

    backup_configuration {
      enabled = true
    }

    user_labels = local.common_labels
  }
}

resource "google_sql_database" "app" {
  name     = var.db_name
  instance = google_sql_database_instance.db.name
}

resource "google_sql_user" "app" {
  name     = var.db_username
  instance = google_sql_database_instance.db.name
  password = var.db_password
}
