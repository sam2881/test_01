#!/bin/bash
# Complete System Startup Script

set -e  # Exit on error

echo "================================================================================"
echo "🚀 AI Agent Platform - System Startup"
echo "================================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PROJECT_ROOT="/home/samrattidke600/ai_agent_app"
cd "$PROJECT_ROOT"

# Function to print step
print_step() {
    echo ""
    echo -e "${GREEN}▶ $1${NC}"
    echo "----------------------------------------"
}

# Function to check if service is up
wait_for_service() {
    local name=$1
    local check_cmd=$2
    local max_attempts=${3:-30}
    local attempt=1

    echo -n "Waiting for $name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if eval $check_cmd > /dev/null 2>&1; then
            echo -e " ${GREEN}✅${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e " ${RED}❌ Timeout${NC}"
    return 1
}

# Step 1: Check Docker
print_step "Step 1: Checking Docker"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker daemon not accessible. Trying with sudo...${NC}"
    DOCKER_CMD="sudo docker"
    DOCKER_COMPOSE_CMD="sudo docker-compose"
else
    DOCKER_CMD="docker"
    DOCKER_COMPOSE_CMD="docker-compose"
fi

echo "✅ Docker is available"

# Step 2: Start Infrastructure Services
print_step "Step 2: Starting Infrastructure (Weaviate, Neo4j, Kafka)"

cd "$PROJECT_ROOT/deployment"

if [ -f "docker-compose.yml" ]; then
    echo "Starting services with docker-compose..."
    $DOCKER_COMPOSE_CMD up -d weaviate neo4j kafka zookeeper 2>/dev/null || \
    $DOCKER_COMPOSE_CMD up -d weaviate neo4j 2>/dev/null || \
    echo "Some services may not be defined in docker-compose.yml"

    # Wait for services
    wait_for_service "Weaviate" "curl -s http://localhost:8081/v1/.well-known/ready" 30
    wait_for_service "Neo4j" "curl -s http://localhost:7474" 30
else
    echo -e "${YELLOW}⚠️  docker-compose.yml not found. Skipping Docker services.${NC}"
    echo "You can start services manually:"
    echo "  docker run -d -p 8081:8080 semitechnologies/weaviate:latest"
    echo "  docker run -d -p 7474:7474 -p 7687:7687 neo4j:latest"
fi

cd "$PROJECT_ROOT"

# Step 3: Index Scripts in Weaviate
print_step "Step 3: Indexing Scripts in Weaviate"

if curl -s http://localhost:8081/v1/.well-known/ready > /dev/null 2>&1; then
    echo "Running script indexer..."
    python3 backend/rag/script_library_indexer.py

    # Check if successful
    SCRIPT_COUNT=$(python3 -c "
import weaviate
try:
    c = weaviate.Client('http://localhost:8081')
    result = c.query.aggregate('InfrastructureScript').with_meta_count().do()
    count = result.get('data', {}).get('Aggregate', {}).get('InfrastructureScript', [{}])[0].get('meta', {}).get('count', 0)
    print(count)
except:
    print(0)
" 2>/dev/null)

    if [ "$SCRIPT_COUNT" -gt "0" ]; then
        echo -e "${GREEN}✅ Successfully indexed $SCRIPT_COUNT scripts${NC}"
    else
        echo -e "${RED}❌ Failed to index scripts${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Weaviate not accessible. Skipping indexing.${NC}"
fi

# Step 4: Start HITL API (in background)
print_step "Step 4: Starting HITL API"

# Check if already running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "HITL API already running on port 8000"
else
    echo "Starting HITL API in background..."
    cd "$PROJECT_ROOT/backend/orchestrator"

    # Start in background with nohup
    nohup python3 hitl_api.py > "$PROJECT_ROOT/logs/hitl_api.log" 2>&1 &
    HITL_PID=$!

    echo "HITL API started (PID: $HITL_PID)"
    echo "Log file: $PROJECT_ROOT/logs/hitl_api.log"

    # Wait for API to be ready
    wait_for_service "HITL API" "curl -s http://localhost:8000/health" 30

    cd "$PROJECT_ROOT"
fi

# Step 5: Start Infrastructure Agent (optional, in background)
print_step "Step 5: Starting Infrastructure Agent (Optional)"

if curl -s http://localhost:8013/health > /dev/null 2>&1; then
    echo "Infrastructure Agent already running on port 8013"
else
    echo "Starting Infrastructure Agent in background..."
    cd "$PROJECT_ROOT/backend/agents/infra"

    mkdir -p "$PROJECT_ROOT/logs"
    nohup python3 enhanced_agent.py > "$PROJECT_ROOT/logs/infra_agent.log" 2>&1 &
    AGENT_PID=$!

    echo "Infrastructure Agent started (PID: $AGENT_PID)"
    echo "Log file: $PROJECT_ROOT/logs/infra_agent.log"

    # Wait briefly
    sleep 5

    cd "$PROJECT_ROOT"
fi

# Step 6: Start Frontend (optional, in background)
print_step "Step 6: Starting Frontend (Optional)"

if curl -s http://localhost:3002 > /dev/null 2>&1; then
    echo "Frontend already running on port 3002"
else
    echo "Starting Frontend in background..."
    cd "$PROJECT_ROOT/frontend"

    if [ -d "node_modules" ]; then
        mkdir -p "$PROJECT_ROOT/logs"
        nohup npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
        FRONTEND_PID=$!

        echo "Frontend started (PID: $FRONTEND_PID)"
        echo "Log file: $PROJECT_ROOT/logs/frontend.log"

        # Wait briefly
        sleep 10
    else
        echo -e "${YELLOW}⚠️  node_modules not found. Run 'npm install' first.${NC}"
    fi

    cd "$PROJECT_ROOT"
fi

# Step 7: Final Health Check
print_step "Step 7: Final Health Check"

echo ""
bash "$PROJECT_ROOT/scripts/health_check.sh"

echo ""
echo "================================================================================"
echo "🎉 System Startup Complete!"
echo "================================================================================"
echo ""
echo "📋 Service URLs:"
echo "  • HITL API:       http://localhost:8000"
echo "  • Frontend UI:    http://localhost:3002/approvals"
echo "  • Weaviate:       http://localhost:8081"
echo "  • Neo4j:          http://localhost:7474"
echo ""
echo "📂 Log Files:"
echo "  • HITL API:       $PROJECT_ROOT/logs/hitl_api.log"
echo "  • Infra Agent:    $PROJECT_ROOT/logs/infra_agent.log"
echo "  • Frontend:       $PROJECT_ROOT/logs/frontend.log"
echo ""
echo "🧪 Ready for Testing:"
echo "  1. Test intelligent selection:"
echo "     python3 scripts/test_intelligent_selection.py"
echo ""
echo "  2. Test complete workflow:"
echo "     python3 scripts/test_complete_workflow.py"
echo ""
echo "  3. Open UI:"
echo "     http://localhost:3002/approvals"
echo ""
echo "⏹️  To stop all services:"
echo "     bash scripts/stop_system.sh"
echo ""
echo "================================================================================"
