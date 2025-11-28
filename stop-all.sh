#!/bin/bash

#############################################
# AI Agent Platform - Stop All Services
#############################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="/home/samrattidke600/ai_agent_app"
LOG_DIR="$PROJECT_ROOT/logs"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   AI Agent Platform - Stopping All Services    ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Stop Frontend
echo -e "${YELLOW}[1/5] Stopping Frontend...${NC}"
if [ -f "$LOG_DIR/frontend.pid" ]; then
    kill $(cat "$LOG_DIR/frontend.pid") 2>/dev/null || true
    rm "$LOG_DIR/frontend.pid"
fi
fuser -k 3002/tcp 2>/dev/null || true
echo -e "${GREEN}   Frontend stopped${NC}"

# Stop MCP Gateway
echo -e "${YELLOW}[2/5] Stopping MCP Gateway...${NC}"
if [ -f "$LOG_DIR/mcp_gateway.pid" ]; then
    kill $(cat "$LOG_DIR/mcp_gateway.pid") 2>/dev/null || true
    rm "$LOG_DIR/mcp_gateway.pid"
fi
pkill -f "python3 mcp_gateway/http_server.py" 2>/dev/null || true
fuser -k 8001/tcp 2>/dev/null || true
echo -e "${GREEN}   MCP Gateway stopped${NC}"

# Stop Kafka Consumer
echo -e "${YELLOW}[3/5] Stopping Kafka Consumer...${NC}"
if [ -f "$LOG_DIR/consumer.pid" ]; then
    kill $(cat "$LOG_DIR/consumer.pid") 2>/dev/null || true
    rm "$LOG_DIR/consumer.pid"
fi
pkill -f "python3 streaming/incident_consumer.py" 2>/dev/null || true
echo -e "${GREEN}   Kafka Consumer stopped${NC}"

# Stop Backend
echo -e "${YELLOW}[4/5] Stopping Backend API...${NC}"
if [ -f "$LOG_DIR/backend.pid" ]; then
    kill $(cat "$LOG_DIR/backend.pid") 2>/dev/null || true
    rm "$LOG_DIR/backend.pid"
fi
pkill -f "python3 orchestrator/main.py" 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
echo -e "${GREEN}   Backend API stopped${NC}"

# Stop Docker (optional - uncomment if you want to stop containers)
echo -e "${YELLOW}[5/5] Docker containers...${NC}"
echo -e "${YELLOW}   Keeping Docker containers running (Kafka, DBs)${NC}"
echo -e "${YELLOW}   To stop Docker: cd deployment && sudo docker compose down${NC}"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   All Application Services Stopped             ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
