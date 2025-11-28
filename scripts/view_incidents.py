#!/usr/bin/env python3
"""
Script to view incidents from ServiceNow
"""
import os
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables
load_dotenv()

# ServiceNow Configuration
SNOW_INSTANCE = os.getenv("SNOW_INSTANCE_URL")
SNOW_USERNAME = os.getenv("SNOW_USERNAME")
SNOW_PASSWORD = os.getenv("SNOW_PASSWORD")


def get_all_incidents(limit=20):
    """Fetch recent incidents from ServiceNow"""
    url = f"{SNOW_INSTANCE}/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    params = {
        "sysparm_limit": limit,
        "sysparm_query": "ORDERBYDESCsys_created_on",
        "sysparm_fields": "number,short_description,priority,state,category,assignment_group,sys_created_on,sys_id"
    }

    try:
        response = requests.get(
            url,
            auth=(SNOW_USERNAME, SNOW_PASSWORD),
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            return response.json()['result']
        else:
            print(f"❌ Error: Status {response.status_code}")
            print(response.text)
            return []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []


def get_incident_details(incident_number):
    """Get detailed information about a specific incident"""
    url = f"{SNOW_INSTANCE}/api/now/table/incident"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    params = {
        "sysparm_query": f"number={incident_number}",
        "sysparm_limit": 1
    }

    try:
        response = requests.get(
            url,
            auth=(SNOW_USERNAME, SNOW_PASSWORD),
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            results = response.json()['result']
            return results[0] if results else None
        else:
            print(f"❌ Error: Status {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def format_priority(priority):
    """Format priority with emoji"""
    priority_map = {
        "1": "🔴 Critical",
        "2": "🟠 High",
        "3": "🟡 Moderate",
        "4": "🟢 Low",
        "5": "⚪ Planning"
    }
    return priority_map.get(priority, f"Priority {priority}")


def format_state(state):
    """Format state with emoji"""
    state_map = {
        "1": "🆕 New",
        "2": "🔄 In Progress",
        "3": "⏸️ On Hold",
        "4": "✅ Resolved",
        "5": "❌ Closed",
        "6": "✅ Resolved",
        "7": "❌ Canceled"
    }
    return state_map.get(state, f"State {state}")


def display_incidents(incidents):
    """Display incidents in a nice table format"""
    if not incidents:
        print("❌ No incidents found")
        return

    # Prepare table data
    table_data = []
    for inc in incidents:
        table_data.append([
            inc.get('number', 'N/A'),
            inc.get('short_description', 'N/A')[:50] + ('...' if len(inc.get('short_description', '')) > 50 else ''),
            format_priority(inc.get('priority', 'N/A')),
            format_state(inc.get('state', 'N/A')),
            inc.get('category', 'N/A'),
            inc.get('assignment_group', 'Unassigned')
        ])

    # Display table
    headers = ['Incident #', 'Description', 'Priority', 'State', 'Category', 'Assigned To']
    print("\n" + "="*120)
    print(f"📋 ServiceNow Incidents (Total: {len(incidents)})")
    print("="*120)
    print(tabulate(table_data, headers=headers, tablefmt='grid'))
    print()


def display_incident_details(incident):
    """Display detailed information about a single incident"""
    if not incident:
        print("❌ Incident not found")
        return

    print("\n" + "="*80)
    print(f"📋 Incident Details: {incident.get('number')}")
    print("="*80)
    print(f"Short Description: {incident.get('short_description')}")
    print(f"Description:       {incident.get('description', 'N/A')}")
    print(f"Priority:          {format_priority(incident.get('priority', 'N/A'))}")
    print(f"State:             {format_state(incident.get('state', 'N/A'))}")
    print(f"Category:          {incident.get('category', 'N/A')}")
    print(f"Urgency:           {incident.get('urgency', 'N/A')}")
    print(f"Impact:            {incident.get('impact', 'N/A')}")
    print(f"Assignment Group:  {incident.get('assignment_group', 'Unassigned')}")
    print(f"Assigned To:       {incident.get('assigned_to', 'Unassigned')}")
    print(f"Created:           {incident.get('sys_created_on', 'N/A')}")
    print(f"Updated:           {incident.get('sys_updated_on', 'N/A')}")
    print(f"Sys ID:            {incident.get('sys_id', 'N/A')}")

    if incident.get('work_notes'):
        print(f"\nWork Notes:\n{incident.get('work_notes')}")

    if incident.get('comments'):
        print(f"\nComments:\n{incident.get('comments')}")

    print("="*80)
    print()


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("🎫 ServiceNow Incident Viewer")
    print("="*80)
    print(f"Instance: {SNOW_INSTANCE}")
    print(f"Username: {SNOW_USERNAME}")
    print("="*80)

    # Check if specific incident number provided
    if len(sys.argv) > 1:
        incident_number = sys.argv[1]
        print(f"\n🔍 Fetching incident: {incident_number}...")
        incident = get_incident_details(incident_number)
        display_incident_details(incident)
    else:
        # Fetch and display all recent incidents
        print("\n🔍 Fetching recent incidents...")
        incidents = get_all_incidents(limit=50)
        display_incidents(incidents)

        print("\n💡 Tip: To view details of a specific incident, run:")
        print(f"   python3 {sys.argv[0]} INC0010001")

    print("\n🌐 View in ServiceNow:")
    print(f"   {SNOW_INSTANCE}/nav_to.do?uri=incident_list.do")
    print()


if __name__ == "__main__":
    main()
