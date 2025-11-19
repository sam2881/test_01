# GCP Cloud SQL Restart Script
# Purpose: Restart Cloud SQL instance to resolve database issues
# Issue Types: database_down, database_slow, database_connection_error
# Risk: Medium (brief database downtime)
# Tested: 6 successful resolutions

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

variable "instance_name" {
  description = "Name of the Cloud SQL instance"
  type        = string
}

variable "region" {
  description = "GCP region where Cloud SQL instance is located"
  type        = string
  default     = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Get Cloud SQL instance details
data "google_sql_database_instance" "instance" {
  name = var.instance_name
}

# Restart Cloud SQL instance
resource "null_resource" "restart_instance" {
  triggers = {
    instance_name = var.instance_name
    timestamp     = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Restarting Cloud SQL instance: ${var.instance_name}"

      gcloud sql instances restart ${var.instance_name} \
        --project=${var.project_id} \
        --quiet

      echo "Restart command executed"
    EOT
  }
}

# Wait for instance to be ready
resource "null_resource" "wait_for_instance" {
  depends_on = [null_resource.restart_instance]

  provisioner "local-exec" {
    command = <<-EOT
      echo "Waiting for Cloud SQL instance to be ready..."

      for i in {1..20}; do
        STATE=$(gcloud sql instances describe ${var.instance_name} \
          --project=${var.project_id} \
          --format='value(state)')

        if [ "$STATE" = "RUNNABLE" ]; then
          echo "Cloud SQL instance is now RUNNABLE"
          exit 0
        fi

        echo "Current state: $STATE (attempt $i/20)"
        sleep 15
      done

      echo "WARNING: Instance may not be fully ready"
    EOT
  }
}

output "instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = var.instance_name
}

output "instance_state" {
  description = "State of the Cloud SQL instance before restart"
  value       = data.google_sql_database_instance.instance.state
}

output "connection_name" {
  description = "Connection name for the Cloud SQL instance"
  value       = data.google_sql_database_instance.instance.connection_name
}

output "ip_address" {
  description = "IP address of the Cloud SQL instance"
  value       = try(data.google_sql_database_instance.instance.ip_address[0].ip_address, "No IP address")
}
