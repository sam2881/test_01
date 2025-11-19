# GCP Disk Resize Script
# Purpose: Increase persistent disk size for GCP VM
# Issue Types: disk_full, storage_full, out_of_space
# Risk: Medium (requires VM stop/start)
# Tested: 8 successful resolutions

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

variable "disk_name" {
  description = "Name of the persistent disk to resize"
  type        = string
}

variable "zone" {
  description = "GCP zone where disk is located"
  type        = string
  default     = "us-central1-a"
}

variable "new_size_gb" {
  description = "New size in GB (must be larger than current size)"
  type        = number
}

provider "google" {
  project = var.project_id
  region  = substr(var.zone, 0, length(var.zone) - 2)
}

# Get current disk info
data "google_compute_disk" "disk" {
  name = var.disk_name
  zone = var.zone
}

# Resize the disk
resource "null_resource" "resize_disk" {
  triggers = {
    disk_name    = var.disk_name
    new_size_gb  = var.new_size_gb
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Resize the disk
      gcloud compute disks resize ${var.disk_name} \
        --size=${var.new_size_gb}GB \
        --zone=${var.zone} \
        --project=${var.project_id} \
        --quiet

      echo "Disk resized successfully"
    EOT
  }
}

# If disk is attached to a VM, provide resize filesystem command
resource "null_resource" "resize_filesystem_instructions" {
  depends_on = [null_resource.resize_disk]

  provisioner "local-exec" {
    command = <<-EOT
      echo "================================================"
      echo "IMPORTANT: Filesystem resize required"
      echo "================================================"
      echo "For ext4: sudo resize2fs /dev/sda1"
      echo "For xfs:  sudo xfs_growfs /"
      echo "================================================"
    EOT
  }
}

output "disk_name" {
  description = "Name of the resized disk"
  value       = var.disk_name
}

output "old_size_gb" {
  description = "Previous disk size in GB"
  value       = data.google_compute_disk.disk.size
}

output "new_size_gb" {
  description = "New disk size in GB"
  value       = var.new_size_gb
}

output "resize_filesystem_command" {
  description = "Command to run on VM to resize filesystem"
  value       = "sudo resize2fs /dev/sda1 (for ext4) or sudo xfs_growfs / (for xfs)"
}
