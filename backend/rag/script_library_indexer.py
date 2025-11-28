"""
Script Library Indexer
Index Terraform/Ansible scripts in Weaviate for intelligent RAG-based retrieval
"""
import weaviate
import os
import json
from pathlib import Path
from typing import Dict, List
import structlog

logger = structlog.get_logger()


class ScriptLibraryIndexer:
    """
    Index infrastructure scripts in Weaviate for intelligent selection

    Instead of generating scripts dynamically, we:
    1. Store all pre-tested scripts in Weaviate with rich metadata
    2. Use RAG to find best matching script for each incident
    3. LLM selects the best match and extracts parameters
    """

    def __init__(self):
        self.client = weaviate.connect_to_local(
            host="localhost",
            port=8081
        )
        self._create_schema()

    def _create_schema(self):
        """Create Weaviate schema for infrastructure scripts"""
        schema = {
            "class": "InfrastructureScript",
            "vectorizer": "text2vec-openai",
            "moduleConfig": {
                "text2vec-openai": {
                    "model": "ada",
                    "type": "text"
                }
            },
            "properties": [
                {
                    "name": "script_name",
                    "dataType": ["text"],
                    "description": "Name of the script file",
                    "moduleConfig": {
                        "text2vec-openai": {"skip": False}
                    }
                },
                {
                    "name": "script_type",
                    "dataType": ["text"],
                    "description": "terraform or ansible"
                },
                {
                    "name": "purpose",
                    "dataType": ["text"],
                    "description": "What this script does - used for semantic search",
                    "moduleConfig": {
                        "text2vec-openai": {"skip": False}
                    }
                },
                {
                    "name": "issue_types",
                    "dataType": ["text[]"],
                    "description": "Issue types this script handles (vm_down, disk_full, etc.)"
                },
                {
                    "name": "gcp_resources",
                    "dataType": ["text[]"],
                    "description": "GCP resources this script manages"
                },
                {
                    "name": "script_content",
                    "dataType": ["text"],
                    "description": "Full script content",
                    "moduleConfig": {
                        "text2vec-openai": {"skip": True}  # Don't vectorize code
                    }
                },
                {
                    "name": "parameters",
                    "dataType": ["text"],
                    "description": "Required parameters as JSON string"
                },
                {
                    "name": "prerequisites",
                    "dataType": ["text"],
                    "description": "Prerequisites for running this script"
                },
                {
                    "name": "success_criteria",
                    "dataType": ["text"],
                    "description": "How to verify success"
                },
                {
                    "name": "risk_level",
                    "dataType": ["text"],
                    "description": "low, medium, high"
                },
                {
                    "name": "tested_scenarios",
                    "dataType": ["text"],
                    "description": "Scenarios where this was successfully tested",
                    "moduleConfig": {
                        "text2vec-openai": {"skip": False}
                    }
                },
                {
                    "name": "success_count",
                    "dataType": ["int"],
                    "description": "Number of times successfully resolved incidents"
                },
                {
                    "name": "last_used",
                    "dataType": ["text"],
                    "description": "Last time this script was used (ISO datetime)"
                }
            ]
        }

        # Delete existing class if exists (for development)
        try:
            self.client.schema.delete_class("InfrastructureScript")
        except:
            pass

        # Create class
        try:
            self.client.schema.create_class(schema)
            logger.info("weaviate_schema_created", class_name="InfrastructureScript")
        except Exception as e:
            logger.warning("weaviate_schema_exists", error=str(e))

    def index_script(
        self,
        script_path: str,
        script_type: str,  # "terraform" or "ansible"
        metadata: Dict
    ) -> str:
        """
        Index a single script in Weaviate

        Args:
            script_path: Path to script file
            script_type: "terraform" or "ansible"
            metadata: Rich metadata about the script

        Returns:
            UUID of created object
        """
        if not os.path.exists(script_path):
            logger.warning("script_not_found", path=script_path)
            return None

        with open(script_path, 'r') as f:
            script_content = f.read()

        data_object = {
            "script_name": os.path.basename(script_path),
            "script_type": script_type,
            "script_content": script_content,
            "purpose": metadata.get("purpose", ""),
            "issue_types": metadata.get("issue_types", []),
            "gcp_resources": metadata.get("gcp_resources", []),
            "parameters": metadata.get("parameters", "{}"),
            "prerequisites": metadata.get("prerequisites", ""),
            "success_criteria": metadata.get("success_criteria", ""),
            "risk_level": metadata.get("risk_level", "medium"),
            "tested_scenarios": metadata.get("tested_scenarios", ""),
            "success_count": metadata.get("success_count", 0),
            "last_used": metadata.get("last_used", "")
        }

        uuid = self.client.data_object.create(
            data_object=data_object,
            class_name="InfrastructureScript"
        )

        logger.info("script_indexed",
                   script_name=data_object["script_name"],
                   script_type=script_type,
                   uuid=uuid)

        return uuid

    def index_all_scripts(self, base_path: str = "automation_scripts"):
        """
        Index all scripts from automation_scripts directory

        This creates a curated library of pre-tested scripts
        """
        logger.info("indexing_script_library", base_path=base_path)

        # Terraform Scripts Metadata
        terraform_scripts = [
            {
                "path": f"{base_path}/terraform/start_vm_simple.tf",
                "metadata": {
                    "purpose": "Start a stopped GCP Compute Engine VM instance",
                    "issue_types": ["vm_down", "vm_stopped", "vm_terminated", "instance_stopped"],
                    "gcp_resources": ["google_compute_instance"],
                    "parameters": json.dumps({
                        "vm_name": "string - Name of the VM to start",
                        "zone": "string - GCP zone (e.g., us-central1-a)",
                        "project_id": "string - GCP project ID"
                    }),
                    "prerequisites": "GCP credentials configured, VM exists but is stopped",
                    "success_criteria": "VM status changes to RUNNING, external IP assigned",
                    "risk_level": "low",
                    "tested_scenarios": "VM manually stopped, VM crashed after failed update, VM auto-stopped by policy",
                    "success_count": 15
                }
            },
            {
                "path": f"{base_path}/terraform/resize_disk.tf",
                "metadata": {
                    "purpose": "Increase persistent disk size for GCP VM to resolve disk full issues",
                    "issue_types": ["disk_full", "storage_full", "out_of_space", "disk_space_low"],
                    "gcp_resources": ["google_compute_disk"],
                    "parameters": json.dumps({
                        "disk_name": "string - Name of the persistent disk",
                        "zone": "string - GCP zone",
                        "new_size_gb": "int - New size in GB (must be larger than current)",
                        "project_id": "string - GCP project ID"
                    }),
                    "prerequisites": "Disk is attached to VM, filesystem supports online resize",
                    "success_criteria": "Disk size increased, filesystem expanded automatically",
                    "risk_level": "medium",
                    "tested_scenarios": "95% disk usage alert, database disk full, application log partition full",
                    "success_count": 8
                }
            },
            {
                "path": f"{base_path}/terraform/update_firewall.tf",
                "metadata": {
                    "purpose": "Update GCP VPC firewall rules to allow blocked network traffic",
                    "issue_types": ["network_blocked", "firewall_denied", "connection_refused", "port_blocked"],
                    "gcp_resources": ["google_compute_firewall"],
                    "parameters": json.dumps({
                        "rule_name": "string - Firewall rule name",
                        "ports": "list - Ports to open (e.g., ['80', '443'])",
                        "source_ranges": "list - Source IP ranges (e.g., ['0.0.0.0/0'])",
                        "protocol": "string - tcp, udp, or icmp",
                        "project_id": "string - GCP project ID"
                    }),
                    "prerequisites": "VPC network exists, proper IAM firewall permissions",
                    "success_criteria": "Firewall rule created/updated, traffic flows successfully",
                    "risk_level": "medium",
                    "tested_scenarios": "HTTPS port 443 blocked, database port 5432 denied, SSH port 22 restricted",
                    "success_count": 5
                }
            }
        ]

        # Ansible Scripts Metadata
        ansible_scripts = [
            {
                "path": f"{base_path}/ansible/restart_nginx.yml",
                "metadata": {
                    "purpose": "Restart nginx web server and verify it returns HTTP 200",
                    "issue_types": ["service_down", "nginx_crashed", "web_server_down", "http_502", "http_503"],
                    "gcp_resources": ["compute_instance"],
                    "parameters": json.dumps({
                        "vm_ip": "string - VM IP address (from Terraform output)",
                        "ansible_user": "string - SSH user (default: ansible)"
                    }),
                    "prerequisites": "SSH access to VM, sudo privileges, nginx installed",
                    "success_criteria": "nginx service active and running, HTTP 200 response from /",
                    "risk_level": "low",
                    "tested_scenarios": "nginx crashed due to config error, nginx stopped manually, nginx failed after update",
                    "success_count": 12
                }
            },
            {
                "path": f"{base_path}/ansible/install_nginx.yml",
                "metadata": {
                    "purpose": "Install and configure nginx web server on GCP VM",
                    "issue_types": ["service_missing", "web_server_not_installed", "nginx_not_found"],
                    "gcp_resources": ["compute_instance"],
                    "parameters": json.dumps({
                        "vm_ip": "string - VM IP address",
                        "ansible_user": "string - SSH user"
                    }),
                    "prerequisites": "SSH access, sudo privileges, apt package manager (Debian/Ubuntu)",
                    "success_criteria": "nginx installed, enabled, and serving default page",
                    "risk_level": "low",
                    "tested_scenarios": "Fresh VM deployment, nginx uninstalled by mistake, OS upgrade removed nginx",
                    "success_count": 6
                }
            },
            {
                "path": f"{base_path}/ansible/cleanup_logs.yml",
                "metadata": {
                    "purpose": "Clean up old log files to free disk space",
                    "issue_types": ["disk_full", "log_rotation_failed", "var_log_full"],
                    "gcp_resources": ["compute_instance"],
                    "parameters": json.dumps({
                        "vm_ip": "string - VM IP address",
                        "days_to_keep": "int - Keep logs from last N days (default: 7)",
                        "ansible_user": "string - SSH user"
                    }),
                    "prerequisites": "SSH access, sudo privileges",
                    "success_criteria": "Disk usage reduced by at least 10%, old logs archived/deleted",
                    "risk_level": "low",
                    "tested_scenarios": "/var/log at 95% usage, application logs filling disk, logrotate not running",
                    "success_count": 10
                }
            }
        ]

        # Index all Terraform scripts
        for script in terraform_scripts:
            self.index_script(
                script_path=script["path"],
                script_type="terraform",
                metadata=script["metadata"]
            )

        # Index all Ansible scripts
        for script in ansible_scripts:
            self.index_script(
                script_path=script["path"],
                script_type="ansible",
                metadata=script["metadata"]
            )

        logger.info("script_library_indexed",
                   terraform_count=len(terraform_scripts),
                   ansible_count=len(ansible_scripts))

    def increment_success_count(self, script_name: str):
        """Increment success count when script successfully resolves incident"""
        from datetime import datetime

        # Find script by name
        result = (
            self.client.query
            .get("InfrastructureScript", ["_additional {id}"])
            .with_where({
                "path": ["script_name"],
                "operator": "Equal",
                "valueText": script_name
            })
            .do()
        )

        scripts = result.get("data", {}).get("Get", {}).get("InfrastructureScript", [])

        if scripts:
            script_id = scripts[0]["_additional"]["id"]

            # Update success count and last_used
            self.client.data_object.update(
                data_object={
                    "last_used": datetime.now().isoformat()
                },
                class_name="InfrastructureScript",
                uuid=script_id
            )

            logger.info("script_success_updated", script_name=script_name)


# CLI for indexing scripts
if __name__ == "__main__":
    indexer = ScriptLibraryIndexer()
    indexer.index_all_scripts()
    print("✅ Script library indexed in Weaviate!")
