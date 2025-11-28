"""Pytest configuration and shared fixtures"""
import os
import sys
import pytest
from typing import Generator, Dict, Any
from unittest.mock import Mock, MagicMock
import httpx

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Test configuration
TEST_API_URL = os.getenv("TEST_API_URL", "http://localhost:8000")
TEST_TIMEOUT = 30


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"selected_agent": "servicenow", "confidence": 0.95, "reasoning": "Infrastructure issue detected"}'
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150
        }
    }


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic Claude API response"""
    return {
        "content": [
            {
                "type": "text",
                "text": '{"selected_agent": "jira", "confidence": 0.92, "reasoning": "Software bug requiring code fix"}'
            }
        ],
        "usage": {
            "input_tokens": 120,
            "output_tokens": 60
        }
    }


@pytest.fixture
def sample_incident():
    """Sample incident data"""
    return {
        "description": "API Gateway returning 502 errors",
        "priority": "P1",
        "metadata": {
            "category": "Performance",
            "affected_service": "api-gateway",
            "affected_users": 1500
        }
    }


@pytest.fixture
def sample_jira_ticket():
    """Sample Jira ticket data"""
    return {
        "description": "Payment validation failing for UTF-8 names",
        "priority": "P2",
        "metadata": {
            "category": "Bug",
            "affected_service": "payment-service",
            "component": "PaymentService.java"
        }
    }


@pytest.fixture
def mock_postgres_client():
    """Mock PostgreSQL client"""
    mock = MagicMock()
    mock.log_event.return_value = True
    mock.get_events.return_value = []
    mock.update_event.return_value = True
    return mock


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock


@pytest.fixture
def mock_kafka_client():
    """Mock Kafka client"""
    mock = MagicMock()
    mock.publish_event.return_value = True
    return mock


@pytest.fixture
def mock_weaviate_client():
    """Mock Weaviate vector database client"""
    mock = MagicMock()
    mock.query.return_value = {
        "data": {
            "Get": {
                "Incident": [
                    {
                        "incident_id": "INC0011234",
                        "description": "API Gateway slow response",
                        "_additional": {"certainty": 0.91}
                    }
                ]
            }
        }
    }
    return mock


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j graph database client"""
    mock = MagicMock()
    mock.run.return_value = [
        {
            "cause": "High CPU Load",
            "resolution": "Scale instances",
            "count": 5
        }
    ]
    return mock


@pytest.fixture
async def async_client() -> Generator:
    """Async HTTP client for API testing"""
    async with httpx.AsyncClient(base_url=TEST_API_URL, timeout=TEST_TIMEOUT) as client:
        yield client


@pytest.fixture
def mock_servicenow_api():
    """Mock ServiceNow API responses"""
    return {
        "result": {
            "sys_id": "abc123",
            "number": "INC0012345",
            "state": "1",
            "short_description": "API Gateway timeout"
        }
    }


@pytest.fixture
def mock_jira_api():
    """Mock Jira API responses"""
    return {
        "id": "10001",
        "key": "ENG-2345",
        "fields": {
            "summary": "Fix UTF-8 validation",
            "status": {"name": "To Do"}
        }
    }


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses"""
    return {
        "id": 234,
        "number": 234,
        "title": "Fix: Support UTF-8 characters",
        "state": "open",
        "html_url": "https://github.com/org/repo/pull/234"
    }


@pytest.fixture
def approval_request_data():
    """Sample approval request data"""
    return {
        "approval_id": "apr_test_123",
        "approval_type": "routing_override",
        "status": "pending",
        "incident_id": "INC0012345",
        "routing_decision": {
            "selected_agent": "infrastructure",
            "confidence": 0.92,
            "reasoning": "Infrastructure scaling required"
        }
    }


@pytest.fixture
def execution_plan():
    """Sample execution plan"""
    return {
        "plan_id": "plan_test_456",
        "steps": [
            {
                "step_number": 1,
                "action": "Check current instance count",
                "command": "gcloud compute instance-groups list",
                "risk_level": "low"
            },
            {
                "step_number": 2,
                "action": "Scale instances",
                "command": "gcloud compute instance-groups managed resize api-gateway-group --size=5",
                "risk_level": "medium"
            }
        ],
        "estimated_duration": "10 minutes",
        "risk_assessment": "medium"
    }


# Test data generators
def generate_incidents(count: int = 10) -> list:
    """Generate multiple test incidents"""
    categories = ["Performance", "Security", "Network", "Database", "API"]
    priorities = ["P1", "P2", "P3", "P4"]

    incidents = []
    for i in range(count):
        incidents.append({
            "description": f"Test incident {i}: System issue detected",
            "priority": priorities[i % len(priorities)],
            "metadata": {
                "category": categories[i % len(categories)],
                "test_incident": True
            }
        })
    return incidents


# Environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    yield
    # Cleanup
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
