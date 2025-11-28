#!/usr/bin/env python3
"""
ServiceNow to Kafka Producer
Fetches incidents from ServiceNow and publishes to Kafka topics
"""
import os
import sys
import json
import time
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Configuration
SNOW_URL = os.getenv('SNOW_INSTANCE_URL', 'https://dev275804.service-now.com')
SNOW_USER = os.getenv('SNOW_USERNAME', 'admin')
SNOW_PASS = os.getenv('SNOW_PASSWORD')
KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
POLL_INTERVAL = int(os.getenv('SNOW_POLL_INTERVAL', '60'))  # seconds

class ServiceNowKafkaProducer:
    def __init__(self):
        """Initialize Kafka producer and ServiceNow client"""
        print(f"🔧 Initializing ServiceNow to Kafka Producer...")
        print(f"   ServiceNow: {SNOW_URL}")
        print(f"   Kafka: {KAFKA_BOOTSTRAP}")

        # Create Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3
        )

        # ServiceNow auth
        self.snow_auth = HTTPBasicAuth(SNOW_USER, SNOW_PASS)
        self.last_poll_time = None

        print("✅ Producer initialized successfully!")

    def fetch_new_incidents(self):
        """Fetch new or updated incidents from ServiceNow"""
        try:
            url = f"{SNOW_URL}/api/now/table/incident"
            params = {
                'sysparm_limit': 100,
                'sysparm_query': 'active=true^ORDERBYDESCsys_updated_on'
            }

            # Only fetch incidents updated since last poll
            if self.last_poll_time:
                params['sysparm_query'] += f'^sys_updated_on>={self.last_poll_time}'

            response = requests.get(
                url,
                auth=self.snow_auth,
                params=params,
                headers={'Accept': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                incidents = response.json().get('result', [])
                print(f"📥 Fetched {len(incidents)} incident(s) from ServiceNow")
                return incidents
            else:
                print(f"❌ ServiceNow API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error fetching incidents: {e}")
            return []

    def publish_incident(self, incident):
        """Publish incident to Kafka topic"""
        try:
            # Transform incident data
            event = {
                'event_type': 'incident_created' if incident.get('sys_created_on') == incident.get('sys_updated_on') else 'incident_updated',
                'timestamp': datetime.now().isoformat(),
                'source': 'servicenow',
                'incident': {
                    'incident_id': incident.get('number'),
                    'sys_id': incident.get('sys_id'),
                    'short_description': incident.get('short_description'),
                    'description': incident.get('description'),
                    'priority': incident.get('priority'),
                    'state': incident.get('state'),
                    'urgency': incident.get('urgency'),
                    'impact': incident.get('impact'),
                    'category': incident.get('category'),
                    'subcategory': incident.get('subcategory'),
                    'assignment_group': incident.get('assignment_group'),
                    'assigned_to': incident.get('assigned_to'),
                    'created_on': incident.get('sys_created_on'),
                    'updated_on': incident.get('sys_updated_on'),
                }
            }

            # Check if GCP alert
            if '[GCP' in incident.get('short_description', ''):
                topic = 'gcp.alerts'
            else:
                topic = 'servicenow.incidents'

            # Publish to Kafka
            future = self.producer.send(
                topic,
                key=incident.get('number'),
                value=event
            )

            # Wait for confirmation
            record_metadata = future.get(timeout=10)

            print(f"✅ Published {incident.get('number')} to {topic} (partition: {record_metadata.partition}, offset: {record_metadata.offset})")

            return True

        except KafkaError as e:
            print(f"❌ Kafka error publishing incident {incident.get('number')}: {e}")
            return False
        except Exception as e:
            print(f"❌ Error publishing incident {incident.get('number')}: {e}")
            return False

    def run(self):
        """Main polling loop"""
        print(f"\n🚀 Starting ServiceNow to Kafka streaming...")
        print(f"   Poll interval: {POLL_INTERVAL}s")
        print(f"   Topics: servicenow.incidents, gcp.alerts\n")

        try:
            while True:
                print(f"⏰ Polling ServiceNow at {datetime.now().strftime('%H:%M:%S')}...")

                # Fetch new incidents
                incidents = self.fetch_new_incidents()

                # Publish to Kafka
                published_count = 0
                for incident in incidents:
                    if self.publish_incident(incident):
                        published_count += 1

                if published_count > 0:
                    print(f"📤 Published {published_count} event(s) to Kafka")

                # Update last poll time
                self.last_poll_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Sleep until next poll
                print(f"😴 Sleeping for {POLL_INTERVAL}s...\n")
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n⏹️  Shutting down producer...")
            self.producer.close()
            print("✅ Producer closed successfully!")

    def test_connection(self):
        """Test ServiceNow and Kafka connections"""
        print("\n🧪 Testing connections...")

        # Test ServiceNow
        try:
            response = requests.get(
                f"{SNOW_URL}/api/now/table/incident",
                auth=self.snow_auth,
                params={'sysparm_limit': 1},
                timeout=10
            )
            if response.status_code == 200:
                print("✅ ServiceNow connection successful")
            else:
                print(f"❌ ServiceNow connection failed: {response.status_code}")
        except Exception as e:
            print(f"❌ ServiceNow connection error: {e}")

        # Test Kafka
        try:
            self.producer.send('agent.events', value={'test': True}).get(timeout=5)
            print("✅ Kafka connection successful")
        except Exception as e:
            print(f"❌ Kafka connection error: {e}")

        print()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='ServiceNow to Kafka Producer')
    parser.add_argument('--test', action='store_true', help='Test connections and exit')
    parser.add_argument('--once', action='store_true', help='Poll once and exit')
    args = parser.parse_args()

    producer = ServiceNowKafkaProducer()

    if args.test:
        producer.test_connection()
    elif args.once:
        print("📥 Fetching incidents once...")
        incidents = producer.fetch_new_incidents()
        for incident in incidents:
            producer.publish_incident(incident)
        print(f"✅ Published {len(incidents)} incident(s)")
        producer.producer.close()
    else:
        producer.run()
