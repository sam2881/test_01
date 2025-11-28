#!/usr/bin/env python3
"""
Jira Client - Fetches tickets/stories from Jira
Integrates with the Code Agent for automated development
"""

import os
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()

# Configuration
JIRA_URL = os.getenv('JIRA_URL', 'https://your-domain.atlassian.net')
JIRA_USERNAME = os.getenv('JIRA_USERNAME', '')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN', '')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY', 'ENG')


class JiraClient:
    """Client for interacting with Jira API"""

    def __init__(self):
        self.base_url = JIRA_URL.rstrip('/')
        self.auth = HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        logger.info("jira_client_initialized", url=self.base_url, project=JIRA_PROJECT_KEY)

    def _make_request(self, method: str, endpoint: str, params: Dict = None, json_data: Dict = None) -> Optional[Dict]:
        """Make API request to Jira"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=30
            )

            if response.status_code in [200, 201, 204]:
                return response.json() if response.text else {}
            else:
                logger.error("jira_api_error",
                           status=response.status_code,
                           response=response.text[:500])
                return None

        except Exception as e:
            logger.error("jira_request_error", error=str(e))
            return None

    def get_all_tickets(self, project_key: str = None, max_results: int = 50) -> List[Dict]:
        """Get all tickets from a project"""
        project = project_key or JIRA_PROJECT_KEY

        jql = f'project = {project} ORDER BY created DESC'

        result = self._make_request(
            'GET',
            '/rest/api/3/search',
            params={
                'jql': jql,
                'maxResults': max_results,
                'fields': 'summary,description,status,priority,assignee,reporter,created,updated,issuetype,labels'
            }
        )

        if result and 'issues' in result:
            tickets = []
            for issue in result['issues']:
                tickets.append(self._format_ticket(issue))
            logger.info("jira_tickets_fetched", count=len(tickets))
            return tickets

        return []

    def get_stories(self, project_key: str = None, status: str = None, max_results: int = 50) -> List[Dict]:
        """Get user stories from Jira"""
        project = project_key or JIRA_PROJECT_KEY

        jql = f'project = {project} AND issuetype = Story'
        if status:
            jql += f' AND status = "{status}"'
        jql += ' ORDER BY created DESC'

        result = self._make_request(
            'GET',
            '/rest/api/3/search',
            params={
                'jql': jql,
                'maxResults': max_results,
                'fields': 'summary,description,status,priority,assignee,reporter,created,updated,labels,customfield_10016'
            }
        )

        if result and 'issues' in result:
            stories = []
            for issue in result['issues']:
                stories.append(self._format_ticket(issue))
            logger.info("jira_stories_fetched", count=len(stories))
            return stories

        return []

    def get_tasks_for_development(self, project_key: str = None, max_results: int = 20) -> List[Dict]:
        """Get tasks ready for development (To Do or In Progress)"""
        project = project_key or JIRA_PROJECT_KEY

        jql = f'''project = {project}
                  AND (issuetype = Story OR issuetype = Task OR issuetype = Bug)
                  AND status in ("To Do", "In Progress", "Open", "Selected for Development")
                  ORDER BY priority DESC, created ASC'''

        result = self._make_request(
            'GET',
            '/rest/api/3/search',
            params={
                'jql': jql.replace('\n', ' '),
                'maxResults': max_results,
                'fields': 'summary,description,status,priority,assignee,reporter,created,updated,issuetype,labels,acceptance'
            }
        )

        if result and 'issues' in result:
            tasks = []
            for issue in result['issues']:
                tasks.append(self._format_ticket(issue))
            logger.info("jira_dev_tasks_fetched", count=len(tasks))
            return tasks

        return []

    def get_ticket_by_key(self, ticket_key: str) -> Optional[Dict]:
        """Get a specific ticket by its key"""
        result = self._make_request(
            'GET',
            f'/rest/api/3/issue/{ticket_key}',
            params={
                'fields': 'summary,description,status,priority,assignee,reporter,created,updated,issuetype,labels,comment,attachment'
            }
        )

        if result:
            return self._format_ticket(result)
        return None

    def _format_ticket(self, issue: Dict) -> Dict:
        """Format Jira issue into a standardized ticket format"""
        fields = issue.get('fields', {})

        # Extract description text
        description = ''
        if fields.get('description'):
            desc = fields['description']
            if isinstance(desc, dict):
                # Atlassian Document Format
                description = self._extract_text_from_adf(desc)
            else:
                description = str(desc)

        # Extract assignee
        assignee = None
        if fields.get('assignee'):
            assignee = {
                'name': fields['assignee'].get('displayName', ''),
                'email': fields['assignee'].get('emailAddress', '')
            }

        # Extract reporter
        reporter = None
        if fields.get('reporter'):
            reporter = {
                'name': fields['reporter'].get('displayName', ''),
                'email': fields['reporter'].get('emailAddress', '')
            }

        return {
            'ticket_id': issue.get('key'),
            'jira_id': issue.get('id'),
            'summary': fields.get('summary', ''),
            'description': description,
            'status': fields.get('status', {}).get('name', 'Unknown'),
            'status_category': fields.get('status', {}).get('statusCategory', {}).get('name', ''),
            'priority': fields.get('priority', {}).get('name', 'Medium') if fields.get('priority') else 'Medium',
            'issue_type': fields.get('issuetype', {}).get('name', 'Task'),
            'assignee': assignee,
            'reporter': reporter,
            'labels': fields.get('labels', []),
            'created': fields.get('created', ''),
            'updated': fields.get('updated', ''),
            'url': f"{self.base_url}/browse/{issue.get('key')}"
        }

    def _extract_text_from_adf(self, adf: Dict) -> str:
        """Extract plain text from Atlassian Document Format"""
        text_parts = []

        def extract_content(node):
            if isinstance(node, dict):
                if node.get('type') == 'text':
                    text_parts.append(node.get('text', ''))
                if 'content' in node:
                    for child in node['content']:
                        extract_content(child)
            elif isinstance(node, list):
                for item in node:
                    extract_content(item)

        extract_content(adf)
        return '\n'.join(text_parts)

    def add_comment(self, ticket_key: str, comment: str) -> bool:
        """Add a comment to a ticket"""
        result = self._make_request(
            'POST',
            f'/rest/api/3/issue/{ticket_key}/comment',
            json_data={
                'body': {
                    'type': 'doc',
                    'version': 1,
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [
                                {
                                    'type': 'text',
                                    'text': comment
                                }
                            ]
                        }
                    ]
                }
            }
        )

        if result:
            logger.info("jira_comment_added", ticket=ticket_key)
            return True
        return False

    def update_ticket_status(self, ticket_key: str, transition_name: str) -> bool:
        """Update ticket status using a transition"""
        # First get available transitions
        transitions = self._make_request(
            'GET',
            f'/rest/api/3/issue/{ticket_key}/transitions'
        )

        if not transitions or 'transitions' not in transitions:
            return False

        # Find the transition
        transition_id = None
        for t in transitions['transitions']:
            if t['name'].lower() == transition_name.lower():
                transition_id = t['id']
                break

        if not transition_id:
            logger.warning("jira_transition_not_found",
                         ticket=ticket_key,
                         transition=transition_name)
            return False

        # Execute transition
        result = self._make_request(
            'POST',
            f'/rest/api/3/issue/{ticket_key}/transitions',
            json_data={'transition': {'id': transition_id}}
        )

        logger.info("jira_status_updated", ticket=ticket_key, transition=transition_name)
        return True

    def create_ticket(self, summary: str, description: str, issue_type: str = 'Task',
                     priority: str = 'Medium', labels: List[str] = None) -> Optional[Dict]:
        """Create a new Jira ticket"""
        result = self._make_request(
            'POST',
            '/rest/api/3/issue',
            json_data={
                'fields': {
                    'project': {'key': JIRA_PROJECT_KEY},
                    'summary': summary,
                    'description': {
                        'type': 'doc',
                        'version': 1,
                        'content': [
                            {
                                'type': 'paragraph',
                                'content': [{'type': 'text', 'text': description}]
                            }
                        ]
                    },
                    'issuetype': {'name': issue_type},
                    'priority': {'name': priority},
                    'labels': labels or []
                }
            }
        )

        if result:
            logger.info("jira_ticket_created", key=result.get('key'))
            return self.get_ticket_by_key(result.get('key'))
        return None


# Mock data for when Jira is not configured
MOCK_JIRA_TICKETS = [
    {
        'ticket_id': 'ENG-101',
        'jira_id': '10001',
        'summary': 'Write unit tests for user authentication module',
        'description': '''Create comprehensive unit tests for the authentication module in the backend.

Requirements:
- Test login functionality with valid/invalid credentials
- Test JWT token generation and validation
- Test password reset flow
- Test session management
- Achieve minimum 80% code coverage

Repository: https://github.com/sam2881/multiagent
File: backend/auth/auth_service.py''',
        'status': 'To Do',
        'status_category': 'To Do',
        'priority': 'High',
        'issue_type': 'Story',
        'assignee': {'name': 'AI Code Agent', 'email': 'code-agent@ai.com'},
        'reporter': {'name': 'Product Owner', 'email': 'po@company.com'},
        'labels': ['testing', 'backend', 'auth'],
        'created': '2025-11-24T10:00:00.000Z',
        'updated': '2025-11-24T10:00:00.000Z',
        'url': 'https://jira.example.com/browse/ENG-101'
    },
    {
        'ticket_id': 'ENG-102',
        'jira_id': '10002',
        'summary': 'Implement API rate limiting middleware',
        'description': '''Add rate limiting to protect API endpoints from abuse.

Acceptance Criteria:
- Implement sliding window rate limiting
- Configure limits per endpoint
- Return proper 429 responses
- Add Redis-based tracking
- Include bypass for internal services

Repository: https://github.com/sam2881/multiagent
File: backend/middleware/rate_limiter.py''',
        'status': 'In Progress',
        'status_category': 'In Progress',
        'priority': 'High',
        'issue_type': 'Task',
        'assignee': {'name': 'AI Code Agent', 'email': 'code-agent@ai.com'},
        'reporter': {'name': 'Tech Lead', 'email': 'tech@company.com'},
        'labels': ['backend', 'security', 'middleware'],
        'created': '2025-11-23T14:00:00.000Z',
        'updated': '2025-11-24T09:00:00.000Z',
        'url': 'https://jira.example.com/browse/ENG-102'
    },
    {
        'ticket_id': 'ENG-103',
        'jira_id': '10003',
        'summary': 'Create integration tests for ServiceNow API',
        'description': '''Write integration tests for the ServiceNow incident management integration.

Test Cases:
- Test incident creation
- Test incident update
- Test incident retrieval
- Test error handling
- Mock ServiceNow responses

Repository: https://github.com/sam2881/multiagent
File: backend/integrations/servicenow_client.py''',
        'status': 'To Do',
        'status_category': 'To Do',
        'priority': 'Medium',
        'issue_type': 'Task',
        'assignee': None,
        'reporter': {'name': 'QA Lead', 'email': 'qa@company.com'},
        'labels': ['testing', 'integration', 'servicenow'],
        'created': '2025-11-22T11:00:00.000Z',
        'updated': '2025-11-22T11:00:00.000Z',
        'url': 'https://jira.example.com/browse/ENG-103'
    },
    {
        'ticket_id': 'ENG-104',
        'jira_id': '10004',
        'summary': 'Add error boundary components to React frontend',
        'description': '''Implement error boundary components to gracefully handle React errors.

Requirements:
- Create reusable ErrorBoundary component
- Add fallback UI for errors
- Log errors to monitoring service
- Add retry functionality
- Cover critical user flows

Repository: https://github.com/sam2881/multiagent
File: frontend/src/components/ErrorBoundary.tsx''',
        'status': 'To Do',
        'status_category': 'To Do',
        'priority': 'Medium',
        'issue_type': 'Story',
        'assignee': None,
        'reporter': {'name': 'Frontend Lead', 'email': 'frontend@company.com'},
        'labels': ['frontend', 'react', 'error-handling'],
        'created': '2025-11-21T16:00:00.000Z',
        'updated': '2025-11-21T16:00:00.000Z',
        'url': 'https://jira.example.com/browse/ENG-104'
    },
    {
        'ticket_id': 'ENG-105',
        'jira_id': '10005',
        'summary': 'Fix database connection pooling issues',
        'description': '''Investigate and fix connection pool exhaustion under high load.

Bug Details:
- Connections not being returned to pool
- Timeout errors during peak traffic
- Memory leak suspected

Steps to reproduce:
1. Run load test with 100 concurrent users
2. Observe connection count growing
3. Eventually fails with connection timeout

Repository: https://github.com/sam2881/multiagent
File: backend/db/connection_pool.py''',
        'status': 'In Progress',
        'status_category': 'In Progress',
        'priority': 'Critical',
        'issue_type': 'Bug',
        'assignee': {'name': 'Senior Dev', 'email': 'senior@company.com'},
        'reporter': {'name': 'DevOps', 'email': 'devops@company.com'},
        'labels': ['bug', 'database', 'performance'],
        'created': '2025-11-24T08:00:00.000Z',
        'updated': '2025-11-24T12:00:00.000Z',
        'url': 'https://jira.example.com/browse/ENG-105'
    }
]


def get_jira_client() -> JiraClient:
    """Get Jira client instance"""
    return JiraClient()


def get_mock_tickets() -> List[Dict]:
    """Get mock Jira tickets for demo"""
    return MOCK_JIRA_TICKETS


if __name__ == '__main__':
    # Test the client
    client = JiraClient()

    print("Testing Jira Connection...")
    tickets = client.get_all_tickets(max_results=5)

    if tickets:
        print(f"✅ Connected! Found {len(tickets)} tickets")
        for t in tickets:
            print(f"  - {t['ticket_id']}: {t['summary'][:50]}...")
    else:
        print("⚠️ Could not fetch tickets. Using mock data...")
        for t in MOCK_JIRA_TICKETS:
            print(f"  - {t['ticket_id']}: {t['summary'][:50]}...")
