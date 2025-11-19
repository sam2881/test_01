# GCP Firewall Allow Rule
# Purpose: Create/update firewall rule to allow blocked traffic
# Issue Types: network_blocked, firewall_denied, connection_refused, port_blocked
# Risk: Medium (network security change)
# Tested: 5 successful resolutions

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

variable "rule_name" {
  description = "Name of the firewall rule"
  type        = string
  default     = "allow-incident-fix"
}

variable "ports" {
  description = "List of ports to allow (e.g., ['80', '443', '22'])"
  type        = list(string)
}

variable "protocol" {
  description = "Protocol to allow (tcp, udp, icmp)"
  type        = string
  default     = "tcp"
}

variable "source_ranges" {
  description = "Source IP ranges (CIDR notation)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "target_tags" {
  description = "Target VM tags (leave empty for all VMs)"
  type        = list(string)
  default     = []
}

variable "network" {
  description = "VPC network name"
  type        = string
  default     = "default"
}

provider "google" {
  project = var.project_id
}

# Create firewall rule
resource "google_compute_firewall" "allow_rule" {
  name    = var.rule_name
  network = var.network

  allow {
    protocol = var.protocol
    ports    = var.ports
  }

  source_ranges = var.source_ranges
  target_tags   = length(var.target_tags) > 0 ? var.target_tags : null

  description = "Auto-created by incident resolution system at ${timestamp()}"

  # Priority (lower number = higher priority)
  priority = 1000
}

# Verification check
resource "null_resource" "verify_rule" {
  depends_on = [google_compute_firewall.allow_rule]

  provisioner "local-exec" {
    command = <<-EOT
      echo "Firewall rule created successfully"
      gcloud compute firewall-rules describe ${var.rule_name} \
        --project=${var.project_id} \
        --format='value(name,allowed)'
    EOT
  }
}

output "rule_name" {
  description = "Name of the created firewall rule"
  value       = google_compute_firewall.allow_rule.name
}

output "rule_id" {
  description = "Full resource ID of the firewall rule"
  value       = google_compute_firewall.allow_rule.id
}

output "allowed_ports" {
  description = "Ports that are now allowed"
  value       = var.ports
}

output "protocol" {
  description = "Protocol that is now allowed"
  value       = var.protocol
}

output "source_ranges" {
  description = "Source IP ranges that are allowed"
  value       = var.source_ranges
}
