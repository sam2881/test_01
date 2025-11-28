"""Unit tests for individual agents"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestServiceNowAgent:
    """Test ServiceNow agent functionality"""

    @patch('requests.post')
    def test_create_incident_success(self, mock_post, mock_servicenow_api):
        """Test successful incident creation in ServiceNow"""
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: mock_servicenow_api
        )

        from agents.servicenow.agent import ServiceNowAgent

        agent = ServiceNowAgent()
        result = agent.create_incident(
            short_description="API Gateway timeout",
            description="Production API returning 502 errors",
            priority="1",
            category="Performance"
        )

        assert result["number"] == "INC0012345"
        assert mock_post.called

    @patch('requests.post')
    def test_create_incident_api_error(self, mock_post):
        """Test incident creation with API error"""
        mock_post.return_value = Mock(
            status_code=500,
            text="Internal Server Error"
        )

        from agents.servicenow.agent import ServiceNowAgent

        agent = ServiceNowAgent()

        with pytest.raises(Exception):
            agent.create_incident(
                short_description="Test",
                description="Test incident",
                priority="2"
            )

    @patch('requests.get')
    def test_get_incident(self, mock_get, mock_servicenow_api):
        """Test retrieving incident from ServiceNow"""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: mock_servicenow_api
        )

        from agents.servicenow.agent import ServiceNowAgent

        agent = ServiceNowAgent()
        result = agent.get_incident("INC0012345")

        assert result["number"] == "INC0012345"

    @patch('requests.patch')
    def test_update_incident(self, mock_patch, mock_servicenow_api):
        """Test updating incident in ServiceNow"""
        mock_patch.return_value = Mock(
            status_code=200,
            json=lambda: {**mock_servicenow_api, "state": "6"}
        )

        from agents.servicenow.agent import ServiceNowAgent

        agent = ServiceNowAgent()
        result = agent.update_incident(
            incident_id="INC0012345",
            state="6",
            close_notes="Resolved by scaling instances"
        )

        assert result["state"] == "6"


class TestJiraAgent:
    """Test Jira agent functionality"""

    @patch('requests.post')
    def test_create_issue_success(self, mock_post, mock_jira_api):
        """Test successful issue creation in Jira"""
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: mock_jira_api
        )

        from agents.jira.agent import JiraAgent

        agent = JiraAgent()
        result = agent.create_issue(
            project_key="ENG",
            summary="Fix UTF-8 validation",
            description="Payment validation failing",
            issue_type="Bug",
            priority="High"
        )

        assert result["key"] == "ENG-2345"
        assert mock_post.called

    @patch('requests.post')
    def test_create_issue_invalid_project(self, mock_post):
        """Test issue creation with invalid project"""
        mock_post.return_value = Mock(
            status_code=400,
            text="Project does not exist"
        )

        from agents.jira.agent import JiraAgent

        agent = JiraAgent()

        with pytest.raises(Exception):
            agent.create_issue(
                project_key="INVALID",
                summary="Test",
                description="Test",
                issue_type="Bug"
            )

    @patch('requests.put')
    def test_transition_issue(self, mock_put):
        """Test transitioning Jira issue status"""
        mock_put.return_value = Mock(status_code=204)

        from agents.jira.agent import JiraAgent

        agent = JiraAgent()
        result = agent.transition_issue(
            issue_key="ENG-2345",
            transition_id="31"  # Done
        )

        assert result is True


class TestGitHubAgent:
    """Test GitHub agent functionality"""

    @patch('requests.post')
    def test_create_pull_request(self, mock_post, mock_github_api):
        """Test creating GitHub pull request"""
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: mock_github_api
        )

        from agents.github.agent import GitHubAgent

        agent = GitHubAgent()
        result = agent.create_pull_request(
            title="Fix: Support UTF-8 characters",
            body="Fixes ENG-2345",
            head="feature/utf8-validation",
            base="main"
        )

        assert result["number"] == 234
        assert result["state"] == "open"

    @patch('requests.get')
    def test_get_pull_request(self, mock_get, mock_github_api):
        """Test retrieving GitHub pull request"""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: mock_github_api
        )

        from agents.github.agent import GitHubAgent

        agent = GitHubAgent()
        result = agent.get_pull_request(234)

        assert result["number"] == 234

    @patch('requests.put')
    def test_merge_pull_request(self, mock_put):
        """Test merging GitHub pull request"""
        mock_put.return_value = Mock(
            status_code=200,
            json=lambda: {"merged": True, "sha": "abc123"}
        )

        from agents.github.agent import GitHubAgent

        agent = GitHubAgent()
        result = agent.merge_pull_request(
            pr_number=234,
            commit_message="Merge PR #234"
        )

        assert result["merged"] is True


class TestInfrastructureAgent:
    """Test Infrastructure agent functionality"""

    @patch('subprocess.run')
    def test_scale_instances_success(self, mock_run):
        """Test successful instance scaling"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Updated instance group",
            stderr=""
        )

        from agents.infra.agent import InfrastructureAgent

        agent = InfrastructureAgent()
        result = agent.scale_instances(
            instance_group="api-gateway-group",
            size=5,
            zone="us-central1-a"
        )

        assert result["success"] is True
        assert result["new_size"] == 5

    @patch('subprocess.run')
    def test_scale_instances_failure(self, mock_run):
        """Test instance scaling failure"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="ERROR: Instance group not found"
        )

        from agents.infra.agent import InfrastructureAgent

        agent = InfrastructureAgent()

        with pytest.raises(Exception):
            agent.scale_instances(
                instance_group="invalid-group",
                size=5
            )

    @patch('subprocess.run')
    def test_configure_autoscaling(self, mock_run):
        """Test autoscaling configuration"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Autoscaling configured",
            stderr=""
        )

        from agents.infra.agent import InfrastructureAgent

        agent = InfrastructureAgent()
        result = agent.configure_autoscaling(
            instance_group="api-gateway-group",
            min_replicas=3,
            max_replicas=8,
            target_cpu=0.7
        )

        assert result["success"] is True


class TestDataAgent:
    """Test Data Pipeline agent functionality"""

    def test_analyze_pipeline_health(self):
        """Test data pipeline health analysis"""
        from agents.data.agent import DataAgent

        agent = DataAgent()
        result = agent.analyze_pipeline_health(
            pipeline_name="user-analytics"
        )

        assert "health_status" in result
        assert result["health_status"] in ["healthy", "degraded", "down"]

    def test_validate_data_quality(self):
        """Test data quality validation"""
        from agents.data.agent import DataAgent

        agent = DataAgent()

        test_data = [
            {"user_id": "123", "name": "John Doe", "email": "john@example.com"},
            {"user_id": "124", "name": "Jane Smith", "email": "jane@example.com"}
        ]

        result = agent.validate_data_quality(test_data)

        assert "validation_passed" in result
        assert "issues" in result


class TestGCPMonitorAgent:
    """Test GCP Monitoring agent functionality"""

    @patch('google.cloud.monitoring_v3.AlertPolicyServiceClient')
    def test_create_alert_policy(self, mock_client):
        """Test creating GCP alert policy"""
        mock_instance = Mock()
        mock_instance.create_alert_policy.return_value = Mock(
            name="projects/test-project/alertPolicies/12345"
        )
        mock_client.return_value = mock_instance

        from agents.gcp_monitor.agent import GCPMonitorAgent

        agent = GCPMonitorAgent()
        result = agent.create_alert_policy(
            display_name="High CPU Alert",
            metric_type="compute.googleapis.com/instance/cpu/utilization",
            threshold=0.8
        )

        assert "name" in result

    @patch('google.cloud.monitoring_v3.MetricServiceClient')
    def test_query_metrics(self, mock_client):
        """Test querying GCP metrics"""
        mock_instance = Mock()
        mock_instance.list_time_series.return_value = [
            Mock(points=[Mock(value=Mock(double_value=0.85))])
        ]
        mock_client.return_value = mock_instance

        from agents.gcp_monitor.agent import GCPMonitorAgent

        agent = GCPMonitorAgent()
        result = agent.query_metrics(
            metric_type="compute.googleapis.com/instance/cpu/utilization",
            instance_name="api-gateway-1"
        )

        assert "values" in result
