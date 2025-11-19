# Simplified Terraform script to start a GCP VM using gcloud
# This is more reliable for just starting/stopping VMs

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
  credentials = file(var.credentials_file)
}

# Use null_resource with local-exec to start VM
resource "null_resource" "start_vm" {
  provisioner "local-exec" {
    command = <<-EOT
      gcloud compute instances start ${var.vm_name} \
        --zone=${var.zone} \
        --project=${var.project_id}
    EOT

    environment = {
      GOOGLE_APPLICATION_CREDENTIALS = var.credentials_file
    }
  }

  # Trigger on every apply
  triggers = {
    always_run = timestamp()
  }
}

# Get VM status after starting
data "google_compute_instance" "vm" {
  name = var.vm_name
  zone = var.zone

  depends_on = [null_resource.start_vm]
}

output "vm_status" {
  description = "Current status of the VM"
  value       = data.google_compute_instance.vm.current_status
}

output "vm_name" {
  description = "Name of the VM"
  value       = data.google_compute_instance.vm.name
}

output "vm_external_ip" {
  description = "External IP of the VM"
  value       = length(data.google_compute_instance.vm.network_interface[0].access_config) > 0 ? data.google_compute_instance.vm.network_interface[0].access_config[0].nat_ip : "No external IP"
}

output "vm_internal_ip" {
  description = "Internal IP of the VM"
  value       = data.google_compute_instance.vm.network_interface[0].network_ip
}
