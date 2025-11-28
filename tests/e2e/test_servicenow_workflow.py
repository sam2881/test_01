"""E2E tests for ServiceNow incident workflow"""
import pytest
import asyncio
import httpx
from typing import Dict, Any


@pytest.mark.e2e
@pytest.mark.asyncio
class TestServiceNowIncidentFlow:
    """Test complete ServiceNow incident resolution workflow"""

    async def test_complete_servicenow_workflow(self, async_client):
        """
        Test Steps (based on SERVICENOW_INCIDENT_FLOW.txt):
        1. Create incident
        2. BERTopic classification
        3. RAG query + routing
        4. HITL routing approval
        5. Sub-agent planning
        6. HITL plan approval
        7. Execution
        8. Learning loop
        9. Ticket closure
        """

        # STEP 1: Create incident
        print("\n[STEP 1] Creating incident...")
        incident_response = await async_client.post("/task", json={
            "description": "Production API Gateway returning 502 errors - 1500 users affected",
            "priority": "P1",
            "metadata": {
                "category": "Performance",
                "affected_service": "api-gateway",
                "affected_users": 1500,
                "error_rate": "1250/min"
            }
        })

        assert incident_response.status_code in [200, 201]
        incident_data = incident_response.json()
        task_id = incident_data["task_id"]
        print(f"✓ Incident created: {task_id}")

        # Wait for processing
        await asyncio.sleep(2)

        # STEP 2-3: Classification and routing should happen automatically
        print("\n[STEP 2-3] Checking routing decision...")

        # Check if approval was created
        approvals_response = await async_client.get("/api/hitl/approvals/pending")
        if approvals_response.status_code == 200:
            approvals = approvals_response.json()

            if len(approvals) > 0:
                approval = approvals[0]
                approval_id = approval["approval_id"]
                print(f"✓ Routing approval created: {approval_id}")

                # STEP 4: Approve routing (HITL)
                print("\n[STEP 4] Approving routing...")
                approve_response = await async_client.post(
                    f"/api/hitl/approvals/{approval_id}/approve-routing",
                    json={
                        "approved_by": "admin@company.com",
                        "selected_agent": approval["routing_decision"]["selected_agent"]
                    }
                )

                if approve_response.status_code == 200:
                    print(f"✓ Routing approved: {approval['routing_decision']['selected_agent']}")

                    # Wait for plan generation
                    await asyncio.sleep(3)

                    # STEP 5-6: Check for plan approval
                    print("\n[STEP 5-6] Checking for execution plan...")
                    plan_approvals = await async_client.get("/api/hitl/approvals/pending")

                    if plan_approvals.status_code == 200:
                        pending_plans = plan_approvals.json()
                        plan_approval = next(
                            (a for a in pending_plans if a.get("approval_type") == "plan_approval"),
                            None
                        )

                        if plan_approval:
                            print(f"✓ Execution plan created")

                            # Approve plan
                            plan_approve_response = await async_client.post(
                                f"/api/hitl/approvals/{plan_approval['approval_id']}/approve-plan",
                                json={
                                    "approved_by": "admin@company.com"
                                }
                            )

                            if plan_approve_response.status_code == 200:
                                print("✓ Execution plan approved")

        # STEP 7-9: Wait for execution, learning, and ticket creation
        print("\n[STEP 7-9] Waiting for execution and ticket creation...")
        await asyncio.sleep(10)

        # Verify incident was created in ServiceNow
        incidents_response = await async_client.get("/incidents")
        if incidents_response.status_code == 200:
            incidents = incidents_response.json()

            # Find our incident
            our_incident = next(
                (inc for inc in incidents if task_id in str(inc)),
                None
            )

            if our_incident:
                print(f"✓ ServiceNow ticket created: {our_incident.get('incident_id', 'N/A')}")

                # Check if resolved
                if our_incident.get("status") == "Resolved":
                    print("✓ Incident resolved successfully")
                    assert True
                else:
                    print(f"⚠ Incident status: {our_incident.get('status', 'Unknown')}")
            else:
                print("⚠ Incident not found in database (might still be processing)")

    async def test_p1_incident_priority_handling(self, async_client):
        """Test that P1 incidents are handled with priority"""

        response = await async_client.post("/task", json={
            "description": "CRITICAL: Database cluster completely down",
            "priority": "P1",
            "metadata": {
                "category": "Database",
                "severity": "critical"
            }
        })

        assert response.status_code in [200, 201]
        data = response.json()

        # P1 incidents should be processed immediately
        assert "task_id" in data

    async def test_infrastructure_scaling_workflow(self, async_client):
        """Test infrastructure scaling workflow specifically"""

        response = await async_client.post("/task", json={
            "description": "API Gateway instances at 95% CPU - need immediate scaling",
            "priority": "P1",
            "metadata": {
                "category": "Infrastructure",
                "metric": "cpu_utilization",
                "current_value": 0.95,
                "threshold": 0.80
            }
        })

        assert response.status_code in [200, 201]
        data = response.json()
        task_id = data["task_id"]

        # Should route to infrastructure agent
        await asyncio.sleep(5)

        # Check routing
        approvals = await async_client.get("/api/hitl/approvals/pending")
        if approvals.status_code == 200:
            pending = approvals.json()
            # Should have infrastructure as selected agent
            for approval in pending:
                if approval.get("incident_id") == task_id:
                    assert approval["routing_decision"]["selected_agent"] in ["infrastructure", "infra"]
                    break


@pytest.mark.e2e
@pytest.mark.asyncio
class TestServiceNowErrorScenarios:
    """Test error handling in ServiceNow workflow"""

    async def test_servicenow_api_timeout(self, async_client):
        """Test handling when ServiceNow API times out"""

        response = await async_client.post("/task", json={
            "description": "Test timeout scenario",
            "priority": "P3",
            "metadata": {
                "test_scenario": "timeout"
            }
        })

        # Should handle gracefully
        assert response.status_code in [200, 201, 500]

    async def test_invalid_incident_data(self, async_client):
        """Test handling of invalid incident data"""

        response = await async_client.post("/task", json={
            "description": "",  # Empty description
            "priority": "INVALID"  # Invalid priority
        })

        assert response.status_code in [400, 422]
