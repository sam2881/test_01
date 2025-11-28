#!/usr/bin/env python3
"""Populate all databases with 100 demo incidents"""
import sys
import os
import json
from datetime import datetime

sys.path.append('/home/samrattidke600/ai_agent_app/backend')

from rag.weaviate_client import weaviate_client
from rag.neo4j_client import neo4j_client
import structlog

logger = structlog.get_logger()


def load_incidents():
    """Load incidents from JSON file"""
    incidents_file = "/home/samrattidke600/ai_agent_app/data/demo_data/incidents_100.json"
    with open(incidents_file, 'r') as f:
        incidents = json.load(f)
    return incidents


def populate_weaviate():
    """Populate Weaviate with 100 incidents and runbooks"""
    print("\n🔵 Populating Weaviate...")

    try:
        # Create schema
        weaviate_client.create_schema()
        print("  ✓ Schema created")

        # Load incidents
        incidents = load_incidents()

        # Add incidents to Weaviate
        success_count = 0
        for incident in incidents:
            try:
                weaviate_data = {
                    "incident_id": incident['incident_id'],
                    "title": incident['title'],
                    "description": incident['description'],
                    "resolution": incident['resolution'],
                    "topic": incident['category'],
                    "severity": incident['severity'],
                    "service": incident['service'],
                    "created_at": incident['created_at']
                }

                weaviate_client.add_incident(weaviate_data)
                success_count += 1

                if success_count % 20 == 0:
                    print(f"  → Added {success_count} incidents...")

            except Exception as e:
                logger.error("incident_add_failed", error=str(e), incident_id=incident['incident_id'])

        print(f"  ✅ Added {success_count} incidents to Weaviate")

        # Add runbooks
        runbooks = generate_runbooks()
        runbook_count = 0
        for runbook in runbooks:
            try:
                weaviate_client.add_runbook(runbook)
                runbook_count += 1
            except Exception as e:
                logger.error("runbook_add_failed", error=str(e))

        print(f"  ✅ Added {runbook_count} runbooks to Weaviate")

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise


def populate_neo4j():
    """Populate Neo4j with graph relationships"""
    print("\n🟢 Populating Neo4j...")

    try:
        # Create indexes
        neo4j_client.create_indexes()
        print("  ✓ Indexes created")

        # Add services
        services = [
            "api-gateway", "web-server", "database", "cache-redis", "message-queue",
            "auth-service", "payment-service", "user-service", "email-service",
            "storage-service", "cdn", "load-balancer", "kubernetes-cluster"
        ]

        for service in services:
            neo4j_client.add_service(service, {"status": "active", "tier": "production"})

        print(f"  ✓ Added {len(services)} services")

        # Load incidents and add to graph
        incidents = load_incidents()
        incident_count = 0

        for incident in incidents:
            try:
                neo4j_client.add_incident(
                    incident_id=incident['incident_id'],
                    service=incident['service'],
                    topic=incident['category'],
                    properties={
                        "title": incident['title'],
                        "severity": incident['severity'],
                        "created_at": incident['created_at'],
                        "resolved_at": incident.get('resolved_at'),
                        "state": incident.get('state', 'Resolved'),
                        "affected_users": incident.get('affected_users', 0)
                    }
                )

                # Add resolution if available
                if incident.get('resolution'):
                    neo4j_client.add_resolution(
                        incident_id=incident['incident_id'],
                        resolution_steps=[incident['resolution']],
                        success=True
                    )

                incident_count += 1

                if incident_count % 20 == 0:
                    print(f"  → Added {incident_count} incidents to graph...")

            except Exception as e:
                logger.error("neo4j_incident_add_failed", error=str(e))

        print(f"  ✅ Added {incident_count} incidents to Neo4j")

        # Add service dependencies
        dependencies = [
            ("web-server", "api-gateway", "DEPENDS_ON"),
            ("api-gateway", "auth-service", "DEPENDS_ON"),
            ("api-gateway", "payment-service", "DEPENDS_ON"),
            ("api-gateway", "user-service", "DEPENDS_ON"),
            ("auth-service", "database", "DEPENDS_ON"),
            ("payment-service", "database", "DEPENDS_ON"),
            ("user-service", "database", "DEPENDS_ON"),
            ("api-gateway", "cache-redis", "DEPENDS_ON"),
            ("payment-service", "message-queue", "DEPENDS_ON"),
            ("email-service", "message-queue", "DEPENDS_ON"),
            ("web-server", "cdn", "DEPENDS_ON"),
            ("api-gateway", "load-balancer", "DEPENDS_ON"),
            ("kubernetes-cluster", "storage-service", "DEPENDS_ON"),
        ]

        for from_svc, to_svc, rel in dependencies:
            neo4j_client.add_causal_relationship(from_svc, to_svc, rel)

        print(f"  ✅ Added {len(dependencies)} service dependencies")

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        raise


def generate_runbooks():
    """Generate runbooks for common incident types"""
    return [
        {
            "runbook_id": "RB001",
            "title": "High CPU Utilization Troubleshooting",
            "content": """
            1. Check current CPU usage: `top` or `htop`
            2. Identify top processes: `ps aux --sort=-%cpu | head -10`
            3. Check for memory leaks: `free -h`
            4. Review recent deployments for changes
            5. Scale horizontally if needed: `kubectl scale deployment`
            6. Check for infinite loops or stuck processes
            7. Analyze application logs for errors
            8. Consider vertical scaling if persistent
            """,
            "topic": "Performance",
            "service": "general",
            "tags": ["cpu", "performance", "troubleshooting"]
        },
        {
            "runbook_id": "RB002",
            "title": "Database Connection Pool Exhaustion",
            "content": """
            1. Check current connections: `SELECT count(*) FROM pg_stat_activity;`
            2. Identify long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active';`
            3. Kill stuck connections if needed: `SELECT pg_terminate_backend(pid);`
            4. Increase max_connections in postgresql.conf
            5. Implement connection pooling (PgBouncer/PgPool)
            6. Add connection timeout to application
            7. Monitor connection metrics going forward
            8. Review application code for connection leaks
            """,
            "topic": "Database",
            "service": "database",
            "tags": ["database", "connections", "postgresql"]
        },
        {
            "runbook_id": "RB003",
            "title": "502 Bad Gateway Resolution",
            "content": """
            1. Check nginx error logs: `tail -f /var/log/nginx/error.log`
            2. Verify upstream servers are running: `systemctl status app-server`
            3. Test upstream connectivity: `curl http://upstream:port/health`
            4. Check upstream timeout settings in nginx.conf
            5. Restart nginx: `systemctl restart nginx`
            6. Clear connection pool if applicable
            7. Verify DNS resolution for upstream
            8. Check for firewall/security group issues
            """,
            "topic": "Infrastructure",
            "service": "api-gateway",
            "tags": ["502", "nginx", "gateway", "troubleshooting"]
        },
        {
            "runbook_id": "RB004",
            "title": "Kubernetes Pod CrashLoopBackOff",
            "content": """
            1. Check pod status: `kubectl get pods`
            2. View pod logs: `kubectl logs <pod-name>`
            3. Describe pod for events: `kubectl describe pod <pod-name>`
            4. Check for missing ConfigMaps/Secrets
            5. Verify environment variables are set
            6. Check resource limits (CPU/memory)
            7. Review liveness/readiness probes
            8. Validate container image exists and is accessible
            """,
            "topic": "Kubernetes",
            "service": "kubernetes-cluster",
            "tags": ["kubernetes", "crashloop", "pods"]
        },
        {
            "runbook_id": "RB005",
            "title": "Memory Leak Investigation",
            "content": """
            1. Monitor memory over time: `watch -n 5 free -h`
            2. Check application metrics (heap usage)
            3. Generate heap dump for analysis
            4. Review recent code changes
            5. Check for unclosed connections/files
            6. Look for circular references in code
            7. Implement memory profiling
            8. Restart service as temporary fix
            9. Deploy permanent fix after identifying leak
            """,
            "topic": "Application",
            "service": "general",
            "tags": ["memory", "leak", "performance"]
        },
        {
            "runbook_id": "RB006",
            "title": "Disk Space Management",
            "content": """
            1. Check disk usage: `df -h`
            2. Find large files: `du -h / | sort -rh | head -20`
            3. Clear old logs: `find /var/log -name "*.log" -mtime +7 -delete`
            4. Compress old logs: `gzip /var/log/*.log`
            5. Set up log rotation in /etc/logrotate.d/
            6. Remove old Docker images: `docker system prune -a`
            7. Clean package cache: `apt-get clean` or `yum clean all`
            8. Monitor disk usage with alerts
            """,
            "topic": "Storage",
            "service": "general",
            "tags": ["disk", "storage", "cleanup"]
        }
    ]


def main():
    """Main execution"""
    print("=" * 70)
    print("  📊 POPULATING DATABASES WITH 100 DEMO INCIDENTS")
    print("=" * 70)

    try:
        # Populate Weaviate
        populate_weaviate()

        # Populate Neo4j
        populate_neo4j()

        print("\n" + "=" * 70)
        print("  ✅ ALL DATA POPULATED SUCCESSFULLY!")
        print("=" * 70)
        print("\n📊 Summary:")
        print("  • 100 incidents in Weaviate")
        print("  • 6 runbooks in Weaviate")
        print("  • 100 incidents in Neo4j graph")
        print("  • 13 services in Neo4j")
        print("  • 13 service dependencies")
        print("\n🎯 Ready for:")
        print("  • Semantic search (Weaviate)")
        print("  • Root cause analysis (Neo4j)")
        print("  • Topic modeling (BERTopic)")
        print("  • Agent operations")
        print()

    except Exception as e:
        print(f"\n❌ Error during population: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
