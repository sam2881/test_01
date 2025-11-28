#!/usr/bin/env python3
"""
Seed Weaviate with historical incident data for RAG similarity search.
This provides context for the 8-step workflow.
"""

import weaviate
import weaviate.classes as wvc
import sys
from datetime import datetime, timedelta

# Historical incident data - realistic examples
HISTORICAL_INCIDENTS = [
    {
        "incident_id": "INC0009988",
        "short_description": "Database high CPU - prod-db-02",
        "description": "PostgreSQL database showing 92% CPU usage. Slow queries identified. Added indexes and optimized queries.",
        "category": "infrastructure",
        "priority": "2",
        "resolution": "Created composite index on orders table. Optimized JOIN queries. CPU reduced to 45%.",
        "root_cause": "Missing database indexes on frequently queried columns causing full table scans",
        "resolution_time_minutes": 35,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["database", "cpu", "postgresql", "slow queries", "index", "gcp"],
        "sys_created_on": (datetime.now() - timedelta(days=15)).isoformat()
    },
    {
        "incident_id": "INC0009975",
        "short_description": "High CPU on MySQL production database",
        "description": "MySQL prod database showing sustained high CPU. Query analysis revealed inefficient queries.",
        "category": "infrastructure",
        "priority": "1",
        "resolution": "Added missing indexes, optimized slow queries, enabled query cache. CPU normalized.",
        "root_cause": "Unoptimized queries without proper indexing strategy",
        "resolution_time_minutes": 42,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["database", "mysql", "cpu", "query optimization", "index", "performance"],
        "sys_created_on": (datetime.now() - timedelta(days=22)).isoformat()
    },
    {
        "incident_id": "INC0009950",
        "short_description": "Database performance degradation - high CPU",
        "description": "Production database experiencing high CPU and slow response times. Multiple long-running queries detected.",
        "category": "infrastructure",
        "priority": "1",
        "resolution": "Identified and killed long-running queries. Added indexes. Implemented query timeout.",
        "root_cause": "Long-running analytical queries running during peak hours without proper indexes",
        "resolution_time_minutes": 55,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["database", "cpu", "performance", "queries", "gcp", "production"],
        "sys_created_on": (datetime.now() - timedelta(days=30)).isoformat()
    },
    {
        "incident_id": "INC0009920",
        "short_description": "GCP VM instance down - prod-web-03",
        "description": "Web server VM terminated unexpectedly. Health checks failing.",
        "category": "infrastructure",
        "priority": "1",
        "resolution": "Restarted VM instance. Investigated logs - OOM killer triggered. Increased memory allocation.",
        "root_cause": "Out of memory condition due to memory leak in application",
        "resolution_time_minutes": 15,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["gcp", "vm", "instance", "down", "terminated", "web server", "oom"],
        "sys_created_on": (datetime.now() - timedelta(days=8)).isoformat()
    },
    {
        "incident_id": "INC0009900",
        "short_description": "VM instance health check failing",
        "description": "GCP compute instance failing health checks. Instance showing TERMINATED status.",
        "category": "infrastructure",
        "priority": "1",
        "resolution": "Restarted instance via gcloud CLI. Updated health check configuration to allow longer startup time.",
        "root_cause": "Application startup time exceeds health check timeout",
        "resolution_time_minutes": 12,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["gcp", "vm", "health check", "terminated", "instance", "compute"],
        "sys_created_on": (datetime.now() - timedelta(days=12)).isoformat()
    },
    {
        "incident_id": "INC0009880",
        "short_description": "Web application unavailable - VM down",
        "description": "Production web application inaccessible. GCP VM instance in STOPPED state.",
        "category": "infrastructure",
        "priority": "1",
        "resolution": "Started VM instance. Root cause: auto-shutdown script triggered incorrectly. Disabled script.",
        "root_cause": "Misconfigured automation script shut down production VM",
        "resolution_time_minutes": 8,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["gcp", "vm", "web", "down", "stopped", "application"],
        "sys_created_on": (datetime.now() - timedelta(days=25)).isoformat()
    },
    {
        "incident_id": "INC0009850",
        "short_description": "Network connectivity issues in GCP",
        "category": "infrastructure",
        "priority": "2",
        "resolution": "Updated firewall rules to allow necessary traffic. Verified VPC configuration.",
        "root_cause": "Firewall rule accidentally deleted during maintenance",
        "resolution_time_minutes": 20,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["gcp", "network", "firewall", "connectivity", "vpc"],
        "sys_created_on": (datetime.now() - timedelta(days=18)).isoformat()
    },
    {
        "incident_id": "INC0009800",
        "short_description": "Redis cache high memory usage",
        "category": "infrastructure",
        "priority": "2",
        "resolution": "Implemented TTL on cache keys. Cleared stale data. Reduced memory usage by 60%.",
        "root_cause": "Cache keys without expiration accumulating over time",
        "resolution_time_minutes": 25,
        "agent_used": "data-agent",
        "success": True,
        "keywords": ["redis", "cache", "memory", "performance", "gcp"],
        "sys_created_on": (datetime.now() - timedelta(days=35)).isoformat()
    },
    {
        "incident_id": "INC0009750",
        "short_description": "API rate limit exceeded - 429 errors",
        "category": "application",
        "priority": "2",
        "resolution": "Implemented request throttling and caching. Optimized API calls to reduce frequency.",
        "root_cause": "Application making excessive API calls without caching",
        "resolution_time_minutes": 45,
        "agent_used": "data-agent",
        "success": True,
        "keywords": ["api", "rate limit", "429", "application", "throttling"],
        "sys_created_on": (datetime.now() - timedelta(days=40)).isoformat()
    },
    {
        "incident_id": "INC0009700",
        "short_description": "Kubernetes pod crashloop - prod namespace",
        "category": "infrastructure",
        "priority": "1",
        "resolution": "Identified misconfigured environment variable. Updated deployment manifest. Pods stabilized.",
        "root_cause": "Missing database connection string in pod environment",
        "resolution_time_minutes": 18,
        "agent_used": "platform-agent",
        "success": True,
        "keywords": ["kubernetes", "pod", "crashloop", "gcp", "deployment", "gke"],
        "sys_created_on": (datetime.now() - timedelta(days=10)).isoformat()
    }
]


def seed_weaviate():
    """Seed Weaviate with historical incident data."""

    try:
        # Connect to Weaviate (v4 syntax)
        client = weaviate.connect_to_local(host="localhost", port=8081)

        # Check if schema exists
        try:
            schema = client.schema.get("HistoricalIncident")
            print("✅ Schema 'HistoricalIncident' exists")
        except:
            print("📝 Creating schema 'HistoricalIncident'...")
            client.schema.create_class({
                "class": "HistoricalIncident",
                "description": "Historical incident resolutions for RAG similarity search",
                "vectorizer": "text2vec-transformers",
                "moduleConfig": {
                    "text2vec-transformers": {
                        "poolingStrategy": "masked_mean"
                    }
                },
                "properties": [
                    {
                        "name": "incident_id",
                        "dataType": ["string"],
                        "description": "Incident ID"
                    },
                    {
                        "name": "short_description",
                        "dataType": ["text"],
                        "description": "Short description of the incident"
                    },
                    {
                        "name": "description",
                        "dataType": ["text"],
                        "description": "Full description"
                    },
                    {
                        "name": "category",
                        "dataType": ["string"],
                        "description": "Incident category"
                    },
                    {
                        "name": "priority",
                        "dataType": ["string"],
                        "description": "Priority level"
                    },
                    {
                        "name": "resolution",
                        "dataType": ["text"],
                        "description": "Resolution steps taken"
                    },
                    {
                        "name": "root_cause",
                        "dataType": ["text"],
                        "description": "Root cause analysis"
                    },
                    {
                        "name": "resolution_time_minutes",
                        "dataType": ["int"],
                        "description": "Time to resolve in minutes"
                    },
                    {
                        "name": "agent_used",
                        "dataType": ["string"],
                        "description": "Which agent resolved it"
                    },
                    {
                        "name": "success",
                        "dataType": ["boolean"],
                        "description": "Whether resolution was successful"
                    },
                    {
                        "name": "keywords",
                        "dataType": ["string[]"],
                        "description": "Keywords for matching"
                    },
                    {
                        "name": "sys_created_on",
                        "dataType": ["string"],
                        "description": "Creation timestamp"
                    }
                ]
            })
            print("✅ Schema created")

        # Delete existing data
        print("🗑️  Clearing existing incidents...")
        try:
            client.batch.delete_objects(
                class_name="HistoricalIncident",
                where={
                    "operator": "Like",
                    "path": ["incident_id"],
                    "valueString": "INC*"
                }
            )
        except:
            pass

        # Add historical incidents
        print(f"📥 Adding {len(HISTORICAL_INCIDENTS)} historical incidents...")

        with client.batch as batch:
            batch.batch_size = 100

            for incident in HISTORICAL_INCIDENTS:
                batch.add_data_object(
                    data_object=incident,
                    class_name="HistoricalIncident"
                )

        # Verify count
        result = client.query.aggregate("HistoricalIncident").with_meta_count().do()
        count = result.get("data", {}).get("Aggregate", {}).get("HistoricalIncident", [{}])[0].get("meta", {}).get("count", 0)

        print(f"✅ Successfully seeded {count} historical incidents in Weaviate")

        # Test similarity search
        print("\n🔍 Testing similarity search for 'database high CPU'...")
        results = client.query.get(
            "HistoricalIncident",
            ["incident_id", "short_description", "resolution", "resolution_time_minutes"]
        ).with_near_text({
            "concepts": ["database high CPU production"]
        }).with_limit(3).with_additional(["distance"]).do()

        if results.get("data", {}).get("Get", {}).get("HistoricalIncident"):
            print("\n📊 Top 3 similar incidents:")
            for i, inc in enumerate(results["data"]["Get"]["HistoricalIncident"], 1):
                distance = inc.get("_additional", {}).get("distance", 0)
                similarity = (1 - distance) * 100
                print(f"\n{i}. {inc['incident_id']} - {inc['short_description']}")
                print(f"   Similarity: {similarity:.1f}%")
                print(f"   Resolution time: {inc['resolution_time_minutes']} minutes")
                print(f"   Solution: {inc['resolution'][:100]}...")

        return True

    except Exception as e:
        print(f"❌ Error seeding Weaviate: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("🌊 Seeding Weaviate with Historical Incident Data")
    print("=" * 80)
    print()

    success = seed_weaviate()

    print()
    print("=" * 80)
    if success:
        print("✅ Seeding completed successfully!")
    else:
        print("❌ Seeding failed!")
        sys.exit(1)
