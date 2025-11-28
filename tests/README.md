# 🧪 Test Suite - AI Agent Platform

Comprehensive test suite covering unit, integration, E2E, performance, security, and LLM-specific tests.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Test Categories](#test-categories)
3. [Quick Start](#quick-start)
4. [Running Tests](#running-tests)
5. [Test Coverage](#test-coverage)
6. [Writing Tests](#writing-tests)
7. [CI/CD Integration](#cicd-integration)

---

## 📊 Overview

### Test Statistics

- **Total Test Files**: 15+
- **Test Categories**: 8
- **Coverage**: Unit, Integration, E2E, Performance, Security, LLM, Regression, Smoke
- **Framework**: Pytest 7.4+

### Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── pytest.ini                  # Pytest configuration
├── requirements-test.txt       # Testing dependencies
├── unit/                       # Unit tests
│   ├── test_orchestrator.py
│   ├── test_agents.py
│   └── test_utils.py
├── integration/                # Integration tests
│   └── test_api_endpoints.py
├── e2e/                        # End-to-end tests
│   ├── test_servicenow_workflow.py
│   └── test_jira_workflow.py
├── performance/                # Performance tests
│   └── test_load.py
├── security/                   # Security tests
│   └── test_security.py
├── llm/                        # LLM-specific tests
│   ├── test_prompt_quality.py
│   ├── test_hallucination.py
│   ├── test_adversarial.py
│   └── test_bias_fairness.py
├── regression/                 # Regression tests
│   └── test_regression.py
└── smoke/                      # Smoke tests
    └── test_smoke.py
```

---

## 🎯 Test Categories

### 1. 🔬 Unit Tests (`tests/unit/`)

Test individual components in isolation.

**Coverage**:
- Orchestrator routing logic
- Individual agent functionality (ServiceNow, Jira, GitHub, Infrastructure, Data, GCP Monitor)
- Utility modules (PostgreSQL, Redis, Kafka, Weaviate, Neo4j)
- DSPy modules
- HITL approval logic
- BERTopic classification

**Run**:
```bash
pytest tests/unit/ -v
```

### 2. 🔗 Integration Tests (`tests/integration/`)

Test component interactions and API endpoints.

**Coverage**:
- Task management API
- Incident management API
- HITL approval API
- Agent management API
- Statistics API
- WebSocket events
- RAG integration (Weaviate + Neo4j)
- Error handling

**Run**:
```bash
pytest tests/integration/ -v
```

### 3. 🎯 E2E Tests (`tests/e2e/`)

Test complete workflows end-to-end.

**Coverage**:
- Complete ServiceNow incident resolution (18-minute flow)
- Complete Jira bug fix workflow (2h 20m flow)
- P1 incident priority handling
- Infrastructure scaling workflow
- Error scenarios

**Run**:
```bash
pytest tests/e2e/ -v -m e2e
```

### 4. ⚡ Performance Tests (`tests/performance/`)

Load testing, stress testing, and performance benchmarks.

**Coverage**:
- Concurrent task creation (50+ concurrent)
- Sustained load testing (5 req/s for 30s)
- Burst traffic handling (100 simultaneous requests)
- API response time SLA (<500ms P95)
- Database query performance
- RAG search performance
- Memory leak detection

**Run**:
```bash
pytest tests/performance/ -v -m performance
```

**Load Testing** (with Locust):
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

### 5. 🔒 Security Tests (`tests/security/`)

Security testing and vulnerability detection.

**Coverage**:
- SQL injection prevention
- XSS prevention
- Command injection prevention
- Path traversal prevention
- Authentication & authorization
- Data leakage prevention
- Rate limiting
- API key protection
- Dependency vulnerabilities

**Run**:
```bash
pytest tests/security/ -v -m security
```

### 6. 🤖 LLM Tests (`tests/llm/`)

LLM-specific testing: prompts, hallucination, adversarial, bias.

**Coverage**:

#### 📝 Prompt Quality (`test_prompt_quality.py`)
- Prompt structure validation
- Clarity and specificity
- Consistency across calls
- Output format validation
- Token usage efficiency

#### 🔍 Hallucination Detection (`test_hallucination.py`)
- Fact verification against knowledge base
- Incident ID validation
- Confidence score calibration
- Technical detail accuracy
- RAG grounding mechanisms
- Citation requirements

#### ⚔️ Adversarial Testing (`test_adversarial.py`)
- Jailbreak prevention ("ignore previous instructions")
- Role reversal attack defense
- Prompt injection prevention
- Unicode homoglyph attacks
- Prompt leakage prevention
- API key extraction attempts
- Token smuggling
- Context overflow attacks

#### ⚖️ Bias & Fairness (`test_bias_fairness.py`)
- Priority assignment bias
- Language and cultural bias
- Agent selection fairness
- Historical data representation
- Equal opportunity metrics
- Demographic parity
- Calibration fairness

**Run**:
```bash
# All LLM tests
pytest tests/llm/ -v -m llm

# Specific categories
pytest tests/llm/test_hallucination.py -v
pytest tests/llm/test_adversarial.py -v -m adversarial
pytest tests/llm/test_bias_fairness.py -v -m bias
```

### 7. 🔄 Regression Tests (`tests/regression/`)

Prevent breaking changes.

**Coverage**:
- API contract stability
- Response schema validation
- Data format consistency
- Performance baselines
- Backward compatibility
- Database schema stability

**Run**:
```bash
pytest tests/regression/ -v -m regression
```

### 8. 💨 Smoke Tests (`tests/smoke/`)

Quick sanity checks for deployment verification.

**Coverage**:
- System health
- Core endpoint accessibility
- Basic functionality
- Critical paths
- Database connectivity
- External service connectivity
- Configuration validation
- Error handling
- System resources

**Run**:
```bash
pytest tests/smoke/ -v -m smoke
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Or install with main dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy test environment
cp .env.example .env.test

# Set test-specific variables
export TESTING=true
export TEST_API_URL=http://localhost:8000
```

### 3. Start Services

```bash
# Start backend services
cd deployment
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run specific category
pytest tests/unit/ -v

# Run with coverage
pytest --cov=backend --cov-report=html
```

---

## 🎮 Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_orchestrator.py

# Run specific test
pytest tests/unit/test_orchestrator.py::TestOrchestratorAPI::test_create_task_success

# Run tests by marker
pytest -m unit
pytest -m "integration and not slow"
pytest -m "llm or security"
```

### Advanced Options

```bash
# Run tests in parallel (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Run only failed tests from last run
pytest --lf

# Run failed tests first, then all
pytest --ff

# Show local variables on failure
pytest -l

# Detailed failure output
pytest -vv

# Run with specific log level
pytest --log-cli-level=DEBUG
```

### Filter Tests

```bash
# Run fast tests only
pytest -m "not slow"

# Run tests that don't require external APIs
pytest -m "not requires_api"

# Run smoke tests only (quick deployment check)
pytest -m smoke --maxfail=1

# Run security and LLM tests
pytest -m "security or llm"
```

### Coverage

```bash
# Generate coverage report
pytest --cov=backend --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Fail if coverage below threshold
pytest --cov=backend --cov-fail-under=70
```

---

## 📈 Test Coverage

### Current Coverage Goals

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| Orchestrator | 80%+ | High |
| Agents | 75%+ | High |
| Utils | 70%+ | Medium |
| RAG | 70%+ | Medium |
| HITL | 75%+ | High |
| API Endpoints | 85%+ | High |

### Generate Coverage Report

```bash
# Terminal report
pytest --cov=backend --cov-report=term-missing

# HTML report
pytest --cov=backend --cov-report=html

# XML report (for CI/CD)
pytest --cov=backend --cov-report=xml
```

---

## ✍️ Writing Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch


@pytest.mark.unit
class TestMyComponent:
    """Test suite for MyComponent"""

    def test_basic_functionality(self):
        """Test basic functionality with clear description"""
        # Arrange
        component = MyComponent()

        # Act
        result = component.do_something()

        # Assert
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_functionality(self, async_client):
        """Test async operations"""
        response = await async_client.get("/endpoint")
        assert response.status_code == 200

    @patch('module.external_dependency')
    def test_with_mock(self, mock_dependency):
        """Test with mocked dependencies"""
        mock_dependency.return_value = "mocked value"
        # ... test logic
```

### Using Fixtures

```python
# Use shared fixtures from conftest.py

def test_with_sample_incident(sample_incident):
    """Use sample incident fixture"""
    assert sample_incident["priority"] == "P1"

def test_with_mock_clients(mock_postgres_client, mock_redis_client):
    """Use multiple fixtures"""
    mock_postgres_client.log_event.return_value = True
    # ... test logic
```

### Test Markers

```python
@pytest.mark.unit  # Unit test
@pytest.mark.integration  # Integration test
@pytest.mark.e2e  # End-to-end test
@pytest.mark.slow  # Slow test (>5 seconds)
@pytest.mark.requires_api  # Requires external API
@pytest.mark.requires_db  # Requires database
@pytest.mark.llm  # LLM-specific test
@pytest.mark.security  # Security test
```

---

## 🔧 CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r tests/requirements-test.txt

    - name: Run smoke tests
      run: pytest tests/smoke/ -v -m smoke

    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=backend

    - name: Run integration tests
      run: pytest tests/integration/ -v

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: local
    hooks:
      - id: pytest-smoke
        name: pytest smoke tests
        entry: pytest tests/smoke/ -v -m smoke
        language: system
        pass_filenames: false
        always_run: true
EOF

# Install hooks
pre-commit install
```

### Test Pipeline

```bash
#!/bin/bash
# test_pipeline.sh

set -e

echo "🧪 Running Test Pipeline..."

# 1. Smoke tests (fast)
echo "💨 Running smoke tests..."
pytest tests/smoke/ -v -m smoke --maxfail=1

# 2. Unit tests
echo "🔬 Running unit tests..."
pytest tests/unit/ -v --cov=backend

# 3. Integration tests
echo "🔗 Running integration tests..."
pytest tests/integration/ -v

# 4. Security tests
echo "🔒 Running security tests..."
pytest tests/security/ -v -m security

# 5. LLM tests
echo "🤖 Running LLM tests..."
pytest tests/llm/ -v -m llm

echo "✅ All tests passed!"
```

---

## 🐛 Debugging Tests

### Run Single Test with Debug

```bash
# Run with pdb (Python debugger)
pytest tests/unit/test_orchestrator.py::test_name --pdb

# Run with ipdb (enhanced debugger)
pytest tests/unit/test_orchestrator.py::test_name --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### Show Print Statements

```bash
# Show print output
pytest -s

# Show print output for failed tests only
pytest --capture=no
```

### Increase Verbosity

```bash
# Very verbose
pytest -vv

# Show local variables on failure
pytest -l

# Show full traceback
pytest --tb=long
```

---

## 📊 Test Reports

### HTML Report

```bash
pytest --html=report.html --self-contained-html
```

### JUnit XML (for CI/CD)

```bash
pytest --junitxml=junit.xml
```

### JSON Report

```bash
pytest --json-report --json-report-file=report.json
```

---

## 🎯 Best Practices

1. **Write tests first** (TDD): Write failing test → Implement → Pass test
2. **Keep tests isolated**: Each test should be independent
3. **Use descriptive names**: `test_routing_selects_infrastructure_for_502_errors`
4. **Follow AAA pattern**: Arrange → Act → Assert
5. **Mock external dependencies**: Don't call real APIs in unit tests
6. **Test edge cases**: Empty inputs, null values, extreme values
7. **Maintain test data**: Use fixtures for consistent test data
8. **Keep tests fast**: Unit tests < 1s, Integration tests < 5s
9. **Update tests with code**: Tests are part of the codebase
10. **Monitor coverage**: Aim for 70%+ coverage

---

## 📝 Test Checklist

When adding new features:

- [ ] Write unit tests for new functions/classes
- [ ] Write integration tests for new API endpoints
- [ ] Add E2E test if new workflow
- [ ] Update smoke tests if critical functionality
- [ ] Add security tests for sensitive operations
- [ ] Test error handling and edge cases
- [ ] Update test documentation
- [ ] Verify coverage doesn't decrease
- [ ] Run full test suite before committing

---

## 🆘 Troubleshooting

### Tests Fail Locally

```bash
# Clean pytest cache
pytest --cache-clear

# Reinstall dependencies
pip install -r tests/requirements-test.txt --force-reinstall

# Check service status
docker-compose ps
```

### Async Tests Fail

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Check pytest.ini has asyncio_mode = auto
```

### Import Errors

```bash
# Add backend to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# Or run from project root
cd /path/to/ai_agent_app
pytest
```

---

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)

---

**For issues or questions, check the [main README](../README.md) or open an issue.**

**Happy Testing! 🧪✨**
