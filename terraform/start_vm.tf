# Terraform script to start a stopped GCP VM
# This script is used by the Infrastructure Agent to automatically recover VMs

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "zone" {
  description = "GCP Zone where VM is located"
  type        = string
  default     = "us-central1-a"
}

variable "vm_name" {
  description = "Name of the VM to start"
  type        = string
}

variable "credentials_file" {
  description = "Path to GCP credentials JSON file"
  type        = string
  default     = "./gcp-service-account-key.json"
}

provider "google" {
  project     = var.project_id
  region      = "us-central1"
  credentials = file(var.credentials_file)
}

# Data source to get VM information
data "google_compute_instance" "vm" {
  name = var.vm_name
  zone = var.zone
}

# Resource to manage VM state
resource "google_compute_instance" "vm_start" {
  name         = var.vm_name
  machine_type = data.google_compute_instance.vm.machine_type
  zone         = var.zone

  # Preserve existing configuration
  boot_disk {
    source = data.google_compute_instance.vm.boot_disk[0].source
  }

  network_interface {
    network = data.google_compute_instance.vm.network_interface[0].network

    dynamic "access_config" {
      for_each = data.google_compute_instance.vm.network_interface[0].access_config
      content {
        nat_ip = access_config.value.nat_ip
      }
    }
  }

  # Important: Set desired_status to RUNNING to start the VM
  desired_status = "RUNNING"

  # Preserve metadata
  metadata = data.google_compute_instance.vm.metadata

  # Preserve tags
  tags = data.google_compute_instance.vm.tags

  lifecycle {
    ignore_changes = [
      # Ignore changes to these attributes to prevent recreation
      boot_disk,
      network_interface,
    ]
  }
}

output "vm_status" {
  description = "Current status of the VM"
  value       = google_compute_instance.vm_start.current_status
}

output "vm_name" {
  description = "Name of the started VM"
  value       = google_compute_instance.vm_start.name
}

output "vm_ip" {
  description = "External IP of the VM"
  value       = length(google_compute_instance.vm_start.network_interface[0].access_config) > 0 ? google_compute_instance.vm_start.network_interface[0].access_config[0].nat_ip : "No external IP"
}

output "vm_internal_ip" {
  description = "Internal IP of the VM"
  value       = google_compute_instance.vm_start.network_interface[0].network_ip
}
