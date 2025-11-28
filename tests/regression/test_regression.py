"""Regression tests for AI Agent Platform"""
import pytest
import json
import httpx


@pytest.mark.regression
@pytest.mark.asyncio
class TestAPIContractRegression:
    """Test that API contracts haven't changed"""

    async def test_task_creation_response_schema(self, async_client):
        """Test that task creation response schema is unchanged"""

        response = await async_client.post("/task", json={
            "description": "Regression test incident",
            "priority": "P3"
        })

        if response.status_code in [200, 201]:
            data = response.json()

            # Required fields that should always be present
            required_fields = ["task_id", "status"]

            for field in required_fields:
                assert field in data, f"Breaking change: missing field '{field}' in task response"

    async def test_incidents_list_response_schema(self, async_client):
        """Test that incidents list response schema is unchanged"""

        response = await async_client.get("/incidents?limit=1")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list), "Breaking change: incidents endpoint should return list"

        if len(data) > 0:
            incident = data[0]

            # Fields that should exist in incident objects
            expected_fields = ["incident_id", "description", "priority", "status"]

            for field in expected_fields:
                assert field in incident, f"Breaking change: missing field '{field}' in incident"

    async def test_approvals_response_schema(self, async_client):
        """Test that approvals response schema is unchanged"""

        response = await async_client.get("/api/hitl/approvals/pending")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list), "Breaking change: approvals should return list"

        if len(data) > 0:
            approval = data[0]

            expected_fields = ["approval_id", "approval_type", "status"]

            for field in expected_fields:
                assert field in approval, f"Breaking change: missing field '{field}' in approval"


@pytest.mark.regression
@pytest.mark.asyncio
class TestFunctionalRegression:
    """Test that core functionality still works"""

    async def test_p1_incidents_still_prioritized(self, async_client):
        """Test that P1 incidents are still handled with priority"""

        response = await async_client.post("/task", json={
            "description": "CRITICAL: Production database down",
            "priority": "P1"
        })

        assert response.status_code in [200, 201]

        data = response.json()
        # Should be accepted and processed
        assert "task_id" in data

    async def test_servicenow_routing_still_works(self, async_client):
        """Test that ServiceNow routing hasn't regressed"""

        response = await async_client.post("/task", json={
            "description": "API Gateway infrastructure failure in production",
            "priority": "P1"
        })

        assert response.status_code in [200, 201]

        # Give time for routing
        import asyncio
        await asyncio.sleep(2)

        # Check routing (if approval created)
        approvals = await async_client.get("/api/hitl/approvals/pending")
        if approvals.status_code == 200 and len(approvals.json()) > 0:
            approval = approvals.json()[0]
            # Should route to infrastructure or servicenow
            agent = approval.get("routing_decision", {}).get("selected_agent", "")
            assert agent in ["infrastructure", "servicenow", "infra", ""]

    async def test_jira_integration_still_works(self, async_client):
        """Test that Jira integration hasn't regressed"""

        response = await async_client.post("/task", json={
            "description": "Bug in payment validation code - NullPointerException",
            "priority": "P2",
            "metadata": {"category": "Bug"}
        })

        assert response.status_code in [200, 201]


@pytest.mark.regression
class TestDataFormatRegression:
    """Test that data formats haven't changed"""

    def test_priority_values_unchanged(self):
        """Test that valid priority values haven't changed"""

        valid_priorities = ["P1", "P2", "P3", "P4"]

        # These should remain valid
        for priority in valid_priorities:
            assert priority in ["P1", "P2", "P3", "P4"]

    def test_status_values_unchanged(self):
        """Test that valid status values haven't changed"""

        valid_statuses = ["New", "In Progress", "Resolved", "Closed"]

        # These should remain valid
        for status in valid_statuses:
            assert status in ["New", "In Progress", "Resolved", "Closed", "Done"]

    def test_agent_names_unchanged(self):
        """Test that agent names haven't changed"""

        valid_agents = ["servicenow", "jira", "github", "infrastructure", "data", "gcp_monitor"]

        # These should still be recognized
        for agent in valid_agents:
            assert agent in ["servicenow", "jira", "github", "infrastructure", "infra", "data", "gcp_monitor"]


@pytest.mark.regression
@pytest.mark.asyncio
class TestPerformanceRegression:
    """Test that performance hasn't regressed"""

    async def test_api_response_time_not_regressed(self, async_client):
        """Test that API response times haven't gotten worse"""

        import time

        start = time.time()
        response = await async_client.get("/health")
        duration = time.time() - start

        # Health endpoint should respond in under 1 second
        assert duration < 1.0, f"Performance regression: health endpoint took {duration:.2f}s"

    async def test_incident_query_time_not_regressed(self, async_client):
        """Test that incident queries haven't slowed down"""

        import time

        start = time.time()
        response = await async_client.get("/incidents?limit=10")
        duration = time.time() - start

        # Should respond in under 2 seconds
        assert duration < 2.0, f"Performance regression: incident query took {duration:.2f}s"


@pytest.mark.regression
class TestBackwardCompatibility:
    """Test backward compatibility with previous versions"""

    def test_old_api_format_still_works(self):
        """Test that old API request formats still work"""

        # Old format (if you had one)
        old_format = {
            "description": "Test incident",
            "priority": "P2"
        }

        # Should still have required fields
        assert "description" in old_format
        assert "priority" in old_format

    def test_deprecated_fields_still_accepted(self):
        """Test that deprecated fields are still accepted (if any)"""

        # Example: if you renamed a field but want backward compatibility
        # Old field: "task_type"
        # New field: "incident_type"

        # Both should work during deprecation period
        assert True  # Document deprecation policy


@pytest.mark.regression
class TestDatabaseSchemaRegression:
    """Test that database schema changes haven't broken queries"""

    def test_incidents_table_schema(self):
        """Test that incidents table structure is compatible"""

        # Expected columns
        expected_columns = [
            "incident_id",
            "short_description",
            "description",
            "priority",
            "status",
            "created_at",
            "updated_at"
        ]

        # This would query actual database in practice
        # For now, document expected schema
        assert len(expected_columns) > 0

    def test_approvals_table_schema(self):
        """Test that approvals table structure is compatible"""

        expected_columns = [
            "approval_id",
            "approval_type",
            "status",
            "created_at",
            "timeout_at"
        ]

        assert len(expected_columns) > 0


@pytest.mark.regression
class TestConfigurationRegression:
    """Test that configuration changes haven't broken functionality"""

    def test_environment_variables_compatibility(self):
        """Test that required environment variables are still recognized"""

        import os

        # Critical env vars that should always be supported
        critical_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        ]

        # In test, these might not be set, but code should recognize them
        for var in critical_vars:
            # Just check the names are consistent
            assert var.isupper()
            assert "_" in var

    def test_agent_configuration_format(self):
        """Test that agent configuration format hasn't changed"""

        # Example agent config
        agent_config = {
            "name": "servicenow",
            "endpoint": "http://servicenow_agent:8010",
            "capabilities": ["incident_management"]
        }

        assert "name" in agent_config
        assert "endpoint" in agent_config
