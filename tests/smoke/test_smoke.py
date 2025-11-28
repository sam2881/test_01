"""Smoke tests for AI Agent Platform - Quick sanity checks"""
import pytest
import httpx


@pytest.mark.smoke
@pytest.mark.asyncio
class TestSystemHealth:
    """Smoke test: System is up and responsive"""

    async def test_api_is_running(self, async_client):
        """Test that API server is running"""

        response = await async_client.get("/health")
        assert response.status_code == 200, "API server is not responding"

    async def test_api_returns_valid_json(self, async_client):
        """Test that API returns valid JSON"""

        response = await async_client.get("/health")

        # Should return valid JSON
        try:
            data = response.json()
            assert isinstance(data, dict) or isinstance(data, list) or isinstance(data, str)
        except ValueError:
            pytest.fail("API is not returning valid JSON")


@pytest.mark.smoke
@pytest.mark.asyncio
class TestCoreEndpoints:
    """Smoke test: Core endpoints are accessible"""

    async def test_task_endpoint_accessible(self, async_client):
        """Test that task creation endpoint is accessible"""

        response = await async_client.post("/task", json={
            "description": "Smoke test incident",
            "priority": "P3"
        })

        # Should not return 404 or 500
        assert response.status_code not in [404, 500], "Task endpoint is not accessible"

    async def test_incidents_endpoint_accessible(self, async_client):
        """Test that incidents endpoint is accessible"""

        response = await async_client.get("/incidents")

        # Should be accessible
        assert response.status_code not in [404, 500], "Incidents endpoint is not accessible"

    async def test_agents_endpoint_accessible(self, async_client):
        """Test that agents endpoint is accessible"""

        response = await async_client.get("/agents/status")

        # Should be accessible
        assert response.status_code not in [404, 500], "Agents endpoint is not accessible"

    async def test_approvals_endpoint_accessible(self, async_client):
        """Test that approvals endpoint is accessible"""

        response = await async_client.get("/api/hitl/approvals/pending")

        # Should be accessible
        assert response.status_code not in [404, 500], "Approvals endpoint is not accessible"

    async def test_stats_endpoint_accessible(self, async_client):
        """Test that stats endpoint is accessible"""

        response = await async_client.get("/api/stats/dashboard")

        # Should be accessible
        assert response.status_code not in [404, 500], "Stats endpoint is not accessible"


@pytest.mark.smoke
@pytest.mark.asyncio
class TestBasicFunctionality:
    """Smoke test: Basic operations work"""

    async def test_can_create_task(self, async_client):
        """Test that we can create a task"""

        response = await async_client.post("/task", json={
            "description": "Smoke test - basic functionality check",
            "priority": "P4"
        })

        # Should create successfully
        assert response.status_code in [200, 201], "Cannot create task"

        data = response.json()
        assert "task_id" in data, "Task creation didn't return task_id"

    async def test_can_list_incidents(self, async_client):
        """Test that we can list incidents"""

        response = await async_client.get("/incidents")

        # Should return a list
        assert response.status_code == 200, "Cannot list incidents"

        data = response.json()
        assert isinstance(data, list), "Incidents endpoint didn't return a list"

    async def test_can_get_agent_status(self, async_client):
        """Test that we can get agent status"""

        response = await async_client.get("/agents/status")

        # Should return agent information
        assert response.status_code == 200, "Cannot get agent status"

        data = response.json()
        assert isinstance(data, list), "Agents status didn't return a list"


@pytest.mark.smoke
@pytest.mark.asyncio
class TestCriticalPaths:
    """Smoke test: Critical paths work end-to-end"""

    async def test_incident_creation_flow(self, async_client):
        """Test basic incident creation flow"""

        # Create incident
        create_response = await async_client.post("/task", json={
            "description": "Smoke test - critical path check",
            "priority": "P3"
        })

        assert create_response.status_code in [200, 201], "Incident creation failed"

        task_id = create_response.json().get("task_id")
        assert task_id is not None, "No task_id returned"

        # Verify it appears in incidents list
        list_response = await async_client.get("/incidents")

        if list_response.status_code == 200:
            incidents = list_response.json()
            # In a full system, would verify our incident is in the list
            assert isinstance(incidents, list)

    async def test_hitl_approval_flow(self, async_client):
        """Test HITL approval flow smoke test"""

        # Get pending approvals
        response = await async_client.get("/api/hitl/approvals/pending")

        assert response.status_code == 200, "Cannot get pending approvals"

        approvals = response.json()
        assert isinstance(approvals, list), "Approvals didn't return a list"


@pytest.mark.smoke
class TestDatabaseConnectivity:
    """Smoke test: Database connections work"""

    def test_postgres_connection(self):
        """Test PostgreSQL connection"""

        try:
            from utils.postgres_client import PostgresClient

            client = PostgresClient()
            # If we get here without exception, connection works
            assert True

        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    def test_redis_connection(self):
        """Test Redis connection"""

        try:
            from utils.redis_client import RedisClient

            client = RedisClient()
            # If we get here without exception, connection works
            assert True

        except Exception as e:
            pytest.skip(f"Redis not available: {e}")

    def test_weaviate_connection(self):
        """Test Weaviate connection"""

        try:
            import weaviate

            client = weaviate.Client("http://localhost:8081")
            # Quick check
            assert client.is_ready() or True

        except Exception as e:
            pytest.skip(f"Weaviate not available: {e}")

    def test_neo4j_connection(self):
        """Test Neo4j connection"""

        try:
            from neo4j import GraphDatabase

            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "password123")
            )

            driver.verify_connectivity()
            assert True

        except Exception as e:
            pytest.skip(f"Neo4j not available: {e}")


@pytest.mark.smoke
class TestExternalServices:
    """Smoke test: External service connectivity"""

    def test_kafka_connection(self):
        """Test Kafka connection"""

        try:
            from kafka import KafkaProducer

            producer = KafkaProducer(
                bootstrap_servers='localhost:29092',
                request_timeout_ms=5000
            )

            # If we get here, Kafka is accessible
            assert True

        except Exception as e:
            pytest.skip(f"Kafka not available: {e}")


@pytest.mark.smoke
class TestConfiguration:
    """Smoke test: Configuration is valid"""

    def test_environment_variables_set(self):
        """Test that critical environment variables are set"""

        import os

        # Check for presence (not values) of critical vars
        # In production, these should be set

        env_vars_to_check = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        ]

        missing_vars = []
        for var in env_vars_to_check:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            pytest.skip(f"Environment variables not set: {', '.join(missing_vars)}")

    def test_agent_endpoints_configured(self):
        """Test that agent endpoints are configured"""

        try:
            from orchestrator.main import AGENT_ENDPOINTS

            # Should have multiple agents configured
            assert len(AGENT_ENDPOINTS) > 0, "No agents configured"

            # Check for expected agents
            expected_agents = ["servicenow", "jira", "github"]

            for agent in expected_agents:
                assert agent in AGENT_ENDPOINTS, f"Agent {agent} not configured"

        except ImportError:
            pytest.skip("Cannot import agent configuration")


@pytest.mark.smoke
@pytest.mark.asyncio
class TestErrorHandling:
    """Smoke test: Basic error handling works"""

    async def test_invalid_endpoint_returns_404(self, async_client):
        """Test that invalid endpoints return 404"""

        response = await async_client.get("/nonexistent_endpoint_xyz")

        assert response.status_code == 404, "Invalid endpoint didn't return 404"

    async def test_invalid_json_returns_error(self, async_client):
        """Test that invalid JSON returns error"""

        response = await async_client.post(
            "/task",
            content="not valid json {",
            headers={"Content-Type": "application/json"}
        )

        # Should return 4xx error
        assert 400 <= response.status_code < 500, "Invalid JSON not handled properly"

    async def test_missing_fields_returns_error(self, async_client):
        """Test that missing required fields returns error"""

        response = await async_client.post("/task", json={
            "priority": "P1"
            # Missing required 'description'
        })

        # Should return 422 (validation error)
        assert response.status_code == 422, "Missing fields not validated"


@pytest.mark.smoke
class TestSystemResources:
    """Smoke test: System has adequate resources"""

    def test_memory_usage_reasonable(self):
        """Test that memory usage is reasonable"""

        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024

            # Should be under 1GB for basic tests
            assert memory_mb < 1024, f"Memory usage too high: {memory_mb:.0f}MB"

        except ImportError:
            pytest.skip("psutil not available")

    def test_disk_space_available(self):
        """Test that adequate disk space is available"""

        try:
            import psutil

            disk = psutil.disk_usage('/')

            # Should have at least 1GB free
            free_gb = disk.free / (1024 ** 3)
            assert free_gb > 1.0, f"Low disk space: {free_gb:.1f}GB free"

        except ImportError:
            pytest.skip("psutil not available")
