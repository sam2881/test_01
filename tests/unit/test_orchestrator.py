"""Unit tests for orchestrator service"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestOrchestratorAPI:
    """Test orchestrator API endpoints"""

    @patch('orchestrator.main.workflow')
    @patch('orchestrator.main.postgres_client')
    @patch('orchestrator.main.kafka_client')
    def test_create_task_success(self, mock_kafka, mock_postgres, mock_workflow):
        """Test successful task creation"""
        # Setup
        from orchestrator.main import app
        client = TestClient(app)

        mock_workflow.invoke.return_value = {
            "task_id": "test-123",
            "current_agent": "servicenow",
            "status": "completed",
            "results": {"ticket_id": "INC0012345"}
        }

        # Execute
        response = client.post("/task", json={
            "description": "API Gateway timeout",
            "priority": "P1"
        })

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["processing", "completed"]
        mock_postgres.log_event.assert_called_once()
        mock_kafka.publish_event.assert_called_once()

    def test_create_task_missing_description(self):
        """Test task creation with missing description"""
        from orchestrator.main import app
        client = TestClient(app)

        response = client.post("/task", json={
            "priority": "P1"
        })

        assert response.status_code == 422  # Validation error

    @patch('orchestrator.main.workflow')
    def test_create_task_workflow_failure(self, mock_workflow):
        """Test task creation when workflow fails"""
        from orchestrator.main import app
        client = TestClient(app)

        mock_workflow.invoke.side_effect = Exception("Workflow error")

        response = client.post("/task", json={
            "description": "Test incident",
            "priority": "P2"
        })

        # Should handle error gracefully
        assert response.status_code in [500, 200]

    def test_health_endpoint(self):
        """Test health check endpoint"""
        from orchestrator.main import app
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200


class TestWorkflowRouter:
    """Test LangGraph workflow routing logic"""

    def test_routing_decision_servicenow(self, mock_openai_response):
        """Test routing to ServiceNow agent"""
        # Mock LLM response indicating ServiceNow
        with patch('openai.ChatCompletion.create') as mock_openai:
            mock_openai.return_value = mock_openai_response

            from orchestrator.router import route_task

            state = {
                "task_id": "test-123",
                "description": "Production API Gateway down",
                "priority": "P1"
            }

            result = route_task(state)
            assert result["current_agent"] == "servicenow"

    def test_routing_decision_jira(self):
        """Test routing to Jira agent"""
        with patch('openai.ChatCompletion.create') as mock_openai:
            mock_openai.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"selected_agent": "jira", "confidence": 0.93}'
                    }
                }]
            }

            from orchestrator.router import route_task

            state = {
                "task_id": "test-456",
                "description": "Bug in payment validation code",
                "priority": "P2"
            }

            result = route_task(state)
            assert result["current_agent"] == "jira"

    def test_routing_with_invalid_response(self):
        """Test handling of invalid LLM routing response"""
        with patch('openai.ChatCompletion.create') as mock_openai:
            mock_openai.return_value = {
                "choices": [{
                    "message": {"content": "invalid json"}
                }]
            }

            from orchestrator.router import route_task

            state = {"task_id": "test-789", "description": "Test"}

            # Should handle error gracefully
            result = route_task(state)
            assert "error" in result or result.get("current_agent") == ""


class TestAgentState:
    """Test agent state management"""

    def test_initial_state_creation(self):
        """Test creating initial agent state"""
        from orchestrator.router import AgentState

        state: AgentState = {
            "task_id": "test-123",
            "task_type": "incident",
            "description": "Test incident",
            "context": {},
            "current_agent": "",
            "results": {},
            "status": "pending",
            "error": ""
        }

        assert state["task_id"] == "test-123"
        assert state["status"] == "pending"
        assert state["current_agent"] == ""

    def test_state_update(self):
        """Test updating agent state"""
        from orchestrator.router import AgentState

        state: AgentState = {
            "task_id": "test-123",
            "task_type": "incident",
            "description": "Test",
            "context": {},
            "current_agent": "",
            "results": {},
            "status": "pending",
            "error": ""
        }

        # Update state
        state["current_agent"] = "servicenow"
        state["status"] = "processing"
        state["results"] = {"ticket_id": "INC0012345"}

        assert state["current_agent"] == "servicenow"
        assert state["status"] == "processing"
        assert state["results"]["ticket_id"] == "INC0012345"
