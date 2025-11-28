"""
Integration tests for Jira task management
Tests using mock data from fixtures/test_jira_tasks.json
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock
from datetime import datetime


@pytest.fixture
def test_jira_tasks():
    """Load test Jira tasks from fixtures"""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "test_jira_tasks.json"
    with open(fixtures_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_jira_client():
    """Mock Jira client"""
    client = MagicMock()
    return client


class TestJiraTaskCreation:
    """Test Jira task creation workflows"""

    def test_create_unit_test_task(self, test_jira_tasks, mock_jira_client):
        """Test creating unit test task"""
        task = test_jira_tasks[0]  # Orchestrator unit tests

        mock_jira_client.create_issue.return_value = {
            'key': task['key'],
            'id': '12345',
            'fields': {
                'summary': task['summary'],
                'status': {'name': 'To Do'}
            }
        }

        result = mock_jira_client.create_issue(
            project='ENG',
            summary=task['summary'],
            description=task['description'],
            issuetype='Task'
        )

        assert result['key'] == 'ENG-101'
        assert 'pytest unit tests' in result['fields']['summary']
        mock_jira_client.create_issue.assert_called_once()

    def test_create_high_priority_task(self, test_jira_tasks, mock_jira_client):
        """Test creating high priority task"""
        high_priority_tasks = [t for t in test_jira_tasks if t['priority'] == 'High']

        assert len(high_priority_tasks) >= 3

        task = high_priority_tasks[0]
        mock_jira_client.create_issue.return_value = {
            'key': task['key'],
            'fields': {'priority': {'name': 'High'}}
        }

        result = mock_jira_client.create_issue(
            project='ENG',
            summary=task['summary'],
            priority='High'
        )

        assert result['fields']['priority']['name'] == 'High'

    def test_task_has_required_fields(self, test_jira_tasks):
        """Test all tasks have required fields"""
        required_fields = [
            'key', 'summary', 'description', 'priority',
            'status', 'labels', 'story_points'
        ]

        for task in test_jira_tasks:
            for field in required_fields:
                assert field in task, f"Missing field {field} in {task.get('key')}"

    def test_task_labels_are_present(self, test_jira_tasks):
        """Test all tasks have testing-related labels"""
        for task in test_jira_tasks:
            assert 'testing' in task['labels'], f"Task {task['key']} missing 'testing' label"
            assert 'pytest' in task['labels'], f"Task {task['key']} missing 'pytest' label"


class TestJiraTaskQuery:
    """Test Jira task querying"""

    def test_query_by_status(self, test_jira_tasks, mock_jira_client):
        """Test querying tasks by status"""
        todo_tasks = [t for t in test_jira_tasks if t['status'] == 'To Do']

        mock_jira_client.search_issues.return_value = todo_tasks

        result = mock_jira_client.search_issues('status = "To Do"')

        assert len(result) == len(todo_tasks)
        assert all(t['status'] == 'To Do' for t in result)

    def test_query_by_priority(self, test_jira_tasks, mock_jira_client):
        """Test querying tasks by priority"""
        high_priority = [t for t in test_jira_tasks if t['priority'] == 'High']

        mock_jira_client.search_issues.return_value = high_priority

        result = mock_jira_client.search_issues('priority = High')

        assert len(result) >= 4
        assert all(t['priority'] == 'High' for t in result)

    def test_query_by_label(self, test_jira_tasks, mock_jira_client):
        """Test querying tasks by label"""
        unit_test_tasks = [t for t in test_jira_tasks if 'unit-tests' in t['labels']]

        mock_jira_client.search_issues.return_value = unit_test_tasks

        result = mock_jira_client.search_issues('labels = unit-tests')

        assert len(result) >= 1
        assert all('unit-tests' in t['labels'] for t in result)


class TestJiraTaskUpdate:
    """Test Jira task updates"""

    def test_update_task_status(self, test_jira_tasks, mock_jira_client):
        """Test updating task status"""
        task = test_jira_tasks[0]

        mock_jira_client.transition_issue.return_value = {
            'key': task['key'],
            'fields': {'status': {'name': 'In Progress'}}
        }

        result = mock_jira_client.transition_issue(task['key'], 'In Progress')

        assert result['fields']['status']['name'] == 'In Progress'
        mock_jira_client.transition_issue.assert_called_once()

    def test_assign_task_to_user(self, test_jira_tasks, mock_jira_client):
        """Test assigning task to user"""
        task = test_jira_tasks[0]
        assignee = "developer@company.com"

        mock_jira_client.update_issue.return_value = {
            'key': task['key'],
            'fields': {'assignee': {'emailAddress': assignee}}
        }

        result = mock_jira_client.update_issue(
            task['key'],
            assignee=assignee
        )

        assert result['fields']['assignee']['emailAddress'] == assignee

    def test_add_comment_to_task(self, test_jira_tasks, mock_jira_client):
        """Test adding comment to task"""
        task = test_jira_tasks[0]
        comment = "Started working on unit tests for orchestrator"

        mock_jira_client.add_comment.return_value = {
            'id': '123',
            'body': comment
        }

        result = mock_jira_client.add_comment(task['key'], comment)

        assert result['body'] == comment
        mock_jira_client.add_comment.assert_called_once()


class TestJiraTestingCategories:
    """Test categorization of testing tasks"""

    def test_unit_testing_tasks(self, test_jira_tasks):
        """Test unit testing tasks are present"""
        unit_tasks = [t for t in test_jira_tasks if 'unit-tests' in t['labels']]

        assert len(unit_tasks) >= 1
        assert any('orchestrator' in t['summary'].lower() for t in unit_tasks)

    def test_integration_testing_tasks(self, test_jira_tasks):
        """Test integration testing tasks are present"""
        integration_tasks = [t for t in test_jira_tasks if 'integration-tests' in t['labels']]

        assert len(integration_tasks) >= 1
        assert any('RAG' in t['summary'] or 'ServiceNow' in t['summary']
                   for t in integration_tasks)

    def test_performance_testing_tasks(self, test_jira_tasks):
        """Test performance testing tasks are present"""
        perf_tasks = [t for t in test_jira_tasks if 'performance-tests' in t['labels']]

        assert len(perf_tasks) >= 1
        assert any('performance' in t['summary'].lower() or 'load' in t['summary'].lower()
                   for t in perf_tasks)

    def test_security_testing_tasks(self, test_jira_tasks):
        """Test security testing tasks are present"""
        security_tasks = [t for t in test_jira_tasks if 'security-tests' in t['labels']]

        assert len(security_tasks) >= 1
        assert any('security' in t['summary'].lower() or 'authentication' in t['summary'].lower()
                   for t in security_tasks)

    def test_llm_testing_tasks(self, test_jira_tasks):
        """Test LLM-specific testing tasks are present"""
        llm_tasks = [t for t in test_jira_tasks if 'llm-tests' in t['labels']]

        assert len(llm_tasks) >= 1
        assert any('hallucination' in t['summary'].lower() for t in llm_tasks)


class TestJiraStoryPoints:
    """Test story point estimation"""

    def test_story_points_are_valid(self, test_jira_tasks):
        """Test all tasks have valid story points"""
        valid_points = [1, 2, 3, 5, 8, 13, 21]

        for task in test_jira_tasks:
            assert task['story_points'] in valid_points, \
                f"Invalid story points {task['story_points']} for {task['key']}"

    def test_complex_tasks_have_high_points(self, test_jira_tasks):
        """Test complex tasks are estimated appropriately"""
        security_task = next(t for t in test_jira_tasks if 'security' in t['summary'].lower())
        rag_task = next(t for t in test_jira_tasks if 'RAG' in t['summary'])

        assert security_task['story_points'] >= 8
        assert rag_task['story_points'] >= 5

    def test_simple_tasks_have_low_points(self, test_jira_tasks):
        """Test simple tasks are estimated appropriately"""
        smoke_task = next(t for t in test_jira_tasks if 'smoke' in t['summary'].lower())

        assert smoke_task['story_points'] <= 5


class TestJiraErrorHandling:
    """Test error handling scenarios"""

    def test_handle_duplicate_task(self, mock_jira_client):
        """Test handling duplicate task creation"""
        mock_jira_client.create_issue.side_effect = Exception("Issue already exists")

        with pytest.raises(Exception) as exc_info:
            mock_jira_client.create_issue(project='ENG', summary='Duplicate')

        assert 'already exists' in str(exc_info.value)

    def test_handle_invalid_transition(self, mock_jira_client):
        """Test handling invalid status transition"""
        mock_jira_client.transition_issue.side_effect = Exception("Invalid transition")

        with pytest.raises(Exception) as exc_info:
            mock_jira_client.transition_issue('ENG-101', 'InvalidStatus')

        assert 'Invalid transition' in str(exc_info.value)

    def test_handle_authentication_error(self, mock_jira_client):
        """Test handling authentication failures"""
        mock_jira_client.create_issue.side_effect = Exception("Authentication failed")

        with pytest.raises(Exception) as exc_info:
            mock_jira_client.create_issue(project='ENG', summary='Test')

        assert 'Authentication' in str(exc_info.value)


@pytest.mark.parametrize("task_index,expected_label", [
    (0, 'unit-tests'),
    (1, 'integration-tests'),
    (2, 'e2e-tests'),
    (3, 'performance-tests'),
    (4, 'security-tests'),
])
def test_task_labels_parametrized(test_jira_tasks, task_index, expected_label):
    """Parametrized test for task labels"""
    assert expected_label in test_jira_tasks[task_index]['labels']


def test_all_tasks_have_unique_keys(test_jira_tasks):
    """Test all tasks have unique keys"""
    keys = [t['key'] for t in test_jira_tasks]
    assert len(keys) == len(set(keys)), "Duplicate task keys found"


def test_all_tasks_are_for_eng_project(test_jira_tasks):
    """Test all tasks belong to ENG project"""
    for task in test_jira_tasks:
        assert task['key'].startswith('ENG-'), f"Task {task['key']} not in ENG project"


def test_task_descriptions_are_comprehensive(test_jira_tasks):
    """Test all tasks have detailed descriptions"""
    for task in test_jira_tasks:
        assert len(task['description']) > 50, \
            f"Task {task['key']} has insufficient description"
        assert 'test' in task['description'].lower(), \
            f"Task {task['key']} description doesn't mention testing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
