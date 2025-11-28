#!/bin/bash
# Stop All Services Script

echo "================================================================================"
echo "⏹️  AI Agent Platform - Stopping Services"
echo "================================================================================"
echo ""

PROJECT_ROOT="/home/samrattidke600/ai_agent_app"

# Stop backend processes
echo "Stopping backend processes..."

# Find and kill HITL API
HITL_PID=$(ps aux | grep "hitl_api.py" | grep -v grep | awk '{print $2}')
if [ -n "$HITL_PID" ]; then
    kill $HITL_PID 2>/dev/null && echo "✅ Stopped HITL API (PID: $HITL_PID)" || echo "⚠️  Could not stop HITL API"
fi

# Find and kill Infrastructure Agent
AGENT_PID=$(ps aux | grep "enhanced_agent.py" | grep -v grep | awk '{print $2}')
if [ -n "$AGENT_PID" ]; then
    kill $AGENT_PID 2>/dev/null && echo "✅ Stopped Infrastructure Agent (PID: $AGENT_PID)" || echo "⚠️  Could not stop Agent"
fi

# Find and kill Frontend
FRONTEND_PID=$(lsof -ti:3002 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null && echo "✅ Stopped Frontend (PID: $FRONTEND_PID)" || echo "⚠️  Could not stop Frontend"
fi

echo ""

# Stop Docker containers
echo "Stopping Docker containers..."
cd "$PROJECT_ROOT/deployment"

if [ -f "docker-compose.yml" ]; then
    docker-compose down 2>/dev/null || sudo docker-compose down 2>/dev/null || echo "⚠️  Could not stop Docker containers"
    echo "✅ Docker containers stopped"
else
    echo "⚠️  docker-compose.yml not found"
fi

echo ""
echo "================================================================================"
echo "✅ All services stopped"
echo "================================================================================"
echo ""
echo "To start again: bash scripts/start_system.sh"
echo ""
