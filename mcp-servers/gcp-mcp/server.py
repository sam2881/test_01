#!/usr/bin/env python3
"""
GCP MCP Server
Provides MCP protocol access to Google Cloud Platform APIs
"""
import os
import asyncio
from typing import Any, Dict, List, Optional
from google.cloud import monitoring_v3, compute_v1
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


class GCPMCPServer:
    """MCP Server for GCP integration"""

    def __init__(self):
        # Initialize GCP clients
        self.project_id = os.getenv("GCP_PROJECT_ID")
        credentials_path = os.getenv("GCP_CREDENTIALS_PATH")

        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID not configured")

        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.compute_client = compute_v1.InstancesClient()

        # Create server
        self.server = Server("gcp-mcp")

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all GCP tools"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="list_compute_instances",
                    description="List GCP Compute Engine instances",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "zone": {
                                "type": "string",
                                "description": "GCP zone (e.g., us-central1-a)"
                            }
                        },
                        "required": ["zone"]
                    }
                ),
                Tool(
                    name="get_instance_metrics",
                    description="Get metrics for a compute instance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_name": {
                                "type": "string",
                                "description": "Instance name"
                            },
                            "zone": {
                                "type": "string",
                                "description": "GCP zone"
                            },
                            "metric_type": {
                                "type": "string",
                                "enum": ["cpu", "memory", "disk", "network"],
                                "description": "Metric to retrieve"
                            }
                        },
                        "required": ["instance_name", "zone", "metric_type"]
                    }
                ),
                Tool(
                    name="create_alert_policy",
                    description="Create a monitoring alert policy",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "display_name": {
                                "type": "string",
                                "description": "Alert policy name"
                            },
                            "metric_type": {
                                "type": "string",
                                "description": "Metric type to monitor"
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Alert threshold value"
                            },
                            "notification_channel": {
                                "type": "string",
                                "description": "Notification channel ID (optional)"
                            }
                        },
                        "required": ["display_name", "metric_type", "threshold"]
                    }
                ),
                Tool(
                    name="list_alert_policies",
                    description="List all monitoring alert policies",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_time_series",
                    description="Get time series data for a metric",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metric_type": {
                                "type": "string",
                                "description": "Full metric type (e.g., compute.googleapis.com/instance/cpu/utilization)"
                            },
                            "hours": {
                                "type": "integer",
                                "description": "Hours of data to retrieve (default: 1)",
                                "default": 1
                            }
                        },
                        "required": ["metric_type"]
                    }
                ),
                Tool(
                    name="start_instance",
                    description="Start a stopped compute instance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_name": {"type": "string"},
                            "zone": {"type": "string"}
                        },
                        "required": ["instance_name", "zone"]
                    }
                ),
                Tool(
                    name="stop_instance",
                    description="Stop a running compute instance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "instance_name": {"type": "string"},
                            "zone": {"type": "string"}
                        },
                        "required": ["instance_name", "zone"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""

            if name == "list_compute_instances":
                return await self._list_compute_instances(arguments["zone"])

            elif name == "get_instance_metrics":
                return await self._get_instance_metrics(
                    arguments["instance_name"],
                    arguments["zone"],
                    arguments["metric_type"]
                )

            elif name == "create_alert_policy":
                return await self._create_alert_policy(
                    arguments["display_name"],
                    arguments["metric_type"],
                    arguments["threshold"],
                    arguments.get("notification_channel")
                )

            elif name == "list_alert_policies":
                return await self._list_alert_policies()

            elif name == "get_time_series":
                return await self._get_time_series(
                    arguments["metric_type"],
                    arguments.get("hours", 1)
                )

            elif name == "start_instance":
                return await self._start_instance(
                    arguments["instance_name"],
                    arguments["zone"]
                )

            elif name == "stop_instance":
                return await self._stop_instance(
                    arguments["instance_name"],
                    arguments["zone"]
                )

            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _list_compute_instances(self, zone: str) -> List[TextContent]:
        """List compute instances in zone"""
        try:
            request = compute_v1.ListInstancesRequest(
                project=self.project_id,
                zone=zone
            )

            instances = list(self.compute_client.list(request=request))

            if not instances:
                return [TextContent(type="text", text=f"No instances found in zone {zone}")]

            text_lines = [f"Compute Instances in {zone}:\n"]

            for instance in instances:
                status = instance.status
                text_lines.append(
                    f"- {instance.name}: {status} (Type: {instance.machine_type.split('/')[-1]})"
                )

            return [TextContent(type="text", text="\n".join(text_lines))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_instance_metrics(
        self,
        instance_name: str,
        zone: str,
        metric_type: str
    ) -> List[TextContent]:
        """Get instance metrics"""
        try:
            # Map metric type to GCP metric
            metric_map = {
                "cpu": "compute.googleapis.com/instance/cpu/utilization",
                "memory": "agent.googleapis.com/memory/percent_used",
                "disk": "compute.googleapis.com/instance/disk/read_bytes_count",
                "network": "compute.googleapis.com/instance/network/received_bytes_count"
            }

            full_metric = metric_map.get(metric_type)
            if not full_metric:
                return [TextContent(type="text", text=f"Unknown metric type: {metric_type}")]

            # Get time series data
            project_name = f"projects/{self.project_id}"

            # Build filter for specific instance
            filter_str = (
                f'metric.type="{full_metric}" '
                f'AND resource.labels.instance_name="{instance_name}" '
                f'AND resource.labels.zone="{zone}"'
            )

            # Time window (last hour)
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            end_time = now
            start_time = now - timedelta(hours=1)

            interval = monitoring_v3.TimeInterval({
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())}
            })

            results = self.monitoring_client.list_time_series(
                name=project_name,
                filter=filter_str,
                interval=interval,
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
            )

            text_lines = [f"Metrics for {instance_name} ({metric_type}):\n"]

            for result in results:
                for point in result.points[-5:]:  # Last 5 points
                    timestamp = point.interval.end_time
                    value = point.value.double_value or point.value.int64_value
                    text_lines.append(f"- {timestamp}: {value:.2f}")

            if len(text_lines) == 1:
                text_lines.append("No data available")

            return [TextContent(type="text", text="\n".join(text_lines))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _create_alert_policy(
        self,
        display_name: str,
        metric_type: str,
        threshold: float,
        notification_channel: Optional[str] = None
    ) -> List[TextContent]:
        """Create alert policy"""
        try:
            project_name = f"projects/{self.project_id}"

            condition = monitoring_v3.AlertPolicy.Condition(
                display_name=f"{display_name} - Condition",
                condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                    filter=f'metric.type="{metric_type}"',
                    comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                    threshold_value=threshold,
                    duration={"seconds": 300}  # 5 minutes
                )
            )

            policy = monitoring_v3.AlertPolicy(
                display_name=display_name,
                conditions=[condition],
                combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.AND
            )

            if notification_channel:
                policy.notification_channels = [notification_channel]

            result = self.monitoring_client.create_alert_policy(
                name=project_name,
                alert_policy=policy
            )

            text = f"Created alert policy: {result.name}"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _list_alert_policies(self) -> List[TextContent]:
        """List alert policies"""
        try:
            project_name = f"projects/{self.project_id}"

            policies = self.monitoring_client.list_alert_policies(name=project_name)

            text_lines = ["Alert Policies:\n"]

            for policy in policies:
                text_lines.append(f"- {policy.display_name} [Enabled: {policy.enabled}]")

            if len(text_lines) == 1:
                text_lines.append("No alert policies found")

            return [TextContent(type="text", text="\n".join(text_lines))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_time_series(
        self,
        metric_type: str,
        hours: int = 1
    ) -> List[TextContent]:
        """Get time series data"""
        try:
            from datetime import datetime, timedelta

            project_name = f"projects/{self.project_id}"

            now = datetime.utcnow()
            end_time = now
            start_time = now - timedelta(hours=hours)

            interval = monitoring_v3.TimeInterval({
                "end_time": {"seconds": int(end_time.timestamp())},
                "start_time": {"seconds": int(start_time.timestamp())}
            })

            results = self.monitoring_client.list_time_series(
                name=project_name,
                filter=f'metric.type="{metric_type}"',
                interval=interval
            )

            text_lines = [f"Time Series for {metric_type} (last {hours}h):\n"]

            for result in results:
                resource = result.resource.labels
                text_lines.append(f"\nResource: {resource}")

                for point in result.points[-10:]:  # Last 10 points
                    timestamp = point.interval.end_time
                    value = point.value.double_value or point.value.int64_value
                    text_lines.append(f"  {timestamp}: {value:.2f}")

            if len(text_lines) == 1:
                text_lines.append("No data available")

            return [TextContent(type="text", text="\n".join(text_lines))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _start_instance(
        self,
        instance_name: str,
        zone: str
    ) -> List[TextContent]:
        """Start compute instance"""
        try:
            request = compute_v1.StartInstanceRequest(
                project=self.project_id,
                zone=zone,
                instance=instance_name
            )

            operation = self.compute_client.start(request=request)

            text = f"Starting instance {instance_name} in {zone}"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _stop_instance(
        self,
        instance_name: str,
        zone: str
    ) -> List[TextContent]:
        """Stop compute instance"""
        try:
            request = compute_v1.StopInstanceRequest(
                project=self.project_id,
                zone=zone,
                instance=instance_name
            )

            operation = self.compute_client.stop(request=request)

            text = f"Stopping instance {instance_name} in {zone}"

            return [TextContent(type="text", text=text)]

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
    server = GCPMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
