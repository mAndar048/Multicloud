terraform {
  required_version = ">= 1.5.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.0"
    }
  }
}

provider "digitalocean" {}

resource "digitalocean_app" "static" {
  spec {
    name   = "${var.project_name}-${var.environment}"
    region = var.region

    service {
      name               = "web"
      instance_count     = 1
      instance_size_slug = var.instance_size_slug
      http_port          = var.container_port

      image {
        registry_type = "DOCKER_HUB"
        repository    = var.image_repository
        tag           = var.image_tag
      }

      routes {
        path = "/"
      }
    }
  }
}
