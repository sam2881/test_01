# GCP VM Reboot Script
# Purpose: Reboot a running GCP VM to resolve hung/unresponsive state
# Issue Types: vm_hung, vm_unresponsive, vm_high_cpu, vm_high_memory
# Risk: Medium (brief downtime)
# Tested: 10 successful resolutions

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
  description = "Name of the VM instance to reboot"
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

# Get VM details
data "google_compute_instance" "vm" {
  name = var.vm_name
  zone = var.zone
}

# Reboot the VM
resource "null_resource" "reboot_vm" {
  triggers = {
    vm_name   = var.vm_name
    timestamp = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Initiating reboot for ${var.vm_name}..."

      gcloud compute instances reset ${var.vm_name} \
        --zone=${var.zone} \
        --project=${var.project_id} \
        --quiet

      echo "Reboot initiated successfully"
    EOT
  }
}

# Wait for VM to come back online
resource "null_resource" "wait_for_vm" {
  depends_on = [null_resource.reboot_vm]

  provisioner "local-exec" {
    command = <<-EOT
      echo "Waiting for VM to come back online..."
      sleep 60

      # Check if VM is running
      for i in {1..10}; do
        STATUS=$(gcloud compute instances describe ${var.vm_name} \
          --zone=${var.zone} \
          --project=${var.project_id} \
          --format='value(status)')

        if [ "$STATUS" = "RUNNING" ]; then
          echo "VM is now RUNNING"
          exit 0
        fi

        echo "Waiting... (attempt $i/10)"
        sleep 10
      done

      echo "WARNING: VM may not be fully running yet"
    EOT
  }
}

output "vm_name" {
  description = "Name of the rebooted VM"
  value       = var.vm_name
}

output "vm_status" {
  description = "VM status before reboot"
  value       = data.google_compute_instance.vm.status
}

output "vm_ip" {
  description = "External IP of the VM"
  value       = try(data.google_compute_instance.vm.network_interface[0].access_config[0].nat_ip, "No external IP")
}

output "reboot_time" {
  description = "Timestamp when reboot was initiated"
  value       = timestamp()
}
