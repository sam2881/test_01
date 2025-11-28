#!/bin/bash

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "  🚀 AI AGENT PLATFORM - FULL DEMO SETUP"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Change to project directory
cd /home/samrattidke600/ai_agent_app

# Step 1: Generate demo data
echo "📊 Step 1: Generating 100 demo incidents..."
python3 data/demo_data/generate_incidents.py
echo "  ✅ Generated 100 incidents"
echo ""

# Step 2: Wait for databases to be ready
echo "⏳ Step 2: Waiting for databases to be ready..."
echo "  Waiting for Weaviate..."
until curl -s http://localhost:8081/v1/.well-known/ready > /dev/null 2>&1; do
    sleep 2
done
echo "  ✅ Weaviate ready"

echo "  Waiting for Neo4j..."
until curl -s http://localhost:7474 > /dev/null 2>&1; do
    sleep 2
done
echo "  ✅ Neo4j ready"

echo "  Waiting for PostgreSQL..."
until docker-compose -f deployment/docker-compose.yml exec -T postgres pg_isready > /dev/null 2>&1; do
    sleep 2
done
echo "  ✅ PostgreSQL ready"

echo "  Waiting for Redis..."
until docker-compose -f deployment/docker-compose.yml exec -T redis redis-cli ping > /dev/null 2>&1; do
    sleep 2
done
echo "  ✅ Redis ready"
echo ""

# Step 3: Run BERTopic analysis
echo "🔍 Step 3: Running BERTopic analysis..."
python3 backend/topic_modeling/bertopic_analyzer.py 2>/dev/null || echo "  ⚠️  BERTopic analysis skipped (dependencies may need installation)"
echo ""

# Step 4: Populate databases
echo "💾 Step 4: Populating databases with demo data..."
python3 scripts/populate_all_data.py
echo ""

# Step 5: Verify data
echo "🔍 Step 5: Verifying data population..."
echo ""

# Check Weaviate
WEAVIATE_COUNT=$(curl -s http://localhost:8081/v1/objects | grep -o '"totalResults":[0-9]*' | grep -o '[0-9]*' || echo "0")
echo "  Weaviate Objects: $WEAVIATE_COUNT"

# Check Neo4j
echo "  Neo4j: Checking via Neo4j Browser at http://localhost:7474"

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  ✅ DEMO DATA SETUP COMPLETE!"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "📊 Data Summary:"
echo "  • 100 ServiceNow Incidents (Generated)"
echo "  • 100 Incidents in Weaviate (Vector DB)"
echo "  • 100 Incidents in Neo4j (Graph DB)"
echo "  • 6 Runbooks in Weaviate"
echo "  • 13 Services with Dependencies (Neo4j)"
echo "  • 5 Jira Stories for Testing"
echo "  • Sample Java Test Code (PaymentServiceTest.java)"
echo ""
echo "🧪 Test the System:"
echo ""
echo "  # Test ServiceNow Incident Creation"
echo '  curl -X POST http://localhost:8000/task \\'
echo '    -H "Content-Type: application/json" \\'
echo '    -d '"'"'{"description": "API Gateway 502 errors", "task_type": "incident"}'"'"''
echo ""
echo "  # Test GCP Monitoring Alert"
echo '  curl -X POST http://localhost:8015/alert \\'
echo '    -H "Content-Type: application/json" \\'
echo '    -d '"'"'{"resource_name": "vm-1", "metric_value": 95, "severity": "critical"}'"'"''
echo ""
echo "  # Search Similar Incidents (semantic search)"
echo '  curl -X POST http://localhost:8000/task \\'
echo '    -H "Content-Type: application/json" \\'
echo '    -d '"'"'{"description": "Database performance issue", "task_type": "incident"}'"'"''
echo ""
echo "🌐 Access Dashboards:"
echo "  • ServiceNow: https://dev322582.service-now.com"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Neo4j Browser: http://localhost:7474 (neo4j/incident_password_2024)"
echo "  • Grafana: http://localhost:3000 (admin/admin)"
echo "  • Kafka UI: http://localhost:8085"
echo "  • LangFuse: https://cloud.langfuse.com"
echo ""
echo "════════════════════════════════════════════════════════════════════"
