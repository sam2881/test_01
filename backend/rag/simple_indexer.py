"""
Simple Script Indexer for Weaviate v4
"""
import weaviate
import weaviate.classes as wvc
import os
import json
from pathlib import Path

# Script metadata
TERRAFORM_SCRIPTS = [
    {
        "script_name": "gcp_vm_start.tf",
        "script_type": "terraform",
        "purpose": "Start a stopped GCP VM instance",
        "issue_types": ["vm_down", "vm_stopped", "instance_stopped"],
        "gcp_resources": ["compute_instance"],
        "parameters": json.dumps({"vm_name": "string", "zone": "string", "project_id": "string"}),
        "success_count": 15,
        "risk_level": "low"
    },
    {
        "script_name": "gcp_disk_resize.tf",
        "script_type": "terraform",
        "purpose": "Resize a GCP persistent disk when out of space",
        "issue_types": ["disk_full", "storage_full", "out_of_space"],
        "gcp_resources": ["compute_disk"],
        "parameters": json.dumps({"disk_name": "string", "zone": "string", "new_size_gb": "int"}),
        "success_count": 8,
        "risk_level": "medium"
    },
    {
        "script_name": "gcp_firewall_allow.tf",
        "script_type": "terraform",
        "purpose": "Add firewall rule to allow blocked traffic",
        "issue_types": ["network_blocked", "firewall_denied", "connection_refused"],
        "gcp_resources": ["compute_firewall"],
        "parameters": json.dumps({"rule_name": "string", "port": "int", "protocol": "string", "source_ranges": "list"}),
        "success_count": 5,
        "risk_level": "high"
    },
    {
        "script_name": "gcp_vm_reboot.tf",
        "script_type": "terraform",
        "purpose": "Reboot a hung or unresponsive VM",
        "issue_types": ["vm_hung", "vm_unresponsive", "vm_high_cpu"],
        "gcp_resources": ["compute_instance"],
        "parameters": json.dumps({"vm_name": "string", "zone": "string"}),
        "success_count": 10,
        "risk_level": "medium"
    },
    {
        "script_name": "gcp_cloudsql_restart.tf",
        "script_type": "terraform",
        "purpose": "Restart Cloud SQL instance",
        "issue_types": ["database_down", "database_slow", "db_connection_refused"],
        "gcp_resources": ["sql_database_instance"],
        "parameters": json.dumps({"instance_name": "string", "project_id": "string"}),
        "success_count": 6,
        "risk_level": "high"
    }
]

ANSIBLE_PLAYBOOKS = [
    {
        "script_name": "service_restart.yml",
        "script_type": "ansible",
        "purpose": "Restart a systemd service and verify it's running",
        "issue_types": ["service_down", "service_crashed", "service_hung"],
        "gcp_resources": [],
        "parameters": json.dumps({"service_name": "string", "target_hosts": "list"}),
        "success_count": 20,
        "risk_level": "low"
    },
    {
        "script_name": "disk_cleanup.yml",
        "script_type": "ansible",
        "purpose": "Clean disk space by removing old logs and temp files",
        "issue_types": ["disk_full", "low_disk_space"],
        "gcp_resources": [],
        "parameters": json.dumps({"min_free_gb": "int", "target_hosts": "list"}),
        "success_count": 15,
        "risk_level": "low"
    },
    {
        "script_name": "app_health_check.yml",
        "script_type": "ansible",
        "purpose": "Check application health and attempt auto-recovery",
        "issue_types": ["app_unhealthy", "health_check_failing"],
        "gcp_resources": [],
        "parameters": json.dumps({"app_name": "string", "health_endpoint": "string", "target_hosts": "list"}),
        "success_count": 12,
        "risk_level": "low"
    },
    {
        "script_name": "database_backup.yml",
        "script_type": "ansible",
        "purpose": "Backup PostgreSQL or MySQL database",
        "issue_types": ["database_backup_needed", "data_protection"],
        "gcp_resources": [],
        "parameters": json.dumps({"db_type": "string", "db_name": "string", "backup_path": "string"}),
        "success_count": 10,
        "risk_level": "medium"
    },
    {
        "script_name": "network_diagnostics.yml",
        "script_type": "ansible",
        "purpose": "Diagnose network connectivity issues",
        "issue_types": ["network_down", "connection_timeout", "dns_failure"],
        "gcp_resources": [],
        "parameters": json.dumps({"target_host": "string", "test_endpoints": "list"}),
        "success_count": 8,
        "risk_level": "low"
    }
]


def main():
    print("🔌 Connecting to Weaviate...")
    client = weaviate.connect_to_local(
        host="localhost",
        port=8081,
        skip_init_checks=True
    )

    try:
        print("📋 Creating InfrastructureScript collection...")

        # Delete existing collection if it exists
        try:
            client.collections.delete("InfrastructureScript")
            print("  ✓ Deleted existing collection")
        except:
            pass

        # Create new collection
        collection = client.collections.create(
            name="InfrastructureScript",
            vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(
                model="ada"
            ),
            properties=[
                wvc.config.Property(
                    name="script_name",
                    data_type=wvc.config.DataType.TEXT
                ),
                wvc.config.Property(
                    name="script_type",
                    data_type=wvc.config.DataType.TEXT
                ),
                wvc.config.Property(
                    name="purpose",
                    data_type=wvc.config.DataType.TEXT
                ),
                wvc.config.Property(
                    name="issue_types",
                    data_type=wvc.config.DataType.TEXT_ARRAY
                ),
                wvc.config.Property(
                    name="gcp_resources",
                    data_type=wvc.config.DataType.TEXT_ARRAY
                ),
                wvc.config.Property(
                    name="parameters",
                    data_type=wvc.config.DataType.TEXT
                ),
                wvc.config.Property(
                    name="success_count",
                    data_type=wvc.config.DataType.INT
                ),
                wvc.config.Property(
                    name="risk_level",
                    data_type=wvc.config.DataType.TEXT
                )
            ]
        )
        print("  ✓ Collection created")

        # Index scripts
        print("\n📦 Indexing Terraform scripts...")
        terraform_collection = client.collections.get("InfrastructureScript")
        for script in TERRAFORM_SCRIPTS:
            terraform_collection.data.insert(
                properties=script
            )
            print(f"  ✓ Indexed {script['script_name']}")

        print("\n📦 Indexing Ansible playbooks...")
        for script in ANSIBLE_PLAYBOOKS:
            terraform_collection.data.insert(
                properties=script
            )
            print(f"  ✓ Indexed {script['script_name']}")

        # Verify
        print("\n✅ Verifying indexed scripts...")
        result = terraform_collection.aggregate.over_all(total_count=True)
        print(f"  Total scripts indexed: {result.total_count}")

        print("\n🎉 Indexing complete!")

    finally:
        client.close()


if __name__ == "__main__":
    main()
