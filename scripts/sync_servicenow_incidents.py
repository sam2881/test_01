#!/usr/bin/env python3
"""
Script to sync incidents from ServiceNow to the HITL API
"""
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ServiceNow Configuration
SNOW_INSTANCE = os.getenv("SNOW_INSTANCE_URL")
SNOW_USERNAME = os.getenv("SNOW_USERNAME")
SNOW_PASSWORD = os.getenv("SNOW_PASSWORD")

# HITL API Configuration
HITL_API_URL = os.getenv("HITL_API_URL", "http://localhost:8000")


def fetch_servicenow_incidents(limit=50):
    """Fetch incidents from ServiceNow"""
    url = f"{SNOW_INSTANCE}/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    params = {
        "sysparm_limit": limit,
        "sysparm_query": "ORDERBYDESCsys_created_on",
        "sysparm_fields": "number,short_description,description,priority,state,category,assignment_group,sys_created_on,sys_id,urgency,impact"
    }

    try:
        print(f"🔍 Fetching incidents from ServiceNow...")
        print(f"   Instance: {SNOW_INSTANCE}")

        response = requests.get(
            url,
            auth=(SNOW_USERNAME, SNOW_PASSWORD),
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            incidents = data.get('result', [])
            print(f"✅ Fetched {len(incidents)} incidents from ServiceNow")
            return incidents
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return []

    except requests.exceptions.Timeout:
        print(f"❌ Error: Connection timed out")
        print(f"   Make sure your ServiceNow instance is active")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {str(e)}")
        return []
    except Exception as e:
        print(f"❌ Error parsing response: {str(e)}")
        return []


def map_servicenow_incident(snow_incident):
    """Map ServiceNow incident to HITL API format"""
    # Map ServiceNow priority (1-5) to severity
    priority_map = {
        "1": "critical",
        "2": "high",
        "3": "medium",
        "4": "low",
        "5": "low"
    }

    # Map ServiceNow state
    state_map = {
        "1": "new",
        "2": "in_progress",
        "3": "on_hold",
        "6": "resolved",
        "7": "closed",
    }

    priority = snow_incident.get('priority', '3')
    state = snow_incident.get('state', '1')

    return {
        "short_description": snow_incident.get('short_description', 'No description'),
        "description": snow_incident.get('description', snow_incident.get('short_description', 'No description')),
        "priority": priority,
        "severity": priority_map.get(priority, "medium"),
        "category": snow_incident.get('category', 'General'),
        "servicenow_number": snow_incident.get('number'),
        "servicenow_sys_id": snow_incident.get('sys_id'),
        "state": state,
        "status": state_map.get(state, "new")
    }


def create_incident_in_hitl_api(incident_data):
    """Create incident in HITL API"""
    url = f"{HITL_API_URL}/api/incidents/create"

    params = {
        "short_description": incident_data["short_description"],
        "description": incident_data["description"],
        "priority": incident_data["priority"],
        "category": incident_data["category"],
        "severity": incident_data["severity"]
    }

    try:
        response = requests.post(url, params=params, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return result.get('incident_id')
        else:
            print(f"   ⚠️  API Error: {response.status_code}")
            return None

    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")
        return None


def sync_incidents():
    """Main sync function"""
    print("="*80)
    print("🔄 ServiceNow → HITL API Incident Sync")
    print("="*80)
    print()

    # Fetch from ServiceNow
    snow_incidents = fetch_servicenow_incidents()

    if not snow_incidents:
        print()
        print("⚠️  No incidents fetched from ServiceNow")
        print()
        print("💡 Troubleshooting:")
        print("   1. Verify your instance is active at:")
        print(f"      {SNOW_INSTANCE}")
        print("   2. Check credentials in .env file")
        print("   3. Try accessing the instance in a browser")
        print()
        return

    print()
    print(f"📥 Syncing {len(snow_incidents)} incidents to HITL API...")
    print()

    synced = 0
    failed = 0

    for snow_incident in snow_incidents:
        incident_number = snow_incident.get('number', 'Unknown')
        short_desc = snow_incident.get('short_description', 'No description')[:60]

        print(f"   [{snow_incident.get('number')}] {short_desc}...", end=" ")

        # Map to HITL format
        incident_data = map_servicenow_incident(snow_incident)

        # Create in HITL API
        incident_id = create_incident_in_hitl_api(incident_data)

        if incident_id:
            print(f"✅ → {incident_id}")
            synced += 1
        else:
            print(f"❌ Failed")
            failed += 1

    print()
    print("="*80)
    print(f"✅ Sync Complete!")
    print(f"   Synced: {synced}")
    print(f"   Failed: {failed}")
    print("="*80)
    print()
    print("🌐 View in frontend:")
    print(f"   http://34.171.221.200:3002/incidents")
    print()
    print("🔌 View in API:")
    print(f"   curl {HITL_API_URL}/api/incidents")
    print()


if __name__ == "__main__":
    sync_incidents()
