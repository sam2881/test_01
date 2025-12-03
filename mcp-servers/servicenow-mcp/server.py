#!/usr/bin/env python3
"""
ServiceNow MCP Server
Provides MCP protocol access to ServiceNow APIs
"""
import os
import sys
import asyncio
import time
from typing import Any, Dict, List, Optional
import pysnow
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add parent directory for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.metrics import start_metrics_server, ToolMetrics, APIMetrics

# Server name and metrics port
SERVER_NAME = "servicenow-mcp"
METRICS_PORT = int(os.getenv("METRICS_PORT", "8091"))


class ServiceNowMCPServer:
    """MCP Server for ServiceNow integration"""

    def __init__(self):
        # Initialize ServiceNow client
        self.snow_instance = os.getenv("SNOW_INSTANCE_URL", "").replace("https://", "").replace("http://", "")
        self.snow_username = os.getenv("SNOW_USERNAME")
        self.snow_password = os.getenv("SNOW_PASSWORD")

        if not all([self.snow_instance, self.snow_username, self.snow_password]):
            raise ValueError("ServiceNow credentials not configured in environment")

        self.client = pysnow.Client(
            instance=self.snow_instance,
            user=self.snow_username,
            password=self.snow_password
        )

        # Create server
        self.server = Server("servicenow-mcp")

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all ServiceNow tools"""

        # Tool 1: Get Incident
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_incident",
                    description="Get a ServiceNow incident by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "incident_id": {
                                "type": "string",
                                "description": "ServiceNow incident ID (e.g., INC0010001)"
                            }
                        },
                        "required": ["incident_id"]
                    }
                ),
                Tool(
                    name="create_incident",
                    description="Create a new ServiceNow incident",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "short_description": {
                                "type": "string",
                                "description": "Brief description of the incident"
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description"
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["1", "2", "3", "4", "5"],
                                "description": "Priority: 1=Critical, 5=Planning"
                            },
                            "assigned_to": {
                                "type": "string",
                                "description": "User to assign (optional)"
                            }
                        },
                        "required": ["short_description", "description"]
                    }
                ),
                Tool(
                    name="update_incident",
                    description="Update an existing ServiceNow incident",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "incident_id": {
                                "type": "string",
                                "description": "Incident ID to update"
                            },
                            "updates": {
                                "type": "object",
                                "description": "Fields to update (e.g., {\"state\": \"6\", \"work_notes\": \"Fixed\"})"
                            }
                        },
                        "required": ["incident_id", "updates"]
                    }
                ),
                Tool(
                    name="search_incidents",
                    description="Search ServiceNow incidents by query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'short_descriptionLIKEdatabase')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max results to return",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_incident_comments",
                    description="Get all comments/work notes for an incident",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "incident_id": {
                                "type": "string",
                                "description": "Incident ID"
                            }
                        },
                        "required": ["incident_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            with ToolMetrics(SERVER_NAME, name):
                if name == "get_incident":
                    return await self._get_incident(arguments["incident_id"])

                elif name == "create_incident":
                    return await self._create_incident(
                        arguments["short_description"],
                        arguments["description"],
                        arguments.get("priority", "3"),
                        arguments.get("assigned_to")
                    )

                elif name == "update_incident":
                    return await self._update_incident(
                        arguments["incident_id"],
                        arguments["updates"]
                    )

                elif name == "search_incidents":
                    return await self._search_incidents(
                        arguments["query"],
                        arguments.get("limit", 10)
                    )

                elif name == "get_incident_comments":
                    return await self._get_incident_comments(arguments["incident_id"])

                else:
                    raise ValueError(f"Unknown tool: {name}")

    async def _get_incident(self, incident_id: str) -> List[TextContent]:
        """Get incident by ID"""
        incident_table = self.client.resource(api_path='/table/incident')

        response = incident_table.get(
            query={'number': incident_id},
            limit=1
        )

        results = list(response.all())

        if not results:
            return [TextContent(
                type="text",
                text=f"Incident {incident_id} not found"
            )]

        incident = results[0]

        text = f"""
Incident: {incident.get('number')}
State: {incident.get('state')}
Priority: {incident.get('priority')}
Short Description: {incident.get('short_description')}
Description: {incident.get('description')}
Assigned To: {incident.get('assigned_to')}
Created: {incident.get('sys_created_on')}
Updated: {incident.get('sys_updated_on')}
Work Notes: {incident.get('work_notes', 'None')}
        """.strip()

        return [TextContent(type="text", text=text)]

    async def _create_incident(
        self,
        short_description: str,
        description: str,
        priority: str = "3",
        assigned_to: Optional[str] = None
    ) -> List[TextContent]:
        """Create new incident"""
        incident_table = self.client.resource(api_path='/table/incident')

        data = {
            'short_description': short_description,
            'description': description,
            'priority': priority,
            'state': '1'  # New
        }

        if assigned_to:
            data['assigned_to'] = assigned_to

        result = incident_table.create(payload=data)

        text = f"""
Created Incident: {result['number']}
Sys ID: {result['sys_id']}
Priority: {result['priority']}
State: {result['state']}
        """.strip()

        return [TextContent(type="text", text=text)]

    async def _update_incident(
        self,
        incident_id: str,
        updates: Dict[str, Any]
    ) -> List[TextContent]:
        """Update incident"""
        incident_table = self.client.resource(api_path='/table/incident')

        # Find incident first
        response = incident_table.get(
            query={'number': incident_id},
            limit=1
        )

        results = list(response.all())
        if not results:
            return [TextContent(
                type="text",
                text=f"Incident {incident_id} not found"
            )]

        sys_id = results[0]['sys_id']

        # Update
        result = incident_table.update(
            query={'sys_id': sys_id},
            payload=updates
        )

        text = f"""
Updated Incident: {incident_id}
Fields updated: {', '.join(updates.keys())}
        """.strip()

        return [TextContent(type="text", text=text)]

    async def _search_incidents(
        self,
        query: str,
        limit: int = 10
    ) -> List[TextContent]:
        """Search incidents"""
        incident_table = self.client.resource(api_path='/table/incident')

        response = incident_table.get(
            query=query,
            limit=limit
        )

        results = list(response.all())

        if not results:
            return [TextContent(
                type="text",
                text=f"No incidents found matching: {query}"
            )]

        text_lines = [f"Found {len(results)} incidents:\n"]

        for inc in results:
            text_lines.append(
                f"- {inc.get('number')}: {inc.get('short_description')} "
                f"[Priority: {inc.get('priority')}, State: {inc.get('state')}]"
            )

        return [TextContent(type="text", text="\n".join(text_lines))]

    async def _get_incident_comments(self, incident_id: str) -> List[TextContent]:
        """Get incident comments/work notes"""
        incident_table = self.client.resource(api_path='/table/incident')

        response = incident_table.get(
            query={'number': incident_id},
            limit=1
        )

        results = list(response.all())
        if not results:
            return [TextContent(
                type="text",
                text=f"Incident {incident_id} not found"
            )]

        incident = results[0]

        text = f"""
Work Notes: {incident.get('work_notes', 'None')}
Comments: {incident.get('comments', 'None')}
Close Notes: {incident.get('close_notes', 'None')}
        """.strip()

        return [TextContent(type="text", text=text)]

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
    print(f"ServiceNow MCP Server starting (metrics on port {METRICS_PORT})")

    server = ServiceNowMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
