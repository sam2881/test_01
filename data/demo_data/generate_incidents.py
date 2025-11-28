#!/usr/bin/env python3
"""Generate 100 realistic demo incidents for ServiceNow"""
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict

# Realistic incident categories and patterns
SERVICES = [
    "api-gateway", "web-server", "database", "cache-redis", "message-queue",
    "auth-service", "payment-service", "user-service", "email-service",
    "storage-service", "cdn", "load-balancer", "kubernetes-cluster"
]

INCIDENT_PATTERNS = [
    {
        "title": "High CPU utilization on {service}",
        "description": "CPU usage has exceeded 85% threshold on {service} in {zone}. Multiple users reporting slow response times.",
        "category": "Performance",
        "severity": ["P2", "P1"],
        "resolution": "Scaled up instance from n1-standard-2 to n1-standard-4. Added horizontal pod autoscaler. CPU normalized to 45%."
    },
    {
        "title": "Database connection pool exhausted on {service}",
        "description": "Connection pool reached maximum limit of 100 connections. New connection requests timing out after 30 seconds.",
        "category": "Database",
        "severity": ["P1", "P2"],
        "resolution": "Increased max_connections from 100 to 200. Implemented connection pooling with PgBouncer. Added connection timeout monitoring."
    },
    {
        "title": "Memory leak detected in {service}",
        "description": "Memory usage increasing steadily over 24 hours from 2GB to 7GB. Application not releasing memory after processing requests.",
        "category": "Application",
        "severity": ["P2", "P3"],
        "resolution": "Identified memory leak in background job processor. Fixed unclosed database cursors. Deployed patch v2.3.1. Memory usage stable at 2.5GB."
    },
    {
        "title": "API Gateway returning 502 Bad Gateway errors",
        "description": "Users experiencing intermittent 502 errors when accessing {service}. Error rate at 15% of total requests.",
        "category": "Infrastructure",
        "severity": ["P1"],
        "resolution": "Restarted nginx workers. Increased upstream timeout from 30s to 60s. Cleared connection pool. Error rate dropped to 0.1%."
    },
    {
        "title": "Disk space running low on {service}",
        "description": "Available disk space below 15% on {service}. Log files consuming 80GB of 100GB total capacity.",
        "category": "Storage",
        "severity": ["P2", "P3"],
        "resolution": "Implemented log rotation policy (7 days retention). Compressed old logs. Freed up 60GB. Set up automated cleanup job."
    },
    {
        "title": "SSL certificate expiring in 7 days for {service}",
        "description": "SSL certificate for {service}.example.com expires on {date}. HTTPS connections will fail after expiration.",
        "category": "Security",
        "severity": ["P2"],
        "resolution": "Renewed SSL certificate using Let's Encrypt. Updated cert-manager configuration. Set up automated renewal 30 days before expiry."
    },
    {
        "title": "Redis cache cluster node failure",
        "description": "One of three Redis nodes in {zone} cluster failed. Cluster operating in degraded mode with reduced redundancy.",
        "category": "Infrastructure",
        "severity": ["P1", "P2"],
        "resolution": "Replaced failed node. Rebalanced cluster slots. Verified data replication. All three nodes operational."
    },
    {
        "title": "Kubernetes pod crash loop on {service}",
        "description": "Pod {service}-deployment-abc123 restarting continuously. CrashLoopBackOff state with 10 restarts in 5 minutes.",
        "category": "Kubernetes",
        "severity": ["P1"],
        "resolution": "Identified missing environment variable DATABASE_URL. Added secret to deployment. Pod stable with 0 restarts."
    },
    {
        "title": "Slow query performance on {service} database",
        "description": "Query execution time increased from 200ms to 8 seconds. Affecting user dashboard load times.",
        "category": "Database",
        "severity": ["P2"],
        "resolution": "Created missing index on user_id column. Optimized JOIN operation. Query time reduced to 150ms. Added query performance monitoring."
    },
    {
        "title": "Network latency spike between {service} and database",
        "description": "Network latency increased from 5ms to 150ms. Affecting all database operations.",
        "category": "Network",
        "severity": ["P1", "P2"],
        "resolution": "Identified network congestion on default VPC. Migrated to dedicated VPC with higher bandwidth. Latency normalized to 3ms."
    },
    {
        "title": "Authentication service token validation failing",
        "description": "JWT token validation failing with 'Invalid signature' error. Users unable to access protected resources.",
        "category": "Security",
        "severity": ["P1"],
        "resolution": "Rotated signing keys in auth service. Updated all microservices with new public key. Token validation working normally."
    },
    {
        "title": "Message queue (Kafka) consumer lag increasing",
        "description": "Consumer lag on 'orders' topic increased to 50,000 messages. Processing delayed by 30 minutes.",
        "category": "Messaging",
        "severity": ["P2"],
        "resolution": "Increased consumer instances from 3 to 6. Optimized message processing code. Lag cleared in 15 minutes."
    },
    {
        "title": "CDN cache hit rate dropped below 60%",
        "description": "Cache hit rate decreased from 85% to 55%. Increased load on origin servers.",
        "category": "CDN",
        "severity": ["P3"],
        "resolution": "Updated cache-control headers. Increased TTL from 1 hour to 4 hours for static assets. Hit rate improved to 82%."
    },
    {
        "title": "Background job queue backlog on {service}",
        "description": "Job queue backlog reached 10,000 jobs. Processing time exceeding SLA by 2 hours.",
        "category": "Application",
        "severity": ["P2"],
        "resolution": "Scaled worker nodes from 5 to 15. Optimized job processing logic. Backlog cleared in 45 minutes."
    },
    {
        "title": "Service mesh (Istio) sidecar injection failing",
        "description": "New pod deployments failing because Istio sidecar not injecting. Services not joining mesh.",
        "category": "Kubernetes",
        "severity": ["P2"],
        "resolution": "Restarted Istio control plane pods. Verified webhook configuration. Sidecar injection working on new deployments."
    }
]

ZONES = ["us-central1-a", "us-east1-b", "us-west1-a", "europe-west1-b", "asia-southeast1-a"]

def generate_incident(index: int) -> Dict:
    """Generate a single realistic incident"""
    pattern = random.choice(INCIDENT_PATTERNS)
    service = random.choice(SERVICES)
    zone = random.choice(ZONES)
    severity = random.choice(pattern["severity"])

    # Generate timestamps
    days_ago = random.randint(1, 90)
    created_date = datetime.now() - timedelta(days=days_ago)
    resolved_date = created_date + timedelta(hours=random.randint(1, 24))

    incident = {
        "incident_id": f"INC{str(index).zfill(6)}",
        "number": f"INC{str(index).zfill(6)}",
        "title": pattern["title"].format(service=service),
        "short_description": pattern["title"].format(service=service),
        "description": pattern["description"].format(
            service=service,
            zone=zone,
            date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        ),
        "category": pattern["category"],
        "severity": severity,
        "priority": severity,
        "state": "Resolved",
        "service": service,
        "zone": zone,
        "resolution": pattern["resolution"],
        "resolution_notes": pattern["resolution"],
        "assigned_to": random.choice([
            "John Smith", "Sarah Johnson", "Mike Chen", "Emily Davis",
            "David Wilson", "Lisa Anderson", "James Brown", "Maria Garcia"
        ]),
        "created_at": created_date.isoformat(),
        "resolved_at": resolved_date.isoformat(),
        "impact": random.choice(["High", "Medium", "Low"]),
        "urgency": random.choice(["High", "Medium", "Low"]),
        "tags": [pattern["category"].lower(), service, severity.lower()],
        "affected_users": random.randint(10, 5000),
        "downtime_minutes": random.randint(0, 240) if severity == "P1" else random.randint(0, 60)
    }

    return incident

def generate_all_incidents(count: int = 100) -> List[Dict]:
    """Generate all demo incidents"""
    incidents = []
    for i in range(1, count + 1):
        incident = generate_incident(i)
        incidents.append(incident)
    return incidents

if __name__ == "__main__":
    incidents = generate_all_incidents(100)

    # Save to JSON file
    output_file = "/home/samrattidke600/ai_agent_app/data/demo_data/incidents_100.json"
    with open(output_file, 'w') as f:
        json.dump(incidents, f, indent=2)

    print(f"✓ Generated 100 demo incidents")
    print(f"✓ Saved to: {output_file}")

    # Print statistics
    severities = {}
    categories = {}
    for inc in incidents:
        severities[inc['severity']] = severities.get(inc['severity'], 0) + 1
        categories[inc['category']] = categories.get(inc['category'], 0) + 1

    print(f"\nStatistics:")
    print(f"  Severities: {severities}")
    print(f"  Categories: {categories}")
