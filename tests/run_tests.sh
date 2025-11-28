#!/bin/bash

# Test execution script for AI Agent Platform
# Usage: ./run_tests.sh [category] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════╗"
echo "║     AI Agent Platform - Test Suite Runner           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Default options
CATEGORY="${1:-all}"
COVERAGE="${2:-false}"
PARALLEL="${3:-false}"

# Function to run tests
run_tests() {
    local category=$1
    local description=$2
    local marker=$3
    local path=$4

    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running: $description${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    if [ "$PARALLEL" = "true" ]; then
        PYTEST_CMD="pytest $path -v -n auto"
    else
        PYTEST_CMD="pytest $path -v"
    fi

    if [ -n "$marker" ]; then
        PYTEST_CMD="$PYTEST_CMD -m $marker"
    fi

    if [ "$COVERAGE" = "true" ]; then
        PYTEST_CMD="$PYTEST_CMD --cov=backend --cov-report=term-missing"
    fi

    if $PYTEST_CMD; then
        echo -e "\n${GREEN}✓ $description PASSED${NC}"
        return 0
    else
        echo -e "\n${RED}✗ $description FAILED${NC}"
        return 1
    fi
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install with: pip install -r tests/requirements-test.txt"
    exit 1
fi

# Main test execution
case $CATEGORY in
    smoke)
        echo -e "${YELLOW}Running SMOKE tests (quick sanity check)...${NC}"
        run_tests "smoke" "Smoke Tests" "smoke" "tests/smoke/"
        ;;

    unit)
        echo -e "${YELLOW}Running UNIT tests...${NC}"
        run_tests "unit" "Unit Tests" "unit" "tests/unit/"
        ;;

    integration)
        echo -e "${YELLOW}Running INTEGRATION tests...${NC}"
        run_tests "integration" "Integration Tests" "integration" "tests/integration/"
        ;;

    e2e)
        echo -e "${YELLOW}Running E2E tests...${NC}"
        run_tests "e2e" "End-to-End Tests" "e2e" "tests/e2e/"
        ;;

    performance)
        echo -e "${YELLOW}Running PERFORMANCE tests...${NC}"
        run_tests "performance" "Performance Tests" "performance" "tests/performance/"
        ;;

    security)
        echo -e "${YELLOW}Running SECURITY tests...${NC}"
        run_tests "security" "Security Tests" "security" "tests/security/"
        ;;

    llm)
        echo -e "${YELLOW}Running LLM tests (prompts, hallucination, adversarial, bias)...${NC}"
        run_tests "llm" "LLM Tests" "llm" "tests/llm/"
        ;;

    regression)
        echo -e "${YELLOW}Running REGRESSION tests...${NC}"
        run_tests "regression" "Regression Tests" "regression" "tests/regression/"
        ;;

    fast)
        echo -e "${YELLOW}Running FAST tests (unit + smoke)...${NC}"
        run_tests "unit" "Unit Tests" "unit" "tests/unit/"
        run_tests "smoke" "Smoke Tests" "smoke" "tests/smoke/"
        ;;

    critical)
        echo -e "${YELLOW}Running CRITICAL tests (smoke + integration)...${NC}"
        run_tests "smoke" "Smoke Tests" "smoke" "tests/smoke/"
        run_tests "integration" "Integration Tests" "integration" "tests/integration/"
        ;;

    all)
        echo -e "${YELLOW}Running ALL tests...${NC}"

        # Track failures
        FAILED=0

        run_tests "smoke" "Smoke Tests" "smoke" "tests/smoke/" || FAILED=$((FAILED + 1))
        run_tests "unit" "Unit Tests" "unit" "tests/unit/" || FAILED=$((FAILED + 1))
        run_tests "integration" "Integration Tests" "integration" "tests/integration/" || FAILED=$((FAILED + 1))
        run_tests "e2e" "End-to-End Tests" "e2e" "tests/e2e/" || FAILED=$((FAILED + 1))
        run_tests "security" "Security Tests" "security" "tests/security/" || FAILED=$((FAILED + 1))
        run_tests "llm" "LLM Tests" "llm" "tests/llm/" || FAILED=$((FAILED + 1))
        run_tests "regression" "Regression Tests" "regression" "tests/regression/" || FAILED=$((FAILED + 1))
        run_tests "performance" "Performance Tests" "performance" "tests/performance/" || FAILED=$((FAILED + 1))

        # Summary
        echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}TEST SUMMARY${NC}"
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        if [ $FAILED -eq 0 ]; then
            echo -e "${GREEN}✓ ALL TESTS PASSED (8/8)${NC}"
            exit 0
        else
            echo -e "${RED}✗ $FAILED TEST SUITE(S) FAILED${NC}"
            exit 1
        fi
        ;;

    help|--help|-h)
        echo "Usage: ./run_tests.sh [category] [coverage] [parallel]"
        echo ""
        echo "Categories:"
        echo "  smoke       - Quick sanity checks"
        echo "  unit        - Unit tests only"
        echo "  integration - Integration tests only"
        echo "  e2e         - End-to-end tests only"
        echo "  performance - Performance tests only"
        echo "  security    - Security tests only"
        echo "  llm         - LLM tests (prompts, hallucination, adversarial, bias)"
        echo "  regression  - Regression tests only"
        echo "  fast        - Fast tests (unit + smoke)"
        echo "  critical    - Critical tests (smoke + integration)"
        echo "  all         - All tests (default)"
        echo ""
        echo "Options:"
        echo "  coverage    - Generate coverage report (true/false)"
        echo "  parallel    - Run tests in parallel (true/false)"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh smoke                  # Run smoke tests"
        echo "  ./run_tests.sh unit true              # Run unit tests with coverage"
        echo "  ./run_tests.sh all true true          # Run all tests with coverage in parallel"
        echo "  ./run_tests.sh fast                   # Run fast tests only"
        exit 0
        ;;

    *)
        echo -e "${RED}Error: Unknown category '$CATEGORY'${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✓ Tests completed successfully!${NC}\n"
