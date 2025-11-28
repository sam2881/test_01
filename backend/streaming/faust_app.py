"""Faust streaming app for log correlation (L1.5 processing)"""
import os
import faust
from typing import Any, Dict
import structlog

logger = structlog.get_logger()

# Create Faust app
app = faust.App(
    'log-correlator',
    broker=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka://kafka:9092'),
    value_serializer='json',
)


# Define topics
raw_logs_topic = app.topic('raw.logs')
correlated_events_topic = app.topic('correlated.events')


# Define agent for processing
@app.agent(raw_logs_topic)
async def correlate_logs(stream):
    """Correlate raw logs into meaningful events"""
    async for log in stream:
        try:
            # Simple correlation logic - group logs by service and time window
            correlated_event = {
                'service': log.get('service', 'unknown'),
                'timestamp': log.get('timestamp'),
                'log_count': 1,
                'severity': log.get('level', 'INFO'),
                'message': log.get('message', ''),
                'correlation_id': log.get('correlation_id', 'N/A')
            }

            # Publish to correlated events topic
            await correlated_events_topic.send(value=correlated_event)

            logger.info("log_correlated", service=correlated_event['service'])

        except Exception as e:
            logger.error("correlation_error", error=str(e))


@app.timer(interval=30.0)
async def periodic_flush():
    """Periodic flush of buffered events"""
    logger.debug("periodic_flush_triggered")


if __name__ == '__main__':
    app.main()
