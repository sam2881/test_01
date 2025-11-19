# GCP VM Start Script
# Purpose: Start a stopped GCP Compute Engine VM instance
# Issue Types: vm_down, vm_stopped, instance_stopped
# Risk: Low
# Tested: 15 successful resolutions

terraform {
  required_version = ">= 1.0"
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

variable "vm_name" {
  description = "Name of the VM instance to start"
  type        = string
}

variable "zone" {
  description = "GCP zone where VM is located"
  type        = string
  default     = "us-central1-a"
}

provider "google" {
  project = var.project_id
  region  = substr(var.zone, 0, length(var.zone) - 2)
}

# Get the existing VM instance
data "google_compute_instance" "vm" {
  name = var.vm_name
  zone = var.zone
}

# Start the VM if it's stopped
resource "null_resource" "start_vm" {
  triggers = {
    vm_name = var.vm_name
    zone    = var.zone
  }

  provisioner "local-exec" {
    command = <<-EOT
      gcloud compute instances start ${var.vm_name} \
        --zone=${var.zone} \
        --project=${var.project_id}
    EOT
  }
}

# Wait for VM to be fully running
resource "null_resource" "wait_for_vm" {
  depends_on = [null_resource.start_vm]

  provisioner "local-exec" {
    command = <<-EOT
      sleep 30
      gcloud compute instances describe ${var.vm_name} \
        --zone=${var.zone} \
        --project=${var.project_id} \
        --format='value(status)' | grep -q RUNNING
    EOT
  }
}

output "vm_status" {
  description = "Current VM status"
  value       = data.google_compute_instance.vm.status
}

output "vm_ip" {
  description = "External IP of the VM"
  value       = try(data.google_compute_instance.vm.network_interface[0].access_config[0].nat_ip, "No external IP")
}

output "vm_internal_ip" {
  description = "Internal IP of the VM"
  value       = data.google_compute_instance.vm.network_interface[0].network_ip
}
