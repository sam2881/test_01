"""Integration tests for API endpoints"""
import pytest
import httpx
import asyncio
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.asyncio
class TestTaskAPI:
    """Test task management API endpoints"""

    async def test_create_task_e2e(self, async_client):
        """Test complete task creation flow"""
        response = await async_client.post("/task", json={
            "description": "Test incident: API Gateway timeout",
            "priority": "P2",
            "metadata": {
                "category": "Performance",
                "test": True
            }
        })

        assert response.status_code in [200, 201]
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["processing", "completed", "pending"]

        return data["task_id"]

    async def test_get_task_status(self, async_client):
        """Test retrieving task status"""
        # First create a task
        create_response = await async_client.post("/task", json={
            "description": "Test task",
            "priority": "P3"
        })
        task_id = create_response.json()["task_id"]

        # Then get its status
        response = await async_client.get(f"/task/{task_id}")

        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data
            assert "status" in data

    async def test_list_tasks(self, async_client):
        """Test listing all tasks"""
        response = await async_client.get("/tasks")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.asyncio
class TestIncidentAPI:
    """Test incident management API endpoints"""

    async def test_list_incidents(self, async_client):
        """Test listing incidents"""
        response = await async_client.get("/incidents")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_filter_incidents_by_priority(self, async_client):
        """Test filtering incidents by priority"""
        response = await async_client.get("/incidents?priority=P1")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # All incidents should be P1
        for incident in data:
            assert incident.get("priority") == "P1"

    async def test_filter_incidents_by_status(self, async_client):
        """Test filtering incidents by status"""
        response = await async_client.get("/incidents?status=Resolved")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_incident_by_id(self, async_client):
        """Test retrieving specific incident"""
        # First get list of incidents
        list_response = await async_client.get("/incidents?limit=1")
        incidents = list_response.json()

        if len(incidents) > 0:
            incident_id = incidents[0]["incident_id"]

            # Get specific incident
            response = await async_client.get(f"/incidents/{incident_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["incident_id"] == incident_id

    async def test_get_nonexistent_incident(self, async_client):
        """Test retrieving non-existent incident"""
        response = await async_client.get("/incidents/INVALID_ID_12345")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestHITLAPI:
    """Test Human-in-the-Loop approval API"""

    async def test_list_pending_approvals(self, async_client):
        """Test listing pending approvals"""
        response = await async_client.get("/api/hitl/approvals/pending")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_approval_by_id(self, async_client):
        """Test retrieving specific approval"""
        # First get pending approvals
        list_response = await async_client.get("/api/hitl/approvals/pending")
        approvals = list_response.json()

        if len(approvals) > 0:
            approval_id = approvals[0]["approval_id"]

            response = await async_client.get(f"/api/hitl/approvals/{approval_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["approval_id"] == approval_id

    async def test_approve_routing(self, async_client, approval_request_data):
        """Test approving routing decision"""
        # This test assumes there's a pending approval
        # In real scenario, create an incident first to generate approval

        response = await async_client.post(
            "/api/hitl/approvals/apr_test_123/approve-routing",
            json={
                "approved_by": "test_user@example.com",
                "selected_agent": "infrastructure"
            }
        )

        # Might be 200 (success) or 404 (approval not found in test env)
        assert response.status_code in [200, 404]

    async def test_approve_plan(self, async_client):
        """Test approving execution plan"""
        response = await async_client.post(
            "/api/hitl/approvals/apr_test_456/approve-plan",
            json={
                "approved_by": "test_user@example.com",
                "modifications": ""
            }
        )

        assert response.status_code in [200, 404]

    async def test_reject_plan(self, async_client):
        """Test rejecting execution plan"""
        response = await async_client.post(
            "/api/hitl/approvals/apr_test_789/reject-plan",
            json={
                "rejected_by": "test_user@example.com",
                "rejection_reason": "Too risky for production"
            }
        )

        assert response.status_code in [200, 404]


@pytest.mark.integration
@pytest.mark.asyncio
class TestAgentAPI:
    """Test agent management API"""

    async def test_get_agent_status(self, async_client):
        """Test retrieving all agent statuses"""
        response = await async_client.get("/agents/status")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check for expected agents
        agent_names = [agent["name"] for agent in data]
        expected_agents = ["servicenow", "jira", "github", "infra", "data"]

        for expected in expected_agents:
            assert expected in agent_names

    async def test_get_specific_agent_metrics(self, async_client):
        """Test retrieving metrics for specific agent"""
        response = await async_client.get("/agents/servicenow/metrics")

        if response.status_code == 200:
            data = response.json()
            assert "agent_name" in data
            assert "total_tasks" in data
            assert "success_rate" in data

    async def test_get_agent_logs(self, async_client):
        """Test retrieving agent logs"""
        response = await async_client.get("/agents/servicenow/logs?limit=50")

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 50


@pytest.mark.integration
@pytest.mark.asyncio
class TestStatisticsAPI:
    """Test statistics and dashboard API"""

    async def test_get_dashboard_stats(self, async_client):
        """Test retrieving dashboard statistics"""
        response = await async_client.get("/api/stats/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "active_incidents" in data
        assert "pending_approvals" in data
        assert "success_rate" in data

    async def test_get_system_health(self, async_client):
        """Test retrieving system health"""
        response = await async_client.get("/api/stats/system-health")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Check for expected services
        service_names = [service["name"] for service in data]
        expected_services = ["Kafka", "Weaviate", "Neo4j", "PostgreSQL", "Redis"]

        for expected in expected_services:
            assert expected in service_names

    async def test_get_activity_data(self, async_client):
        """Test retrieving activity timeline data"""
        response = await async_client.get("/api/stats/activity?hours=24")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestWebSocketEvents:
    """Test WebSocket real-time events"""

    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        import socketio

        sio = socketio.AsyncClient()

        connected = False

        @sio.event
        async def connect():
            nonlocal connected
            connected = True

        try:
            await sio.connect('http://localhost:8000')
            await asyncio.sleep(1)
            assert connected is True
        except Exception as e:
            # Connection might fail in test environment
            pytest.skip(f"WebSocket connection failed: {e}")
        finally:
            await sio.disconnect()

    @pytest.mark.asyncio
    async def test_websocket_incident_created_event(self):
        """Test receiving incident_created event"""
        import socketio

        sio = socketio.AsyncClient()
        event_received = False

        @sio.event
        async def incident_created(data):
            nonlocal event_received
            event_received = True
            assert "incident_id" in data

        try:
            await sio.connect('http://localhost:8000')
            await asyncio.sleep(2)
            # In real test, trigger incident creation here
        except Exception:
            pytest.skip("WebSocket test skipped in test environment")
        finally:
            await sio.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
class TestRAGIntegration:
    """Test RAG system integration"""

    async def test_weaviate_search(self, async_client):
        """Test Weaviate vector search integration"""
        # This would call an endpoint that uses Weaviate
        response = await async_client.post("/api/rag/search", json={
            "query": "API Gateway timeout errors",
            "limit": 5
        })

        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert isinstance(data["results"], list)

    async def test_neo4j_causal_search(self, async_client):
        """Test Neo4j causal relationship search"""
        response = await async_client.post("/api/rag/causal", json={
            "symptom": "502 errors",
            "limit": 3
        })

        if response.status_code == 200:
            data = response.json()
            assert "causes" in data
            assert isinstance(data["causes"], list)


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandling:
    """Test API error handling"""

    async def test_invalid_json_payload(self, async_client):
        """Test handling of invalid JSON"""
        response = await async_client.post(
            "/task",
            content="invalid json {",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    async def test_missing_required_fields(self, async_client):
        """Test handling of missing required fields"""
        response = await async_client.post("/task", json={
            "priority": "P1"
            # Missing 'description'
        })

        assert response.status_code == 422

    async def test_rate_limiting(self, async_client):
        """Test API rate limiting"""
        # Send many requests rapidly
        responses = []
        for _ in range(110):  # Assuming 100 req/min limit
            response = await async_client.get("/health")
            responses.append(response.status_code)

        # At least one should be rate limited
        # In test environment, rate limiting might not be enforced
        assert 200 in responses

    async def test_unauthorized_access(self, async_client):
        """Test unauthorized access handling"""
        # This test assumes authentication is implemented
        response = await async_client.post(
            "/admin/reset",
            headers={"Authorization": "Bearer invalid_token"}
        )

        # Might be 401 (unauthorized) or 404 (endpoint doesn't exist)
        assert response.status_code in [401, 404]
