#!/bin/bash

#############################################
# AI Agent Platform v3.0 - Stop All Services
# Enterprise Incident Remediation Platform
#############################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_ROOT="/home/samrattidke600/ai_agent_app"
LOG_DIR="$PROJECT_ROOT/logs"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   AI Agent Platform v3.0 - Stopping All Services              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

#############################################
# Stop Frontend
#############################################
echo -e "${YELLOW}[1/5] Stopping Frontend...${NC}"
if [ -f "$LOG_DIR/frontend.pid" ]; then
    PID=$(cat "$LOG_DIR/frontend.pid")
    kill $PID 2>/dev/null && echo -e "${GREEN}   ✓ Frontend stopped (PID: $PID)${NC}" || true
    rm -f "$LOG_DIR/frontend.pid"
fi
fuser -k 3002/tcp 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
echo -e "${GREEN}   ✓ Frontend stopped${NC}"

#############################################
# Stop DSPy Service
#############################################
echo -e "${YELLOW}[2/5] Stopping DSPy Service...${NC}"
if [ -f "$LOG_DIR/dspy.pid" ]; then
    PID=$(cat "$LOG_DIR/dspy.pid")
    kill $PID 2>/dev/null && echo -e "${GREEN}   ✓ DSPy stopped (PID: $PID)${NC}" || true
    rm -f "$LOG_DIR/dspy.pid"
fi
pkill -f "python3 dspy_service/api.py" 2>/dev/null || true
fuser -k 8090/tcp 2>/dev/null || true
echo -e "${GREEN}   ✓ DSPy Service stopped${NC}"

#############################################
# Stop Kafka Consumer
#############################################
echo -e "${YELLOW}[3/5] Stopping Kafka Consumer...${NC}"
if [ -f "$LOG_DIR/consumer.pid" ]; then
    PID=$(cat "$LOG_DIR/consumer.pid")
    kill $PID 2>/dev/null && echo -e "${GREEN}   ✓ Consumer stopped (PID: $PID)${NC}" || true
    rm -f "$LOG_DIR/consumer.pid"
fi
pkill -f "python3 streaming/incident_consumer.py" 2>/dev/null || true
pkill -f "python3 streaming/servicenow_producer.py" 2>/dev/null || true
echo -e "${GREEN}   ✓ Kafka Consumer stopped${NC}"

#############################################
# Stop Backend API
#############################################
echo -e "${YELLOW}[4/5] Stopping Backend API...${NC}"
if [ -f "$LOG_DIR/backend.pid" ]; then
    PID=$(cat "$LOG_DIR/backend.pid")
    kill $PID 2>/dev/null && echo -e "${GREEN}   ✓ Backend stopped (PID: $PID)${NC}" || true
    rm -f "$LOG_DIR/backend.pid"
fi
pkill -f "python3 orchestrator/main.py" 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
echo -e "${GREEN}   ✓ Backend API stopped${NC}"

#############################################
# Docker Containers (optional)
#############################################
echo -e "${YELLOW}[5/5] Docker containers...${NC}"
echo -e "${CYAN}   Docker containers are kept running (Kafka, Neo4j, Redis, etc.)${NC}"
echo -e "${CYAN}   To stop Docker infrastructure:${NC}"
echo -e "${CYAN}     cd $PROJECT_ROOT/deployment && sudo docker compose down${NC}"
echo ""

# Show current Docker status
RUNNING=$(sudo docker compose -f "$PROJECT_ROOT/deployment/docker-compose.yml" ps --format '{{.Name}}' 2>/dev/null | wc -l)
echo -e "${CYAN}   Currently running containers: $RUNNING${NC}"

#############################################
# Summary
#############################################
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✓ All Application Services Stopped                          ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Verify all services are stopped
echo -e "${BLUE}Verification:${NC}"

# Check if port 8000 is in use
if ! fuser 8000/tcp &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Backend API (port 8000): ${GREEN}stopped${NC}"
else
    echo -e "  ${RED}✗${NC} Backend API (port 8000): ${RED}still running${NC}"
fi

# Check if port 3002 is in use
if ! fuser 3002/tcp &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Frontend (port 3002): ${GREEN}stopped${NC}"
else
    echo -e "  ${RED}✗${NC} Frontend (port 3002): ${RED}still running${NC}"
fi

# Check for remaining Python processes
REMAINING=$(pgrep -f "python3.*(orchestrator|streaming|dspy)" 2>/dev/null | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} Python services: ${GREEN}all stopped${NC}"
else
    echo -e "  ${YELLOW}⚠${NC} Python services: ${YELLOW}$REMAINING still running${NC}"
fi

echo ""
echo -e "${YELLOW}To restart services: ./start-all.sh${NC}"
echo ""
