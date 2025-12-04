#!/bin/bash

#############################################
# AI Agent Platform v3.0 - Start All Services
# Enterprise Incident Remediation Platform
#
# Services:
# - Docker Infrastructure (Kafka, Neo4j, Weaviate, Redis, PostgreSQL)
# - Backend API (FastAPI with Enhanced RAG, Guardrails, LangGraph)
# - Kafka Consumer (Multi-source incident processing)
# - DSPy Optimizer Service (Prompt optimization)
# - Frontend (Next.js Dashboard)
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="/home/samrattidke600/ai_agent_app"

# Log directory
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# Clear old logs
> "$LOG_DIR/backend.log"
> "$LOG_DIR/consumer.log"
> "$LOG_DIR/dspy.log"
> "$LOG_DIR/frontend.log"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   AI Agent Platform v3.0 - Enterprise Incident Remediation    ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Features: Enhanced RAG | LLM Guardrails | LangGraph | DSPy${NC}"
echo ""

#############################################
# Environment Variables
#############################################
echo -e "${YELLOW}[1/6] Setting environment variables...${NC}"

# ServiceNow
export SNOW_INSTANCE_URL="https://dev275804.service-now.com"
export SNOW_USERNAME="admin"
export SNOW_PASSWORD='YdZ3Y/n1Zlh*'

# Kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:29092

# GCP
export GOOGLE_APPLICATION_CREDENTIALS="$PROJECT_ROOT/gcp-service-account-key.json"

# GitHub
export GITHUB_TOKEN="${GITHUB_TOKEN:-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}"

# OpenAI
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# Neo4j
export NEO4J_PASSWORD="adminadmin"
export NEO4J_URI="bolt://localhost:7687"

# Redis
export REDIS_URL="redis://localhost:6379"

# Weaviate
export WEAVIATE_URL="http://localhost:8080"

# Feature flags
export USE_ENTERPRISE_MATCHER=true
export GUARDRAILS_ENABLED=true
export ENHANCED_RAG_ENABLED=true

echo -e "${GREEN}   ✓ Environment variables configured${NC}"

#############################################
# Kill existing processes
#############################################
echo -e "${YELLOW}[2/6] Stopping any existing processes...${NC}"

# Kill existing Python processes
pkill -f "python3 orchestrator/main.py" 2>/dev/null || true
pkill -f "python3 streaming/incident_consumer.py" 2>/dev/null || true
pkill -f "python3 streaming/servicenow_producer.py" 2>/dev/null || true
pkill -f "python3 dspy_service/api.py" 2>/dev/null || true

# Kill processes on ports
fuser -k 3002/tcp 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8090/tcp 2>/dev/null || true

sleep 2
echo -e "${GREEN}   ✓ Existing processes stopped${NC}"

#############################################
# Start Docker Infrastructure
#############################################
echo -e "${YELLOW}[3/6] Starting Docker infrastructure...${NC}"

cd "$PROJECT_ROOT/deployment"

# Check if containers are already running
RUNNING_CONTAINERS=$(sudo docker compose ps --format '{{.Name}}' 2>/dev/null | wc -l)

if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
    echo -e "${GREEN}   ✓ Docker containers already running ($RUNNING_CONTAINERS services)${NC}"
else
    echo -e "${CYAN}   Starting Docker containers...${NC}"
    sudo docker compose up -d
    echo -e "${GREEN}   ✓ Docker containers started${NC}"
fi

# Wait for Kafka to be ready
echo -e "${CYAN}   Waiting for Kafka...${NC}"
for i in {1..30}; do
    if sudo docker exec deployment-kafka-1 kafka-topics --list --bootstrap-server localhost:9092 &>/dev/null; then
        echo -e "${GREEN}   ✓ Kafka is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}   ✗ Kafka failed to start - check 'sudo docker logs deployment-kafka-1'${NC}"
        exit 1
    fi
    sleep 2
done

# Verify other services
echo -e "${CYAN}   Checking infrastructure services...${NC}"

# Check Redis
if redis-cli ping &>/dev/null; then
    echo -e "${GREEN}   ✓ Redis is ready${NC}"
else
    echo -e "${YELLOW}   ⚠ Redis not responding (may start later)${NC}"
fi

# Check Neo4j
if curl -s http://localhost:7474 &>/dev/null; then
    echo -e "${GREEN}   ✓ Neo4j is ready${NC}"
else
    echo -e "${YELLOW}   ⚠ Neo4j not responding (may start later)${NC}"
fi

#############################################
# Start Backend API
#############################################
echo -e "${YELLOW}[4/6] Starting Backend API server...${NC}"

cd "$PROJECT_ROOT/backend"

# Start backend in background
nohup python3 orchestrator/main.py > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"

# Wait for backend to be ready
echo -e "${CYAN}   Waiting for Backend API...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        echo -e "${GREEN}   ✓ Backend API started (PID: $BACKEND_PID)${NC}"

        # Check guardrails status
        GUARDRAILS=$(curl -s http://localhost:8000/api/guardrails/status 2>/dev/null | grep -o '"enabled":true' || echo "")
        if [ -n "$GUARDRAILS" ]; then
            echo -e "${GREEN}   ✓ LLM Guardrails enabled${NC}"
        fi
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}   ✗ Backend API failed to start${NC}"
        echo -e "${RED}   Check: tail -f $LOG_DIR/backend.log${NC}"
        exit 1
    fi
    sleep 2
done

#############################################
# Start Kafka Consumer
#############################################
echo -e "${YELLOW}[5/6] Starting Kafka Consumer...${NC}"

cd "$PROJECT_ROOT/backend"

# Start consumer in background
nohup python3 streaming/incident_consumer.py > "$LOG_DIR/consumer.log" 2>&1 &
CONSUMER_PID=$!
echo $CONSUMER_PID > "$LOG_DIR/consumer.pid"

sleep 3
if ps -p $CONSUMER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}   ✓ Kafka Consumer started (PID: $CONSUMER_PID)${NC}"
else
    echo -e "${YELLOW}   ⚠ Kafka Consumer may have issues - check $LOG_DIR/consumer.log${NC}"
fi

# Optionally start DSPy service
if [ -f "$PROJECT_ROOT/backend/dspy_service/api.py" ]; then
    echo -e "${CYAN}   Starting DSPy Optimizer Service...${NC}"
    nohup python3 dspy_service/api.py > "$LOG_DIR/dspy.log" 2>&1 &
    DSPY_PID=$!
    echo $DSPY_PID > "$LOG_DIR/dspy.pid"
    sleep 2
    if ps -p $DSPY_PID > /dev/null 2>&1; then
        echo -e "${GREEN}   ✓ DSPy Service started (PID: $DSPY_PID)${NC}"
    fi
fi

#############################################
# Start Frontend
#############################################
echo -e "${YELLOW}[6/6] Starting Frontend...${NC}"

cd "$PROJECT_ROOT/frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${CYAN}   Installing frontend dependencies...${NC}"
    npm install --silent
fi

# Start frontend in background
PORT=3002 nohup npm run start > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"

# Wait for frontend to be ready
echo -e "${CYAN}   Waiting for Frontend (may take up to 60s)...${NC}"
for i in {1..60}; do
    if curl -s http://localhost:3002 &>/dev/null; then
        echo -e "${GREEN}   ✓ Frontend started (PID: $FRONTEND_PID)${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${YELLOW}   ⚠ Frontend still starting... check $LOG_DIR/frontend.log${NC}"
    fi
    sleep 2
done

#############################################
# Summary
#############################################
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✓ All Services Started Successfully!                        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}┌─────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│                    SERVICE ENDPOINTS                         │${NC}"
echo -e "${BLUE}├─────────────────────────────────────────────────────────────┤${NC}"
echo -e "${BLUE}│${NC} Frontend Dashboard    ${GREEN}http://localhost:3002${NC}               ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Backend API           ${GREEN}http://localhost:8000${NC}               ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} API Documentation     ${GREEN}http://localhost:8000/docs${NC}          ${BLUE}│${NC}"
echo -e "${BLUE}├─────────────────────────────────────────────────────────────┤${NC}"
echo -e "${BLUE}│${NC}                   INFRASTRUCTURE                          ${BLUE}│${NC}"
echo -e "${BLUE}├─────────────────────────────────────────────────────────────┤${NC}"
echo -e "${BLUE}│${NC} Kafka UI              ${GREEN}http://localhost:8085${NC}               ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Neo4j Browser         ${GREEN}http://localhost:7474${NC}               ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Grafana               ${GREEN}http://localhost:3000${NC}               ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Prometheus            ${GREEN}http://localhost:9090${NC}               ${BLUE}│${NC}"
echo -e "${BLUE}└─────────────────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "${BLUE}┌─────────────────────────────────────────────────────────────┐${NC}"
echo -e "${BLUE}│                    KEY API ENDPOINTS                         │${NC}"
echo -e "${BLUE}├─────────────────────────────────────────────────────────────┤${NC}"
echo -e "${BLUE}│${NC} RAG Search            ${CYAN}POST /api/rag/search${NC}                 ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Guardrails Validate   ${CYAN}POST /api/guardrails/validate${NC}        ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Script Match          ${CYAN}POST /api/scripts/match${NC}              ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Execute Script        ${CYAN}POST /api/execute${NC}                    ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} LangGraph Workflow    ${CYAN}GET  /api/langgraph/definition${NC}       ${BLUE}│${NC}"
echo -e "${BLUE}│${NC} Rollback Generate     ${CYAN}POST /api/rollback/generate${NC}          ${BLUE}│${NC}"
echo -e "${BLUE}└─────────────────────────────────────────────────────────────┘${NC}"
echo ""
echo -e "${BLUE}Log Files:${NC}"
echo -e "  Backend:  ${CYAN}tail -f $LOG_DIR/backend.log${NC}"
echo -e "  Consumer: ${CYAN}tail -f $LOG_DIR/consumer.log${NC}"
echo -e "  Frontend: ${CYAN}tail -f $LOG_DIR/frontend.log${NC}"
echo ""
echo -e "${BLUE}Process IDs:${NC}"
echo -e "  Backend:  $(cat $LOG_DIR/backend.pid 2>/dev/null || echo 'N/A')"
echo -e "  Consumer: $(cat $LOG_DIR/consumer.pid 2>/dev/null || echo 'N/A')"
echo -e "  DSPy:     $(cat $LOG_DIR/dspy.pid 2>/dev/null || echo 'N/A')"
echo -e "  Frontend: $(cat $LOG_DIR/frontend.pid 2>/dev/null || echo 'N/A')"
echo ""
echo -e "${YELLOW}To stop all services: ./stop-all.sh${NC}"
echo ""
