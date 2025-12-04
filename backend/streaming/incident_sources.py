"""
Multi-source Incident Connectors

Unified incident ingestion from multiple monitoring sources:
- ServiceNow (existing)
- GCP Monitoring (existing)
- Datadog
- Prometheus/AlertManager
- AWS CloudWatch
- PagerDuty

All sources normalize to a common incident format.
"""

import os
import json
import hmac
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import httpx
import structlog

logger = structlog.get_logger()


class IncidentSeverity(Enum):
    """Normalized severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(Enum):
    """Normalized incident statuses"""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class NormalizedIncident:
    """
    Unified incident format for all sources.

    All source connectors normalize their data to this format.
    """
    incident_id: str
    source: str  # servicenow, gcp, datadog, prometheus, cloudwatch, pagerduty
    source_incident_id: str

    title: str
    description: str

    severity: str
    status: str

    # Categorization
    category: str = "unknown"
    subcategory: str = ""
    service: str = ""
    environment: str = ""

    # Affected resources
    resource_type: str = ""
    resource_id: str = ""
    cloud_provider: str = ""
    region: str = ""

    # Metrics/Details
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0

    # Timing
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""
    resolved_at: str = ""

    # Raw data for reference
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_kafka_message(self) -> Dict[str, Any]:
        """Format for Kafka publishing"""
        return {
            "incident_id": self.incident_id,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "category": self.category,
            "service": self.service,
            "environment": self.environment,
            "resource_type": self.resource_type,
            "cloud_provider": self.cloud_provider,
            "created_at": self.created_at,
            "metadata": {
                "source_incident_id": self.source_incident_id,
                "metric_name": self.metric_name,
                "metric_value": self.metric_value,
                "region": self.region
            }
        }


class IncidentSourceConnector(ABC):
    """Base class for incident source connectors"""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source name"""
        pass

    @abstractmethod
    def normalize_incident(self, raw_data: Dict[str, Any]) -> NormalizedIncident:
        """Normalize raw incident data to unified format"""
        pass

    @abstractmethod
    def validate_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Validate incoming webhook authenticity"""
        pass


class DatadogConnector(IncidentSourceConnector):
    """
    Datadog incident connector.

    Handles webhooks from Datadog monitors and events.
    """

    def __init__(self):
        self.api_key = os.getenv("DATADOG_API_KEY", "")
        self.app_key = os.getenv("DATADOG_APP_KEY", "")

    @property
    def source_name(self) -> str:
        return "datadog"

    def normalize_incident(self, raw_data: Dict[str, Any]) -> NormalizedIncident:
        """Normalize Datadog alert to unified format"""
        # Map Datadog alert status to severity
        alert_type = raw_data.get("alert_type", "").lower()
        severity_map = {
            "error": IncidentSeverity.HIGH.value,
            "warning": IncidentSeverity.MEDIUM.value,
            "info": IncidentSeverity.LOW.value,
            "success": IncidentSeverity.INFO.value
        }

        # Extract host/service info
        tags = raw_data.get("tags", "")
        if isinstance(tags, str):
            tags = tags.split(",")

        service = ""
        environment = ""
        for tag in tags:
            if tag.startswith("service:"):
                service = tag.split(":")[1]
            elif tag.startswith("env:"):
                environment = tag.split(":")[1]

        return NormalizedIncident(
            incident_id=f"dd_{raw_data.get('id', raw_data.get('alert_id', 'unknown'))}",
            source=self.source_name,
            source_incident_id=str(raw_data.get("alert_id", raw_data.get("id", ""))),
            title=raw_data.get("title", raw_data.get("alert_title", "Datadog Alert")),
            description=raw_data.get("body", raw_data.get("alert_body", "")),
            severity=severity_map.get(alert_type, IncidentSeverity.MEDIUM.value),
            status=IncidentStatus.NEW.value,
            category=raw_data.get("alert_type", "monitoring"),
            service=service,
            environment=environment,
            metric_name=raw_data.get("alert_metric", ""),
            resource_type=raw_data.get("host", ""),
            raw_data=raw_data
        )

    def validate_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Validate Datadog webhook signature"""
        # Datadog uses a simple token validation
        token = headers.get("DD-WEBHOOK-TOKEN", "")
        expected = os.getenv("DATADOG_WEBHOOK_TOKEN", "")
        return hmac.compare_digest(token, expected) if expected else True


class PrometheusConnector(IncidentSourceConnector):
    """
    Prometheus/AlertManager connector.

    Handles webhooks from AlertManager.
    """

    @property
    def source_name(self) -> str:
        return "prometheus"

    def normalize_incident(self, raw_data: Dict[str, Any]) -> NormalizedIncident:
        """Normalize Prometheus/AlertManager alert to unified format"""
        alerts = raw_data.get("alerts", [raw_data])
        if not alerts:
            alerts = [raw_data]

        alert = alerts[0]  # Process first alert
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        # Map AlertManager severity
        severity = labels.get("severity", "warning").lower()
        severity_map = {
            "critical": IncidentSeverity.CRITICAL.value,
            "high": IncidentSeverity.HIGH.value,
            "warning": IncidentSeverity.MEDIUM.value,
            "info": IncidentSeverity.LOW.value
        }

        # Map status
        status = alert.get("status", "firing")
        status_map = {
            "firing": IncidentStatus.NEW.value,
            "resolved": IncidentStatus.RESOLVED.value
        }

        return NormalizedIncident(
            incident_id=f"prom_{labels.get('alertname', 'unknown')}_{int(datetime.now().timestamp())}",
            source=self.source_name,
            source_incident_id=alert.get("fingerprint", ""),
            title=labels.get("alertname", "Prometheus Alert"),
            description=annotations.get("description", annotations.get("summary", "")),
            severity=severity_map.get(severity, IncidentSeverity.MEDIUM.value),
            status=status_map.get(status, IncidentStatus.NEW.value),
            category=labels.get("category", "infrastructure"),
            service=labels.get("service", labels.get("job", "")),
            environment=labels.get("env", labels.get("environment", "")),
            resource_type=labels.get("instance", ""),
            metric_name=labels.get("alertname", ""),
            raw_data=raw_data
        )

    def validate_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """AlertManager typically uses basic auth or no auth"""
        # Add authentication as needed
        return True


class CloudWatchConnector(IncidentSourceConnector):
    """
    AWS CloudWatch connector.

    Handles SNS notifications from CloudWatch Alarms.
    """

    @property
    def source_name(self) -> str:
        return "cloudwatch"

    def normalize_incident(self, raw_data: Dict[str, Any]) -> NormalizedIncident:
        """Normalize CloudWatch alarm to unified format"""
        # CloudWatch SNS notifications have a specific structure
        message = raw_data.get("Message", "{}")
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except:
                message = {"AlarmDescription": message}

        alarm_name = message.get("AlarmName", raw_data.get("AlarmName", "CloudWatch Alarm"))
        new_state = message.get("NewStateValue", "ALARM")

        # Map CloudWatch state to severity
        severity_map = {
            "ALARM": IncidentSeverity.HIGH.value,
            "INSUFFICIENT_DATA": IncidentSeverity.MEDIUM.value,
            "OK": IncidentSeverity.INFO.value
        }

        # Extract dimension info
        trigger = message.get("Trigger", {})
        dimensions = trigger.get("Dimensions", [])
        resource_id = ""
        service = ""
        for dim in dimensions:
            name = dim.get("name", dim.get("Name", ""))
            value = dim.get("value", dim.get("Value", ""))
            if name in ["InstanceId", "DBInstanceIdentifier"]:
                resource_id = value
            elif name in ["ServiceName", "FunctionName"]:
                service = value

        return NormalizedIncident(
            incident_id=f"cw_{alarm_name}_{int(datetime.now().timestamp())}",
            source=self.source_name,
            source_incident_id=message.get("AlarmArn", alarm_name),
            title=alarm_name,
            description=message.get("AlarmDescription", message.get("NewStateReason", "")),
            severity=severity_map.get(new_state, IncidentSeverity.MEDIUM.value),
            status=IncidentStatus.NEW.value if new_state == "ALARM" else IncidentStatus.RESOLVED.value,
            category="monitoring",
            service=service,
            cloud_provider="aws",
            region=message.get("Region", ""),
            resource_id=resource_id,
            metric_name=trigger.get("MetricName", ""),
            threshold=trigger.get("Threshold", 0),
            raw_data=raw_data
        )

    def validate_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Validate SNS message signature"""
        # AWS SNS uses certificate-based signature validation
        # For simplicity, check for expected headers
        message_type = headers.get("x-amz-sns-message-type", "")
        return message_type in ["Notification", "SubscriptionConfirmation"]


class PagerDutyConnector(IncidentSourceConnector):
    """
    PagerDuty incident connector.

    Handles webhooks from PagerDuty.
    """

    def __init__(self):
        self.webhook_secret = os.getenv("PAGERDUTY_WEBHOOK_SECRET", "")

    @property
    def source_name(self) -> str:
        return "pagerduty"

    def normalize_incident(self, raw_data: Dict[str, Any]) -> NormalizedIncident:
        """Normalize PagerDuty incident to unified format"""
        messages = raw_data.get("messages", [raw_data])
        if not messages:
            messages = [raw_data]

        message = messages[0]
        incident = message.get("incident", message)

        # Map PagerDuty urgency to severity
        urgency = incident.get("urgency", "high")
        severity_map = {
            "high": IncidentSeverity.HIGH.value,
            "low": IncidentSeverity.MEDIUM.value
        }

        # Map status
        status = incident.get("status", "triggered")
        status_map = {
            "triggered": IncidentStatus.NEW.value,
            "acknowledged": IncidentStatus.ACKNOWLEDGED.value,
            "resolved": IncidentStatus.RESOLVED.value
        }

        # Get service info
        service_info = incident.get("service", {})
        service_name = service_info.get("name", service_info.get("summary", ""))

        return NormalizedIncident(
            incident_id=f"pd_{incident.get('id', 'unknown')}",
            source=self.source_name,
            source_incident_id=incident.get("id", ""),
            title=incident.get("title", incident.get("summary", "PagerDuty Incident")),
            description=incident.get("description", incident.get("summary", "")),
            severity=severity_map.get(urgency, IncidentSeverity.MEDIUM.value),
            status=status_map.get(status, IncidentStatus.NEW.value),
            category=incident.get("type", "incident"),
            service=service_name,
            created_at=incident.get("created_at", datetime.now().isoformat()),
            raw_data=raw_data
        )

    def validate_webhook(self, headers: Dict[str, str], body: bytes) -> bool:
        """Validate PagerDuty webhook signature"""
        if not self.webhook_secret:
            return True

        signature = headers.get("X-PagerDuty-Signature", "")
        if not signature:
            return False

        # PagerDuty uses HMAC-SHA256
        expected = hmac.new(
            self.webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"v1={expected}", signature)


class IncidentSourceManager:
    """
    Manager for all incident source connectors.

    Routes incoming webhooks to appropriate connector and normalizes.
    """

    def __init__(self):
        self.connectors: Dict[str, IncidentSourceConnector] = {
            "datadog": DatadogConnector(),
            "prometheus": PrometheusConnector(),
            "alertmanager": PrometheusConnector(),
            "cloudwatch": CloudWatchConnector(),
            "pagerduty": PagerDutyConnector(),
        }

        logger.info(
            "incident_source_manager_initialized",
            sources=list(self.connectors.keys())
        )

    def normalize_incident(
        self,
        source: str,
        raw_data: Dict[str, Any]
    ) -> NormalizedIncident:
        """Normalize incident from any source"""
        connector = self.connectors.get(source.lower())
        if not connector:
            logger.warning("unknown_incident_source", source=source)
            # Return generic normalized incident
            return NormalizedIncident(
                incident_id=f"unknown_{int(datetime.now().timestamp())}",
                source=source,
                source_incident_id=str(raw_data.get("id", "")),
                title=raw_data.get("title", raw_data.get("summary", "Unknown Incident")),
                description=str(raw_data),
                severity=IncidentSeverity.MEDIUM.value,
                status=IncidentStatus.NEW.value,
                raw_data=raw_data
            )

        return connector.normalize_incident(raw_data)

    def validate_webhook(
        self,
        source: str,
        headers: Dict[str, str],
        body: bytes
    ) -> bool:
        """Validate webhook from source"""
        connector = self.connectors.get(source.lower())
        if not connector:
            return False
        return connector.validate_webhook(headers, body)

    def get_supported_sources(self) -> List[str]:
        """Get list of supported sources"""
        return list(self.connectors.keys())


# Global instance
incident_source_manager = IncidentSourceManager()
