"""
Kafka Producer for Incident Events
Industry-standard event-driven architecture
"""
import os
import json
from typing import Any, Dict
from datetime import datetime
import structlog
from kafka import KafkaProducer
from kafka.errors import KafkaError

logger = structlog.get_logger()


class IncidentKafkaProducer:
    """
    Kafka producer for publishing incident lifecycle events

    Topics:
    - incident.created
    - incident.llm.analysis_complete
    - incident.approval.requested
    - incident.execution.approved
    - incident.github.pr_created
    - incident.jira.ticket_created
    - incident.execution.completed
    """

    def __init__(self):
        self.bootstrap_servers = os.getenv(
            'KAFKA_BOOTSTRAP_SERVERS',
            'localhost:9092'
        ).replace('kafka://', '')

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1  # Ensure ordering
            )
            logger.info("kafka_producer_initialized", servers=self.bootstrap_servers)
        except Exception as e:
            logger.error("kafka_producer_init_failed", error=str(e))
            self.producer = None

    async def publish_event(
        self,
        topic: str,
        event: Dict[str, Any],
        key: str = None
    ) -> bool:
        """
        Publish event to Kafka topic

        Args:
            topic: Kafka topic name
            event: Event payload (will be JSON serialized)
            key: Optional partition key

        Returns:
            True if successful, False otherwise
        """
        if not self.producer:
            logger.warning("kafka_producer_not_available", topic=topic)
            return False

        try:
            # Add timestamp if not present
            if 'timestamp' not in event:
                event['timestamp'] = datetime.now().isoformat()

            # Use incident_id as key if available and no key provided
            if not key and 'incident_id' in event:
                key = event['incident_id']

            # Send to Kafka
            future = self.producer.send(
                topic=topic,
                value=event,
                key=key
            )

            # Wait for confirmation (optional, can be async)
            record_metadata = future.get(timeout=10)

            logger.info(
                "kafka_event_published",
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                key=key
            )

            return True

        except KafkaError as e:
            logger.error("kafka_publish_error", topic=topic, error=str(e))
            return False
        except Exception as e:
            logger.error("kafka_publish_exception", topic=topic, error=str(e))
            return False

    def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("kafka_producer_closed")


# Global instance
incident_producer = IncidentKafkaProducer()
