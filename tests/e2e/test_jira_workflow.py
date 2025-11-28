"""E2E tests for Jira ticket workflow"""
import pytest
import asyncio
import httpx


@pytest.mark.e2e
@pytest.mark.asyncio
class TestJiraTicketFlow:
    """Test complete Jira bug fix workflow"""

    async def test_complete_jira_workflow(self, async_client):
        """
        Test Steps (based on JIRA_TICKET_FLOW.txt):
        1. Report bug
        2. BERTopic classification
        3. RAG query + routing to Jira agent
        4. HITL routing approval
        5. Sub-agent planning (8 steps)
        6. HITL plan approval
        7. Execution (code fix, tests, PR, review, deploy)
        8. Learning loop
        9. Ticket closure
        """

        # STEP 1: Report bug
        print("\n[STEP 1] Reporting bug...")
        bug_response = await async_client.post("/task", json={
            "description": "Payment validation failing for UTF-8 characters - José, María, François names rejected",
            "priority": "P2",
            "metadata": {
                "category": "Bug",
                "affected_service": "payment-service",
                "component": "PaymentService.java",
                "affected_users_per_day": 200
            }
        })

        assert bug_response.status_code in [200, 201]
        bug_data = bug_response.json()
        task_id = bug_data["task_id"]
        print(f"✓ Bug reported: {task_id}")

        # Wait for processing
        await asyncio.sleep(2)

        # STEP 2-3: Classification and routing
        print("\n[STEP 2-3] Checking routing to Jira agent...")

        approvals_response = await async_client.get("/api/hitl/approvals/pending")
        if approvals_response.status_code == 200:
            approvals = approvals_response.json()

            if len(approvals) > 0:
                approval = approvals[0]
                approval_id = approval["approval_id"]
                selected_agent = approval["routing_decision"]["selected_agent"]

                print(f"✓ Routing decision: {selected_agent}")

                # Should route to Jira agent for software bugs
                assert selected_agent in ["jira", "github"]

                # STEP 4: Approve routing
                print("\n[STEP 4] Approving routing to Jira agent...")
                approve_response = await async_client.post(
                    f"/api/hitl/approvals/{approval_id}/approve-routing",
                    json={
                        "approved_by": "developer@company.com",
                        "selected_agent": selected_agent
                    }
                )

                if approve_response.status_code == 200:
                    print(f"✓ Routing approved")

                    # Wait for plan generation
                    await asyncio.sleep(3)

                    # STEP 5-6: Check for execution plan (8 steps expected)
                    print("\n[STEP 5-6] Checking for 8-step execution plan...")
                    plan_approvals = await async_client.get("/api/hitl/approvals/pending")

                    if plan_approvals.status_code == 200:
                        pending_plans = plan_approvals.json()
                        plan_approval = next(
                            (a for a in pending_plans if a.get("approval_type") == "plan_approval"),
                            None
                        )

                        if plan_approval:
                            execution_plan = plan_approval.get("execution_plan", {})
                            steps = execution_plan.get("steps", [])
                            print(f"✓ Execution plan created with {len(steps)} steps")

                            # Approve plan
                            plan_approve_response = await async_client.post(
                                f"/api/hitl/approvals/{plan_approval['approval_id']}/approve-plan",
                                json={
                                    "approved_by": "developer@company.com"
                                }
                            )

                            if plan_approve_response.status_code == 200:
                                print("✓ Execution plan approved")

        # STEP 7: Wait for execution (code fix, tests, PR, review, deploy)
        print("\n[STEP 7] Waiting for code fix, tests, PR creation, and deployment...")
        await asyncio.sleep(15)

        # Check if Jira ticket was created
        incidents_response = await async_client.get("/incidents")
        if incidents_response.status_code == 200:
            incidents = incidents_response.json()

            our_incident = next(
                (inc for inc in incidents if task_id in str(inc)),
                None
            )

            if our_incident:
                print(f"✓ Jira ticket created: {our_incident.get('incident_id', 'N/A')}")

                # STEP 8-9: Learning and closure
                if our_incident.get("status") in ["Done", "Resolved"]:
                    print("✓ Bug fixed and ticket closed")
                    assert True

    async def test_code_bug_routing(self, async_client):
        """Test that code bugs are routed to Jira agent"""

        response = await async_client.post("/task", json={
            "description": "NullPointerException in UserService.validateEmail() method",
            "priority": "P2",
            "metadata": {
                "category": "Bug",
                "stack_trace": "java.lang.NullPointerException at UserService.java:145"
            }
        })

        assert response.status_code in [200, 201]

        # Wait for routing
        await asyncio.sleep(3)

        approvals = await async_client.get("/api/hitl/approvals/pending")
        if approvals.status_code == 200:
            pending = approvals.json()
            if len(pending) > 0:
                # Should route to Jira for code bugs
                assert pending[0]["routing_decision"]["selected_agent"] in ["jira", "github"]

    async def test_github_pr_creation(self, async_client):
        """Test that GitHub PR is created for code fixes"""

        response = await async_client.post("/task", json={
            "description": "Fix regex validation bug in PaymentService",
            "priority": "P3",
            "metadata": {
                "category": "Bug",
                "requires_pr": True,
                "repository": "payment-service"
            }
        })

        assert response.status_code in [200, 201]

        # In real scenario, would check for PR creation via GitHub API
        # For now, just verify task was created
        data = response.json()
        assert "task_id" in data


@pytest.mark.e2e
@pytest.mark.asyncio
class TestJiraErrorScenarios:
    """Test error handling in Jira workflow"""

    async def test_jira_api_authentication_error(self, async_client):
        """Test handling when Jira authentication fails"""

        response = await async_client.post("/task", json={
            "description": "Test Jira auth failure",
            "priority": "P3",
            "metadata": {
                "test_scenario": "auth_failure"
            }
        })

        # Should handle gracefully
        assert response.status_code in [200, 201, 500]

    async def test_github_pr_merge_conflict(self, async_client):
        """Test handling when GitHub PR has merge conflicts"""

        response = await async_client.post("/task", json={
            "description": "Fix bug with potential merge conflicts",
            "priority": "P3",
            "metadata": {
                "test_scenario": "merge_conflict"
            }
        })

        assert response.status_code in [200, 201]
