"""
Shared Prometheus Metrics for MCP Servers
"""
import time
import threading
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY
)

# Tool call metrics
MCP_TOOL_CALLS = Counter(
    'mcp_tool_calls_total',
    'Total MCP tool calls',
    ['server', 'tool', 'status']
)

MCP_TOOL_LATENCY = Histogram(
    'mcp_tool_latency_seconds',
    'MCP tool call latency',
    ['server', 'tool'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

MCP_TOOL_ERRORS = Counter(
    'mcp_tool_errors_total',
    'Total MCP tool errors',
    ['server', 'tool', 'error_type']
)

# Server status
MCP_SERVER_UP = Gauge(
    'mcp_server_up',
    'MCP server status (1=up, 0=down)',
    ['server']
)

MCP_SERVER_START_TIME = Gauge(
    'mcp_server_start_time_seconds',
    'MCP server start time in seconds since epoch',
    ['server']
)

# API call metrics (for external APIs like ServiceNow, GitHub, etc.)
MCP_API_CALLS = Counter(
    'mcp_api_calls_total',
    'Total external API calls',
    ['server', 'api', 'endpoint', 'status']
)

MCP_API_LATENCY = Histogram(
    'mcp_api_latency_seconds',
    'External API call latency',
    ['server', 'api', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint"""

    def log_message(self, format, *args):
        """Suppress HTTP logging"""
        pass

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest(REGISTRY))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()


def start_metrics_server(port: int, server_name: str):
    """Start a background HTTP server for Prometheus metrics"""

    # Mark server as up
    MCP_SERVER_UP.labels(server=server_name).set(1)
    MCP_SERVER_START_TIME.labels(server=server_name).set(time.time())

    def run_server():
        server = HTTPServer(('0.0.0.0', port), MetricsHandler)
        server.serve_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    print(f"Metrics server started on port {port}")
    return thread


class ToolMetrics:
    """Context manager for tracking tool call metrics"""

    def __init__(self, server_name: str, tool_name: str):
        self.server_name = server_name
        self.tool_name = tool_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type is None:
            MCP_TOOL_CALLS.labels(
                server=self.server_name,
                tool=self.tool_name,
                status='success'
            ).inc()
        else:
            MCP_TOOL_CALLS.labels(
                server=self.server_name,
                tool=self.tool_name,
                status='error'
            ).inc()
            MCP_TOOL_ERRORS.labels(
                server=self.server_name,
                tool=self.tool_name,
                error_type=exc_type.__name__ if exc_type else 'unknown'
            ).inc()

        MCP_TOOL_LATENCY.labels(
            server=self.server_name,
            tool=self.tool_name
        ).observe(duration)

        # Don't suppress exceptions
        return False


class APIMetrics:
    """Context manager for tracking external API call metrics"""

    def __init__(self, server_name: str, api_name: str, endpoint: str):
        self.server_name = server_name
        self.api_name = api_name
        self.endpoint = endpoint
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status = 'success' if exc_type is None else 'error'

        MCP_API_CALLS.labels(
            server=self.server_name,
            api=self.api_name,
            endpoint=self.endpoint,
            status=status
        ).inc()

        MCP_API_LATENCY.labels(
            server=self.server_name,
            api=self.api_name,
            endpoint=self.endpoint
        ).observe(duration)

        return False


def record_tool_call(server: str, tool: str, status: str = 'success', duration: float = 0):
    """Record a tool call metric"""
    MCP_TOOL_CALLS.labels(server=server, tool=tool, status=status).inc()
    if duration > 0:
        MCP_TOOL_LATENCY.labels(server=server, tool=tool).observe(duration)


def record_api_call(server: str, api: str, endpoint: str, status: str = 'success', duration: float = 0):
    """Record an external API call metric"""
    MCP_API_CALLS.labels(server=server, api=api, endpoint=endpoint, status=status).inc()
    if duration > 0:
        MCP_API_LATENCY.labels(server=server, api=api, endpoint=endpoint).observe(duration)
