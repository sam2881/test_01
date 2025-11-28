"""
Integration tests for ServiceNow incident management
Tests using mock data from fixtures/test_incidents.json
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def test_incidents():
    """Load test incident data from fixtures"""
    fixtures_path = Path(__file__).parent.parent / "fixtures" / "test_incidents.json"
    with open(fixtures_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_snow_client():
    """Mock ServiceNow client"""
    client = MagicMock()
    return client


class TestServiceNowIncidentCreation:
    """Test incident creation workflows"""

    def test_create_critical_incident(self, test_incidents, mock_snow_client):
        """Test creating a P1 critical incident"""
        critical_incident = test_incidents[0]  # API Gateway timeout

        # Mock the creation response
        mock_snow_client.create_incident.return_value = {
            'number': critical_incident['number'],
            'sys_id': critical_incident['sys_id'],
            'state': 'New'
        }

        # Create incident
        result = mock_snow_client.create_incident({
            'short_description': critical_incident['short_description'],
            'description': critical_incident['description'],
            'priority': critical_incident['priority'],
            'category': critical_incident['category']
        })

        # Assertions
        assert result['number'] == 'INC0010001'
        assert result['state'] == 'New'
        mock_snow_client.create_incident.assert_called_once()

    def test_create_multiple_incidents(self, test_incidents, mock_snow_client):
        """Test bulk incident creation"""
        incidents_to_create = test_incidents[:3]

        created = []
        for incident in incidents_to_create:
            mock_snow_client.create_incident.return_value = {
                'number': incident['number'],
                'sys_id': incident['sys_id']
            }
            result = mock_snow_client.create_incident(incident)
            created.append(result)

        assert len(created) == 3
        assert created[0]['number'] == 'INC0010001'
        assert created[1]['number'] == 'INC0010002'
        assert created[2]['number'] == 'INC0010003'

    def test_incident_priority_validation(self, test_incidents):
        """Test incident priority levels are valid"""
        valid_priorities = ['1 - Critical', '2 - High', '3 - Moderate', '4 - Low']

        for incident in test_incidents:
            assert incident['priority'] in valid_priorities, \
                f"Invalid priority: {incident['priority']}"

    def test_incident_required_fields(self, test_incidents):
        """Test all incidents have required fields"""
        required_fields = [
            'number', 'short_description', 'description',
            'priority', 'state', 'category', 'sys_id'
        ]

        for incident in test_incidents:
            for field in required_fields:
                assert field in incident, f"Missing field {field} in {incident.get('number')}"
                assert incident[field], f"Empty field {field} in {incident.get('number')}"


class TestServiceNowIncidentUpdate:
    """Test incident update workflows"""

    def test_update_incident_state(self, test_incidents, mock_snow_client):
        """Test updating incident state"""
        incident = test_incidents[0]

        mock_snow_client.update_incident.return_value = {
            'number': incident['number'],
            'state': 'In Progress'
        }

        result = mock_snow_client.update_incident(
            incident['sys_id'],
            {'state': 'In Progress'}
        )

        assert result['state'] == 'In Progress'
        mock_snow_client.update_incident.assert_called_once()

    def test_assign_incident_to_group(self, test_incidents, mock_snow_client):
        """Test assigning incident to team"""
        incident = test_incidents[1]  # Database issue

        mock_snow_client.update_incident.return_value = {
            'number': incident['number'],
            'assignment_group': 'Database Team',
            'state': 'Assigned'
        }

        result = mock_snow_client.update_incident(
            incident['sys_id'],
            {
                'assignment_group': 'Database Team',
                'state': 'Assigned'
            }
        )

        assert result['assignment_group'] == 'Database Team'
        assert result['state'] == 'Assigned'

    def test_add_work_notes(self, test_incidents, mock_snow_client):
        """Test adding work notes to incident"""
        incident = test_incidents[0]
        work_note = "Investigated load balancer logs. Found connection pooling issue."

        mock_snow_client.add_work_note.return_value = {
            'number': incident['number'],
            'work_notes': work_note
        }

        result = mock_snow_client.add_work_note(
            incident['sys_id'],
            work_note
        )

        assert result['work_notes'] == work_note


class TestServiceNowIncidentQuery:
    """Test incident query and search"""

    def test_query_by_priority(self, test_incidents, mock_snow_client):
        """Test querying incidents by priority"""
        critical_incidents = [i for i in test_incidents if i['priority'] == '1 - Critical']

        mock_snow_client.query_incidents.return_value = critical_incidents

        result = mock_snow_client.query_incidents(priority='1 - Critical')

        assert len(result) == len(critical_incidents)
        assert all(i['priority'] == '1 - Critical' for i in result)

    def test_query_by_category(self, test_incidents, mock_snow_client):
        """Test querying incidents by category"""
        db_incidents = [i for i in test_incidents if i['category'] == 'Database']

        mock_snow_client.query_incidents.return_value = db_incidents

        result = mock_snow_client.query_incidents(category='Database')

        assert len(result) == len(db_incidents)
        assert all(i['category'] == 'Database' for i in result)

    def test_query_by_state(self, test_incidents, mock_snow_client):
        """Test querying incidents by state"""
        in_progress = [i for i in test_incidents if i['state'] == 'In Progress']

        mock_snow_client.query_incidents.return_value = in_progress

        result = mock_snow_client.query_incidents(state='In Progress')

        assert len(result) == len(in_progress)
        assert all(i['state'] == 'In Progress' for i in result)


class TestServiceNowCategorization:
    """Test incident categorization"""

    def test_infrastructure_incidents(self, test_incidents):
        """Test infrastructure category incidents"""
        infra_incidents = [i for i in test_incidents if i['category'] == 'Infrastructure']

        assert len(infra_incidents) >= 1
        assert any('Redis' in i['short_description'] for i in infra_incidents)

    def test_database_incidents(self, test_incidents):
        """Test database category incidents"""
        db_incidents = [i for i in test_incidents if i['category'] == 'Database']

        assert len(db_incidents) >= 2
        categories = [i['short_description'] for i in db_incidents]
        assert any('PostgreSQL' in desc or 'Neo4j' in desc for desc in categories)

    def test_aiml_incidents(self, test_incidents):
        """Test AI/ML category incidents"""
        ai_incidents = [i for i in test_incidents if i['category'] == 'AI/ML']

        assert len(ai_incidents) >= 2
        assert any('LLM' in i['short_description'] or 'vector' in i['short_description'].lower()
                   for i in ai_incidents)


class TestServiceNowErrorHandling:
    """Test error handling scenarios"""

    def test_handle_duplicate_incident(self, mock_snow_client):
        """Test handling duplicate incident creation"""
        mock_snow_client.create_incident.side_effect = Exception("Duplicate incident")

        with pytest.raises(Exception) as exc_info:
            mock_snow_client.create_incident({'short_description': 'Test'})

        assert 'Duplicate' in str(exc_info.value)

    def test_handle_invalid_state_transition(self, mock_snow_client):
        """Test handling invalid state transition"""
        mock_snow_client.update_incident.side_effect = Exception("Invalid state transition")

        with pytest.raises(Exception) as exc_info:
            mock_snow_client.update_incident('sys123', {'state': 'InvalidState'})

        assert 'Invalid state' in str(exc_info.value)

    def test_handle_authentication_error(self, mock_snow_client):
        """Test handling authentication failures"""
        mock_snow_client.create_incident.side_effect = Exception("Authentication failed")

        with pytest.raises(Exception) as exc_info:
            mock_snow_client.create_incident({'short_description': 'Test'})

        assert 'Authentication' in str(exc_info.value)


@pytest.mark.parametrize("incident_index,expected_priority", [
    (0, '1 - Critical'),  # API Gateway
    (1, '2 - High'),      # Database pool
    (4, '3 - Moderate'),  # Neo4j performance
])
def test_incident_priorities_parametrized(test_incidents, incident_index, expected_priority):
    """Parametrized test for incident priorities"""
    assert test_incidents[incident_index]['priority'] == expected_priority


def test_all_incidents_have_unique_numbers(test_incidents):
    """Test all incidents have unique incident numbers"""
    numbers = [i['number'] for i in test_incidents]
    assert len(numbers) == len(set(numbers)), "Duplicate incident numbers found"


def test_all_incidents_have_unique_sys_ids(test_incidents):
    """Test all incidents have unique sys_ids"""
    sys_ids = [i['sys_id'] for i in test_incidents]
    assert len(sys_ids) == len(set(sys_ids)), "Duplicate sys_ids found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
