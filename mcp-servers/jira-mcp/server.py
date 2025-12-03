#!/usr/bin/env python3
"""
Jira MCP Server
Provides MCP protocol access to Jira APIs
"""
import os
import sys
import asyncio
import time
from typing import Any, Dict, List, Optional
from jira import JIRA
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add parent directory for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.metrics import start_metrics_server, ToolMetrics, APIMetrics

# Server name and metrics port
SERVER_NAME = "jira-mcp"
METRICS_PORT = int(os.getenv("METRICS_PORT", "8093"))


class JiraMCPServer:
    """MCP Server for Jira integration"""

    def __init__(self):
        # Initialize Jira client
        self.jira_url = os.getenv("JIRA_URL")
        self.jira_username = os.getenv("JIRA_USERNAME")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN")

        if not all([self.jira_url, self.jira_username, self.jira_api_token]):
            raise ValueError("Jira credentials not configured in environment")

        self.client = JIRA(
            server=self.jira_url,
            basic_auth=(self.jira_username, self.jira_api_token)
        )

        # Create server
        self.server = Server("jira-mcp")

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all Jira tools"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_issue",
                    description="Get a Jira issue by key",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Jira issue key (e.g., ENG-123)"
                            }
                        },
                        "required": ["issue_key"]
                    }
                ),
                Tool(
                    name="create_story",
                    description="Create a new Jira story",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key (e.g., ENG)"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Story title/summary"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description"
                            },
                            "story_points": {
                                "type": "integer",
                                "description": "Story points (optional)"
                            }
                        },
                        "required": ["project_key", "summary", "description"]
                    }
                ),
                Tool(
                    name="create_task",
                    description="Create a new Jira task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Task title"
                            },
                            "description": {
                                "type": "string",
                                "description": "Task description"
                            },
                            "parent_key": {
                                "type": "string",
                                "description": "Parent story key (optional)"
                            }
                        },
                        "required": ["project_key", "summary"]
                    }
                ),
                Tool(
                    name="add_comment",
                    description="Add a comment to a Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key"
                            },
                            "comment": {
                                "type": "string",
                                "description": "Comment text"
                            }
                        },
                        "required": ["issue_key", "comment"]
                    }
                ),
                Tool(
                    name="transition_issue",
                    description="Transition issue to a new status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key"
                            },
                            "transition": {
                                "type": "string",
                                "description": "Transition name (e.g., 'Done', 'In Progress')"
                            }
                        },
                        "required": ["issue_key", "transition"]
                    }
                ),
                Tool(
                    name="search_issues",
                    description="Search Jira issues with JQL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "jql": {
                                "type": "string",
                                "description": "JQL query (e.g., 'project=ENG AND status=Open')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Max results",
                                "default": 50
                            }
                        },
                        "required": ["jql"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            with ToolMetrics(SERVER_NAME, name):
                if name == "get_issue":
                    return await self._get_issue(arguments["issue_key"])

                elif name == "create_story":
                    return await self._create_story(
                        arguments["project_key"],
                        arguments["summary"],
                        arguments["description"],
                        arguments.get("story_points")
                    )

                elif name == "create_task":
                    return await self._create_task(
                        arguments["project_key"],
                        arguments["summary"],
                        arguments.get("description", ""),
                        arguments.get("parent_key")
                    )

                elif name == "add_comment":
                    return await self._add_comment(
                        arguments["issue_key"],
                        arguments["comment"]
                    )

                elif name == "transition_issue":
                    return await self._transition_issue(
                        arguments["issue_key"],
                        arguments["transition"]
                    )

                elif name == "search_issues":
                    return await self._search_issues(
                        arguments["jql"],
                        arguments.get("max_results", 50)
                    )

                else:
                    raise ValueError(f"Unknown tool: {name}")

    async def _get_issue(self, issue_key: str) -> List[TextContent]:
        """Get issue by key"""
        try:
            issue = self.client.issue(issue_key)

            text = f"""
Issue: {issue.key}
Type: {issue.fields.issuetype.name}
Status: {issue.fields.status.name}
Summary: {issue.fields.summary}
Description: {issue.fields.description or 'None'}
Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'}
Reporter: {issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown'}
Created: {issue.fields.created}
Updated: {issue.fields.updated}
            """.strip()

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _create_story(
        self,
        project_key: str,
        summary: str,
        description: str,
        story_points: Optional[int] = None
    ) -> List[TextContent]:
        """Create new story"""
        try:
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': 'Story'}
            }

            if story_points:
                issue_dict['customfield_10016'] = story_points  # Story points field

            issue = self.client.create_issue(fields=issue_dict)

            text = f"""
Created Story: {issue.key}
Summary: {summary}
URL: {self.jira_url}/browse/{issue.key}
            """.strip()

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _create_task(
        self,
        project_key: str,
        summary: str,
        description: str = "",
        parent_key: Optional[str] = None
    ) -> List[TextContent]:
        """Create new task"""
        try:
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': 'Task'}
            }

            if parent_key:
                issue_dict['parent'] = {'key': parent_key}

            issue = self.client.create_issue(fields=issue_dict)

            text = f"""
Created Task: {issue.key}
Summary: {summary}
Parent: {parent_key or 'None'}
URL: {self.jira_url}/browse/{issue.key}
            """.strip()

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _add_comment(self, issue_key: str, comment: str) -> List[TextContent]:
        """Add comment to issue"""
        try:
            self.client.add_comment(issue_key, comment)

            text = f"Comment added to {issue_key}"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _transition_issue(
        self,
        issue_key: str,
        transition: str
    ) -> List[TextContent]:
        """Transition issue to new status"""
        try:
            # Find transition ID
            transitions = self.client.transitions(issue_key)
            transition_id = None

            for t in transitions:
                if t['name'].lower() == transition.lower():
                    transition_id = t['id']
                    break

            if not transition_id:
                available = ', '.join([t['name'] for t in transitions])
                return [TextContent(
                    type="text",
                    text=f"Transition '{transition}' not found. Available: {available}"
                )]

            self.client.transition_issue(issue_key, transition_id)

            text = f"Transitioned {issue_key} to {transition}"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _search_issues(
        self,
        jql: str,
        max_results: int = 50
    ) -> List[TextContent]:
        """Search issues with JQL"""
        try:
            issues = self.client.search_issues(jql, maxResults=max_results)

            if not issues:
                return [TextContent(type="text", text=f"No issues found for: {jql}")]

            text_lines = [f"Found {len(issues)} issues:\n"]

            for issue in issues:
                text_lines.append(
                    f"- {issue.key}: {issue.fields.summary} "
                    f"[{issue.fields.status.name}]"
                )

            return [TextContent(type="text", text="\n".join(text_lines))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    # Start metrics server in background
    start_metrics_server(METRICS_PORT, SERVER_NAME)
    print(f"Jira MCP Server starting (metrics on port {METRICS_PORT})")

    server = JiraMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
