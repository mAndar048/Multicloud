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
  bucket_name = "${var.project_name}-${var.environment}-site"

  common_labels = merge(
    {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
    },
    var.labels
  )
}

resource "google_storage_bucket" "site" {
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  website {
    main_page_suffix = var.main_page_suffix
    not_found_page   = var.not_found_page
  }

  labels = local.common_labels
}

resource "google_compute_backend_bucket" "site" {
  name        = "${var.project_name}-${var.environment}-backend"
  bucket_name = google_storage_bucket.site.name
  enable_cdn  = true
}

resource "google_compute_url_map" "site" {
  name            = "${var.project_name}-${var.environment}-url-map"
  default_service = google_compute_backend_bucket.site.id
}

resource "google_compute_target_http_proxy" "site" {
  name    = "${var.project_name}-${var.environment}-http-proxy"
  url_map = google_compute_url_map.site.id
}

resource "google_compute_global_address" "site" {
  name = "${var.project_name}-${var.environment}-ip"
}

resource "google_compute_global_forwarding_rule" "site" {
  name                  = "${var.project_name}-${var.environment}-fwd"
  ip_address            = google_compute_global_address.site.address
  target                = google_compute_target_http_proxy.site.id
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL"
}
