"""GCP Alerting Policies and Webhook Handler"""
import os
from typing import Dict, Any, List
from google.cloud import monitoring_v3
from google.api_core import protobuf_helpers
import structlog

logger = structlog.get_logger()


class GCPAlertingPolicyManager:
    """Manage GCP Cloud Monitoring alerting policies"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_name = f"projects/{project_id}"
        self.alert_policy_client = monitoring_v3.AlertPolicyServiceClient()
        self.notification_channel_client = monitoring_v3.NotificationChannelServiceClient()

    def create_notification_channel(
        self,
        webhook_url: str,
        display_name: str = "AI Agent Platform Webhook"
    ) -> str:
        """Create a webhook notification channel"""
        try:
            notification_channel = monitoring_v3.NotificationChannel(
                type_="webhook_tokenauth",
                display_name=display_name,
                labels={
                    "url": webhook_url
                }
            )

            channel = self.notification_channel_client.create_notification_channel(
                name=self.project_name,
                notification_channel=notification_channel
            )

            logger.info("notification_channel_created", channel_name=channel.name)
            return channel.name

        except Exception as e:
            logger.error("notification_channel_creation_failed", error=str(e))
            raise

    def create_cpu_alert_policy(
        self,
        notification_channel_name: str,
        threshold: float = 0.85,
        duration_seconds: int = 300
    ):
        """Create alert policy for high CPU utilization"""
        try:
            # Define the condition
            condition = monitoring_v3.AlertPolicy.Condition(
                display_name="High CPU Utilization",
                condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                    filter='metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.type="gce_instance"',
                    comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                    threshold_value=threshold,
                    duration={"seconds": duration_seconds},
                    aggregations=[
                        monitoring_v3.Aggregation(
                            alignment_period={"seconds": 60},
                            per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
                        )
                    ],
                ),
            )

            # Create the alert policy
            policy = monitoring_v3.AlertPolicy(
                display_name="GCE Instance High CPU Utilization",
                conditions=[condition],
                notification_channels=[notification_channel_name],
                combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.AND,
                enabled=True,
                documentation=monitoring_v3.AlertPolicy.Documentation(
                    content="CPU utilization exceeded threshold. Automatic ticket created in ServiceNow.",
                    mime_type="text/markdown"
                )
            )

            created_policy = self.alert_policy_client.create_alert_policy(
                name=self.project_name,
                alert_policy=policy
            )

            logger.info("cpu_alert_policy_created", policy_name=created_policy.name)
            return created_policy

        except Exception as e:
            logger.error("alert_policy_creation_failed", error=str(e))
            raise

    def create_memory_alert_policy(
        self,
        notification_channel_name: str,
        threshold: float = 0.90
    ):
        """Create alert policy for high memory utilization"""
        condition = monitoring_v3.AlertPolicy.Condition(
            display_name="High Memory Utilization",
            condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                filter='metric.type="compute.googleapis.com/instance/memory/percent_used" AND resource.type="gce_instance"',
                comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                threshold_value=threshold,
                duration={"seconds": 300},
            ),
        )

        policy = monitoring_v3.AlertPolicy(
            display_name="GCE Instance High Memory Utilization",
            conditions=[condition],
            notification_channels=[notification_channel_name],
            combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.AND,
            enabled=True,
        )

        created_policy = self.alert_policy_client.create_alert_policy(
            name=self.project_name,
            alert_policy=policy
        )

        logger.info("memory_alert_policy_created", policy_name=created_policy.name)
        return created_policy

    def create_disk_alert_policy(
        self,
        notification_channel_name: str,
        threshold: float = 0.85
    ):
        """Create alert policy for high disk utilization"""
        condition = monitoring_v3.AlertPolicy.Condition(
            display_name="High Disk Utilization",
            condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                filter='metric.type="compute.googleapis.com/instance/disk/percent_used" AND resource.type="gce_instance"',
                comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                threshold_value=threshold,
                duration={"seconds": 600},
            ),
        )

        policy = monitoring_v3.AlertPolicy(
            display_name="GCE Instance High Disk Utilization",
            conditions=[condition],
            notification_channels=[notification_channel_name],
            combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.AND,
            enabled=True,
        )

        created_policy = self.alert_policy_client.create_alert_policy(
            name=self.project_name,
            alert_policy=policy
        )

        logger.info("disk_alert_policy_created", policy_name=created_policy.name)
        return created_policy

    def create_cloud_sql_alert_policy(
        self,
        notification_channel_name: str,
        cpu_threshold: float = 0.80
    ):
        """Create alert policy for Cloud SQL high CPU"""
        condition = monitoring_v3.AlertPolicy.Condition(
            display_name="Cloud SQL High CPU",
            condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                filter='metric.type="cloudsql.googleapis.com/database/cpu/utilization" AND resource.type="cloudsql_database"',
                comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                threshold_value=cpu_threshold,
                duration={"seconds": 300},
            ),
        )

        policy = monitoring_v3.AlertPolicy(
            display_name="Cloud SQL High CPU Utilization",
            conditions=[condition],
            notification_channels=[notification_channel_name],
            combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.AND,
            enabled=True,
        )

        created_policy = self.alert_policy_client.create_alert_policy(
            name=self.project_name,
            alert_policy=policy
        )

        logger.info("cloudsql_alert_policy_created", policy_name=created_policy.name)
        return created_policy

    def create_gke_alert_policy(
        self,
        notification_channel_name: str,
        pod_crash_threshold: int = 5
    ):
        """Create alert policy for GKE pod crashes"""
        condition = monitoring_v3.AlertPolicy.Condition(
            display_name="GKE Pod Crash Rate",
            condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                filter='metric.type="kubernetes.io/container/restart_count" AND resource.type="k8s_container"',
                comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                threshold_value=pod_crash_threshold,
                duration={"seconds": 300},
            ),
        )

        policy = monitoring_v3.AlertPolicy(
            display_name="GKE High Pod Restart Rate",
            conditions=[condition],
            notification_channels=[notification_channel_name],
            combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.AND,
            enabled=True,
        )

        created_policy = self.alert_policy_client.create_alert_policy(
            name=self.project_name,
            alert_policy=policy
        )

        logger.info("gke_alert_policy_created", policy_name=created_policy.name)
        return created_policy

    def setup_all_policies(self, webhook_url: str) -> Dict[str, Any]:
        """Set up all monitoring policies"""
        results = {
            "notification_channel": None,
            "policies_created": []
        }

        try:
            # Create notification channel
            channel_name = self.create_notification_channel(webhook_url)
            results["notification_channel"] = channel_name

            # Create all alert policies
            policies = [
                ("cpu", lambda: self.create_cpu_alert_policy(channel_name)),
                ("memory", lambda: self.create_memory_alert_policy(channel_name)),
                ("disk", lambda: self.create_disk_alert_policy(channel_name)),
                ("cloudsql", lambda: self.create_cloud_sql_alert_policy(channel_name)),
                ("gke", lambda: self.create_gke_alert_policy(channel_name)),
            ]

            for policy_type, policy_creator in policies:
                try:
                    policy = policy_creator()
                    results["policies_created"].append({
                        "type": policy_type,
                        "name": policy.name,
                        "status": "created"
                    })
                except Exception as e:
                    logger.error(f"{policy_type}_policy_failed", error=str(e))
                    results["policies_created"].append({
                        "type": policy_type,
                        "status": "failed",
                        "error": str(e)
                    })

            logger.info("all_policies_setup_complete", policies=len(results["policies_created"]))
            return results

        except Exception as e:
            logger.error("policy_setup_failed", error=str(e))
            raise


def parse_gcp_alert_notification(notification_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse GCP alert notification to extract key information"""
    incident = notification_data.get("incident", {})

    return {
        "incident_id": incident.get("incident_id"),
        "resource_type": incident.get("resource_type_display_name"),
        "resource_name": incident.get("resource_name"),
        "metric_type": incident.get("metric", {}).get("type"),
        "threshold_value": incident.get("threshold_value"),
        "observed_value": incident.get("observed_value"),
        "started_at": incident.get("started_at"),
        "policy_name": incident.get("policy_name"),
        "summary": incident.get("summary"),
        "severity": "high" if "critical" in incident.get("severity", "").lower() else "medium"
    }
