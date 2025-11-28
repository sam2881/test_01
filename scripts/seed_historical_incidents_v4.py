#!/usr/bin/env python3
"""
Seed Weaviate with historical incident data for RAG similarity search.
Uses Weaviate Python Client v4 API.
"""

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
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
        "description": "Production network experiencing intermittent connectivity issues. Packet loss detected.",
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
        "description": "Redis instance consuming excessive memory. Risk of OOM.",
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
        "description": "Application receiving 429 errors from third-party API.",
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
        "description": "Production pods in crashloop state. Application failing to start.",
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

    client = None
    try:
        # Connect to Weaviate (v4 syntax)
        print("🔌 Connecting to Weaviate...")
        client = weaviate.connect_to_local(host="localhost", port=8081)
        print("✅ Connected to Weaviate")

        # Check if collection exists
        collections = client.collections.list_all()
        collection_names = [c.name for c in collections.values()]

        if "HistoricalIncident" in collection_names:
            print("🗑️  Deleting existing 'HistoricalIncident' collection...")
            client.collections.delete("HistoricalIncident")

        # Create collection
        print("📝 Creating 'HistoricalIncident' collection...")
        client.collections.create(
            name="HistoricalIncident",
            description="Historical incident resolutions for RAG similarity search",
            vectorizer_config=Configure.Vectorizer.none(),  # We'll use default vectorization
            properties=[
                Property(name="incident_id", data_type=DataType.TEXT),
                Property(name="short_description", data_type=DataType.TEXT),
                Property(name="description", data_type=DataType.TEXT),
                Property(name="category", data_type=DataType.TEXT),
                Property(name="priority", data_type=DataType.TEXT),
                Property(name="resolution", data_type=DataType.TEXT),
                Property(name="root_cause", data_type=DataType.TEXT),
                Property(name="resolution_time_minutes", data_type=DataType.INT),
                Property(name="agent_used", data_type=DataType.TEXT),
                Property(name="success", data_type=DataType.BOOL),
                Property(name="keywords", data_type=DataType.TEXT_ARRAY),
                Property(name="sys_created_on", data_type=DataType.TEXT),
            ]
        )
        print("✅ Collection created")

        # Get collection
        collection = client.collections.get("HistoricalIncident")

        # Add historical incidents
        print(f"📥 Adding {len(HISTORICAL_INCIDENTS)} historical incidents...")

        for incident in HISTORICAL_INCIDENTS:
            collection.data.insert(
                properties=incident
            )

        # Verify count
        response = collection.aggregate.over_all(total_count=True)
        count = response.total_count

        print(f"✅ Successfully seeded {count} historical incidents in Weaviate")

        # Test similarity search
        print("\n🔍 Testing similarity search for 'database high CPU'...")
        results = collection.query.near_text(
            query="database high CPU production",
            limit=3,
            return_metadata=MetadataQuery(distance=True)
        )

        if results.objects:
            print("\n📊 Top 3 similar incidents:")
            for i, obj in enumerate(results.objects, 1):
                similarity = (1 - obj.metadata.distance) * 100 if obj.metadata.distance else 0
                print(f"\n{i}. {obj.properties['incident_id']} - {obj.properties['short_description']}")
                print(f"   Similarity: {similarity:.1f}%")
                print(f"   Resolution time: {obj.properties['resolution_time_minutes']} minutes")
                print(f"   Solution: {obj.properties['resolution'][:100]}...")

        return True

    except Exception as e:
        print(f"❌ Error seeding Weaviate: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if client:
            client.close()
            print("\n🔌 Disconnected from Weaviate")


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
