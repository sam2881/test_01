"""GCP Monitoring Agent - Monitors GCP resources and creates ServiceNow tickets"""
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import httpx
from google.cloud import monitoring_v3
from google.cloud import compute_v1
from google.cloud import logging as gcp_logging
import structlog

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent

logger = structlog.get_logger()

app = FastAPI(title="GCP Monitoring Agent")


class GCPAlert(BaseModel):
    """GCP Alert schema"""
    incident_id: Optional[str] = None
    resource_type: str  # "compute", "storage", "database", "network", "kubernetes"
    resource_name: str
    metric_type: str
    metric_value: float
    threshold: float
    severity: str  # "critical", "high", "medium", "low"
    description: str
    project_id: str
    zone: Optional[str] = None


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    project_id: str
    check_interval: int = 60  # seconds
    metrics_to_monitor: List[str] = [
        "compute.googleapis.com/instance/cpu/utilization",
        "compute.googleapis.com/instance/disk/read_bytes_count",
        "storage.googleapis.com/network/sent_bytes_count",
        "cloudsql.googleapis.com/database/cpu/utilization"
    ]


class GCPMonitoringAgent(BaseAgent):
    """Agent for monitoring GCP resources and creating ServiceNow incidents"""

    def __init__(self):
        super().__init__(agent_name="GCPMonitoringAgent", agent_type="cloud_monitoring")

        # GCP Project Configuration
        self.project_id = os.getenv("GCP_PROJECT_ID", "")
        self.gcp_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

        # ServiceNow Agent endpoint
        self.servicenow_agent_url = os.getenv(
            "SERVICENOW_AGENT_URL",
            "http://servicenow_agent:8010/process"
        )

        # Initialize GCP clients
        try:
            self.monitoring_client = monitoring_v3.MetricServiceClient()
            self.compute_client = compute_v1.InstancesClient()
            self.logging_client = gcp_logging.Client(project=self.project_id)
            logger.info("gcp_clients_initialized", project_id=self.project_id)
        except Exception as e:
            logger.warning("gcp_client_init_failed", error=str(e))
            self.monitoring_client = None

        # Thresholds for automatic ticket creation
        self.thresholds = {
            "cpu_utilization": 85.0,  # %
            "memory_utilization": 90.0,  # %
            "disk_utilization": 85.0,  # %
            "error_rate": 5.0,  # %
            "latency_p95": 1000.0  # ms
        }

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate monitoring task input"""
        return "resource_type" in task or "metric_type" in task

    def get_compute_instances(self, zone: str = "us-central1-a") -> List[Dict[str, Any]]:
        """Get all compute instances in a zone"""
        if not self.compute_client:
            return []

        try:
            instances = []
            request = compute_v1.ListInstancesRequest(
                project=self.project_id,
                zone=zone
            )

            for instance in self.compute_client.list(request=request):
                instances.append({
                    "name": instance.name,
                    "status": instance.status,
                    "machine_type": instance.machine_type,
                    "zone": zone
                })

            logger.info("compute_instances_retrieved", count=len(instances), zone=zone)
            return instances
        except Exception as e:
            logger.error("get_instances_error", error=str(e))
            return []

    def query_metric(
        self,
        metric_type: str,
        resource_type: str,
        resource_id: str,
        minutes: int = 5
    ) -> Optional[float]:
        """Query a specific metric from Cloud Monitoring"""
        if not self.monitoring_client:
            logger.warning("monitoring_client_not_available")
            return None

        try:
            # Build time interval
            now = datetime.utcnow()
            interval = monitoring_v3.TimeInterval(
                {
                    "end_time": {"seconds": int(now.timestamp())},
                    "start_time": {"seconds": int((now - timedelta(minutes=minutes)).timestamp())},
                }
            )

            # Build metric filter
            project_name = f"projects/{self.project_id}"

            # Query the metric
            results = self.monitoring_client.list_time_series(
                request={
                    "name": project_name,
                    "filter": f'metric.type="{metric_type}" AND resource.type="{resource_type}"',
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )

            # Get the latest value
            for result in results:
                if result.points:
                    latest_point = result.points[0]
                    value = latest_point.value.double_value or latest_point.value.int64_value
                    logger.info(
                        "metric_retrieved",
                        metric=metric_type,
                        value=value,
                        resource=resource_id
                    )
                    return float(value)

            return None

        except Exception as e:
            logger.error("metric_query_error", error=str(e), metric=metric_type)
            return None

    def check_cpu_utilization(self, instance_name: str, zone: str) -> Optional[Dict[str, Any]]:
        """Check CPU utilization for a compute instance"""
        metric_type = "compute.googleapis.com/instance/cpu/utilization"
        resource_type = "gce_instance"

        cpu_usage = self.query_metric(metric_type, resource_type, instance_name)

        if cpu_usage is not None and cpu_usage > self.thresholds["cpu_utilization"]:
            return {
                "resource_type": "compute",
                "resource_name": instance_name,
                "metric_type": "cpu_utilization",
                "metric_value": cpu_usage,
                "threshold": self.thresholds["cpu_utilization"],
                "severity": "high" if cpu_usage > 95 else "medium",
                "description": f"High CPU utilization detected on {instance_name}: {cpu_usage:.2f}%",
                "project_id": self.project_id,
                "zone": zone
            }
        return None

    def check_disk_usage(self, instance_name: str, zone: str) -> Optional[Dict[str, Any]]:
        """Check disk usage for a compute instance"""
        # In a real implementation, you would query disk metrics
        # For demo purposes, returning a mock check
        return None

    def scan_gcp_resources(self) -> List[Dict[str, Any]]:
        """Scan all GCP resources for anomalies"""
        anomalies = []

        # Get all compute instances
        zones = ["us-central1-a", "us-east1-b", "europe-west1-b"]

        for zone in zones:
            instances = self.get_compute_instances(zone)

            for instance in instances:
                # Check CPU
                cpu_alert = self.check_cpu_utilization(instance["name"], zone)
                if cpu_alert:
                    anomalies.append(cpu_alert)

                # Check Disk
                disk_alert = self.check_disk_usage(instance["name"], zone)
                if disk_alert:
                    anomalies.append(disk_alert)

        logger.info("gcp_scan_complete", anomalies_found=len(anomalies))
        return anomalies

    async def create_servicenow_ticket(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create ServiceNow ticket via ServiceNow Agent"""
        try:
            async with httpx.AsyncClient() as client:
                # Call ServiceNow Agent
                response = await client.post(
                    self.servicenow_agent_url,
                    json={
                        "task_id": f"gcp-{alert['resource_name']}-{datetime.utcnow().timestamp()}",
                        "task_type": "incident",
                        "description": alert["description"],
                        "service": alert["resource_name"],
                        "priority": alert["severity"]
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        "servicenow_ticket_created",
                        resource=alert["resource_name"],
                        incident_id=result.get("result", {}).get("incident_id")
                    )
                    return result
                else:
                    logger.error("servicenow_ticket_failed", status=response.status_code)
                    return {"status": "error", "message": response.text}

        except Exception as e:
            logger.error("create_ticket_error", error=str(e))
            return {"status": "error", "message": str(e)}

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process GCP monitoring task"""
        task_type = task.get("task_type", "scan")

        if task_type == "scan":
            # Scan all resources
            anomalies = self.scan_gcp_resources()
            return {
                "anomalies_found": len(anomalies),
                "anomalies": anomalies
            }

        elif task_type == "alert":
            # Process specific alert
            alert = task.get("alert", {})
            return {
                "alert_processed": True,
                "alert": alert
            }

        else:
            raise ValueError(f"Unknown task type: {task_type}")


# Global agent instance
agent = GCPMonitoringAgent()


@app.post("/scan")
async def scan_resources(background_tasks: BackgroundTasks):
    """Scan GCP resources and create tickets for anomalies"""
    try:
        # Scan resources
        anomalies = agent.scan_gcp_resources()

        # Create ServiceNow tickets for critical anomalies
        tickets_created = []
        for anomaly in anomalies:
            if anomaly["severity"] in ["critical", "high"]:
                # Create ticket in background
                ticket = await agent.create_servicenow_ticket(anomaly)
                tickets_created.append({
                    "resource": anomaly["resource_name"],
                    "ticket": ticket
                })

        return {
            "status": "success",
            "anomalies_found": len(anomalies),
            "tickets_created": len(tickets_created),
            "anomalies": anomalies,
            "tickets": tickets_created
        }

    except Exception as e:
        logger.error("scan_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alert")
async def process_alert(alert: GCPAlert):
    """Process incoming GCP alert and create ServiceNow ticket"""
    try:
        logger.info("gcp_alert_received", resource=alert.resource_name, severity=alert.severity)

        # Create ServiceNow ticket
        ticket = await agent.create_servicenow_ticket(alert.dict())

        return {
            "status": "success",
            "alert": alert.dict(),
            "ticket": ticket
        }

    except Exception as e:
        logger.error("alert_processing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/monitor/start")
async def start_monitoring(config: MonitoringConfig):
    """Start continuous monitoring of GCP resources"""
    # In production, this would start a background task
    return {
        "status": "started",
        "project_id": config.project_id,
        "check_interval": config.check_interval,
        "message": "Monitoring started successfully"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "GCPMonitoringAgent",
        "project_id": agent.project_id,
        "monitoring_enabled": agent.monitoring_client is not None
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8015)
