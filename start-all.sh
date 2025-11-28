#!/bin/bash

#############################################
# AI Agent Platform - Start All Services
# Enterprise Incident Remediation Platform
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="/home/samrattidke600/ai_agent_app"

# Log file
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   AI Agent Platform - Starting All Services    ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

#############################################
# Environment Variables
#############################################
echo -e "${YELLOW}[1/7] Setting environment variables...${NC}"

export KAFKA_BOOTSTRAP_SERVERS=localhost:29092
export SNOW_INSTANCE_URL="https://dev275804.service-now.com"
export SNOW_USERNAME="admin"
export SNOW_PASSWORD='YdZ3Y/n1Zlh*'
export OPENAI_API_KEY="${OPENAI_API_KEY:-your-openai-key}"
export GOOGLE_APPLICATION_CREDENTIALS="/home/samrattidke600/ai_agent_app/gcp-service-account-key.json"
export GITHUB_TOKEN="${GITHUB_TOKEN:-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}"
export NEO4J_PASSWORD="adminadmin"
export USE_ENTERPRISE_MATCHER=true

echo -e "${GREEN}   Environment variables set${NC}"

#############################################
# Kill existing processes
#############################################
echo -e "${YELLOW}[2/7] Stopping any existing processes...${NC}"

# Kill existing Python processes for our app
pkill -f "python3 orchestrator/main.py" 2>/dev/null || true
pkill -f "python3 streaming/incident_consumer.py" 2>/dev/null || true
pkill -f "python3 mcp_gateway/http_server.py" 2>/dev/null || true

# Kill existing frontend on port 3002
fuser -k 3002/tcp 2>/dev/null || true
fuser -k 8001/tcp 2>/dev/null || true

sleep 2
echo -e "${GREEN}   Existing processes stopped${NC}"

#############################################
# Start Docker Infrastructure
#############################################
echo -e "${YELLOW}[3/7] Starting Docker infrastructure...${NC}"

cd "$PROJECT_ROOT/deployment"

# Check if containers are already running
if sudo docker compose ps | grep -q "Up"; then
    echo -e "${GREEN}   Docker containers already running${NC}"
else
    sudo docker compose up -d
    echo -e "${GREEN}   Docker containers started${NC}"
fi

# Wait for services to be ready
echo -e "${YELLOW}   Waiting for services to be ready...${NC}"
sleep 10

# Check Kafka is ready
for i in {1..30}; do
    if sudo docker exec deployment-kafka-1 kafka-topics --list --bootstrap-server localhost:9092 &>/dev/null; then
        echo -e "${GREEN}   Kafka is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}   Kafka failed to start${NC}"
        exit 1
    fi
    sleep 2
done

#############################################
# Start Backend API
#############################################
echo -e "${YELLOW}[4/7] Starting Backend API server...${NC}"

cd "$PROJECT_ROOT/backend"

# Start backend in background
nohup python3 orchestrator/main.py > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"

# Wait for backend to be ready
for i in {1..30}; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        echo -e "${GREEN}   Backend API started (PID: $BACKEND_PID)${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}   Backend API failed to start. Check $LOG_DIR/backend.log${NC}"
        exit 1
    fi
    sleep 2
done

#############################################
# Start Kafka Consumer
#############################################
echo -e "${YELLOW}[5/7] Starting Kafka Consumer...${NC}"

cd "$PROJECT_ROOT/backend"

# Start consumer in background
nohup python3 streaming/incident_consumer.py > "$LOG_DIR/consumer.log" 2>&1 &
CONSUMER_PID=$!
echo $CONSUMER_PID > "$LOG_DIR/consumer.pid"

sleep 3
if ps -p $CONSUMER_PID > /dev/null; then
    echo -e "${GREEN}   Kafka Consumer started (PID: $CONSUMER_PID)${NC}"
else
    echo -e "${RED}   Kafka Consumer failed to start. Check $LOG_DIR/consumer.log${NC}"
fi

#############################################
# Start MCP HTTP Gateway
#############################################
echo -e "${YELLOW}[6/7] Starting MCP HTTP Gateway...${NC}"

cd "$PROJECT_ROOT/backend"

# Start MCP Gateway in background
nohup python3 mcp_gateway/http_server.py > "$LOG_DIR/mcp_gateway.log" 2>&1 &
MCP_PID=$!
echo $MCP_PID > "$LOG_DIR/mcp_gateway.pid"

# Wait for MCP Gateway to be ready
for i in {1..15}; do
    if curl -s http://localhost:8001/health &>/dev/null; then
        echo -e "${GREEN}   MCP Gateway started (PID: $MCP_PID)${NC}"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${YELLOW}   MCP Gateway still starting... Check $LOG_DIR/mcp_gateway.log${NC}"
    fi
    sleep 1
done

#############################################
# Start Frontend
#############################################
echo -e "${YELLOW}[7/7] Starting Frontend...${NC}"

cd "$PROJECT_ROOT/frontend"

# Start frontend in background
nohup npm run start > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"

# Wait for frontend to be ready
for i in {1..60}; do
    if curl -s http://localhost:3002 &>/dev/null; then
        echo -e "${GREEN}   Frontend started (PID: $FRONTEND_PID)${NC}"
        break
    fi
    if [ $i -eq 60 ]; then
        echo -e "${YELLOW}   Frontend is still starting... Check $LOG_DIR/frontend.log${NC}"
    fi
    sleep 2
done

#############################################
# Summary
#############################################
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}   All Services Started Successfully!           ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo -e "  Frontend Dashboard:  ${GREEN}http://localhost:3002${NC}"
echo -e "  Backend API:         ${GREEN}http://localhost:8000${NC}"
echo -e "  MCP Gateway:         ${GREEN}http://localhost:8001${NC}"
echo -e "  API Documentation:   ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  MCP API Docs:        ${GREEN}http://localhost:8001/docs${NC}"
echo -e "  Kafka UI:            ${GREEN}http://localhost:8085${NC}"
echo -e "  Grafana:             ${GREEN}http://localhost:3000${NC}"
echo -e "  Neo4j Browser:       ${GREEN}http://localhost:7474${NC}"
echo ""
echo -e "${BLUE}MCP Servers (via HTTP Gateway):${NC}"
echo -e "  ServiceNow MCP:      ${GREEN}http://localhost:8001/api/mcp/servicenow${NC}"
echo -e "  GCP MCP:             ${GREEN}http://localhost:8001/api/mcp/gcp${NC}"
echo -e "  GitHub MCP:          ${GREEN}http://localhost:8001/api/mcp/github${NC}"
echo -e "  Jira MCP:            ${GREEN}http://localhost:8001/api/mcp/jira${NC}"
echo ""
echo -e "${BLUE}Log Files:${NC}"
echo -e "  Backend:     $LOG_DIR/backend.log"
echo -e "  Consumer:    $LOG_DIR/consumer.log"
echo -e "  MCP Gateway: $LOG_DIR/mcp_gateway.log"
echo -e "  Frontend:    $LOG_DIR/frontend.log"
echo ""
echo -e "${BLUE}Process IDs:${NC}"
echo -e "  Backend:     $(cat $LOG_DIR/backend.pid 2>/dev/null || echo 'N/A')"
echo -e "  Consumer:    $(cat $LOG_DIR/consumer.pid 2>/dev/null || echo 'N/A')"
echo -e "  MCP Gateway: $(cat $LOG_DIR/mcp_gateway.pid 2>/dev/null || echo 'N/A')"
echo -e "  Frontend:    $(cat $LOG_DIR/frontend.pid 2>/dev/null || echo 'N/A')"
echo ""
echo -e "${YELLOW}To stop all services, run: ./stop-all.sh${NC}"
echo ""
