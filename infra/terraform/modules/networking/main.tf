terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

variable "project_id" { type = string }
variable "region" { type = string }
variable "name_prefix" { type = string }
variable "connector_cidr" {
  description = "Unused /28 CIDR for the serverless VPC connector."
  type        = string
  default     = "10.8.0.0/28"
}

# Private network so Cloud Run reaches Cloud SQL and Memorystore over private IP.
resource "google_compute_network" "vpc" {
  project                 = var.project_id
  name                    = "${var.name_prefix}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  project       = var.project_id
  name          = "${var.name_prefix}-subnet"
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.20.0.0/24"
}

# Serverless VPC Access connector: Cloud Run's bridge into the VPC.
resource "google_vpc_access_connector" "connector" {
  project       = var.project_id
  name          = "${var.name_prefix}-conn"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.connector_cidr
}

# Private Services Access range so Cloud SQL / Memorystore get private IPs.
resource "google_compute_global_address" "private_range" {
  project       = var.project_id
  name          = "${var.name_prefix}-psa"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "psa" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_range.name]
}

output "network_id" {
  value = google_compute_network.vpc.id
}

output "connector_id" {
  value = google_vpc_access_connector.connector.id
}

output "private_vpc_connection" {
  description = "Depend on this so SQL/Redis wait for the peering to exist."
  value       = google_service_networking_connection.psa.id
}
