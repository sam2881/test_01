"""
GCP Issue Resolver with LLM + RAG + HITL
Handles variety of GCP issues with human approval at 2 steps
"""
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import httpx

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.rag.hybrid_search import hybrid_rag
from backend.orchestrator.dynamic_solution_generator import solution_generator
from backend.streaming.kafka_producer import incident_producer

logger = structlog.get_logger()


class IssueCategory(Enum):
    """GCP issue categories"""
    VM_DOWN = "vm_down"
    VM_PERFORMANCE = "vm_performance"
    DISK_FULL = "disk_full"
    NETWORK_ISSUE = "network_issue"
    DATABASE_ISSUE = "database_issue"
    KUBERNETES_ISSUE = "kubernetes_issue"
    PERMISSION_ISSUE = "permission_issue"
    COST_ANOMALY = "cost_anomaly"
    SECURITY_ALERT = "security_alert"
    UNKNOWN = "unknown"


class SubAgent(Enum):
    """Available sub-agents"""
    INFRASTRUCTURE = "infrastructure"  # VM, Disk, Network
    DATABASE = "database"              # Cloud SQL
    KUBERNETES = "kubernetes"          # GKE
    SECURITY = "security"              # IAM, Firewall
    DATA = "data"                      # BigQuery, Storage


class ApprovalStatus(Enum):
    """HITL approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"


class GCPIssueResolver:
    """
    Resolves variety of GCP issues using LLM + RAG with HITL

    Workflow:
    1. Analyze incident with LLM + RAG
    2. HITL Step 1: Approve/Override agent routing
    3. Sub-agent generates execution plan
    4. HITL Step 2: Approve/Reject execution plan
    5. Execute (Terraform/Ansible/gcloud)
    6. Update ServiceNow with results
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.2)
        self.rag = hybrid_rag

        # Agent endpoints
        self.agents = {
            SubAgent.INFRASTRUCTURE: "http://localhost:8013",
            SubAgent.DATABASE: "http://localhost:8014",
            SubAgent.KUBERNETES: "http://localhost:8016",
            SubAgent.SECURITY: "http://localhost:8017",
            SubAgent.DATA: "http://localhost:8012",
        }

        # Approval storage (in production, use Redis/DB)
        self.pending_approvals = {}

    def analyze_issue_with_llm(
        self,
        incident_description: str,
        gcp_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 1: Analyze GCP issue with LLM + RAG

        Returns:
            - issue_category
            - recommended_agent
            - root_cause_hypothesis
            - recommended_actions
            - confidence_score
            - rag_context_used
        """
        logger.info("analyzing_gcp_issue", description=incident_description[:100])

        # Get RAG context
        rag_context = self.rag.retrieve_context_for_incident(
            incident_description=incident_description,
            service="gcp",
            limit=5
        )

        similar_incidents = "\n".join([
            f"- {inc.get('title', '')}: {inc.get('resolution', '')}"
            for inc in rag_context.get("similar_incidents", [])[:3]
        ])

        # LLM Analysis Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert GCP DevOps engineer analyzing infrastructure incidents.

Analyze the incident and provide:
1. Issue category (vm_down, vm_performance, disk_full, network_issue, database_issue, kubernetes_issue, permission_issue, cost_anomaly, security_alert, unknown)
2. Recommended sub-agent to handle this (infrastructure, database, kubernetes, security, data)
3. Root cause hypothesis
4. Recommended remediation actions
5. Confidence score (0.0-1.0)

GCP Context:
{gcp_context}

Similar incidents from RAG:
{similar_incidents}

Respond in JSON format:
{{
    "issue_category": "category",
    "recommended_agent": "agent_name",
    "root_cause": "detailed hypothesis",
    "recommended_actions": [
        "action 1",
        "action 2"
    ],
    "requires_terraform": true/false,
    "requires_ansible": true/false,
    "requires_gcloud": true/false,
    "vm_name": "extracted-vm-name or null",
    "zone": "extracted-zone or null",
    "project_id": "extracted-project or null",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}"""),
            ("human", "Incident: {description}")
        ])

        chain = prompt | self.llm

        try:
            response = chain.invoke({
                "description": incident_description,
                "gcp_context": str(gcp_context),
                "similar_incidents": similar_incidents or "No similar incidents"
            })

            import json
            result = json.loads(response.content)
            result["rag_context"] = {
                "similar_incidents_count": len(rag_context.get("similar_incidents", [])),
                "runbooks_count": len(rag_context.get("runbooks", []))
            }

            logger.info("llm_analysis_complete",
                       category=result.get("issue_category"),
                       agent=result.get("recommended_agent"),
                       confidence=result.get("confidence"))

            return result

        except Exception as e:
            logger.error("llm_analysis_error", error=str(e))
            return {
                "issue_category": IssueCategory.UNKNOWN.value,
                "recommended_agent": SubAgent.INFRASTRUCTURE.value,
                "error": str(e),
                "confidence": 0.0
            }

    def create_hitl_approval_request(
        self,
        approval_type: str,
        incident_id: str,
        data: Dict[str, Any]
    ) -> str:
        """
        Create HITL approval request

        Args:
            approval_type: "routing" or "execution"
            incident_id: ServiceNow incident ID
            data: Approval data

        Returns:
            approval_id
        """
        approval_id = f"{approval_type}_{incident_id}_{int(datetime.now().timestamp())}"

        self.pending_approvals[approval_id] = {
            "approval_id": approval_id,
            "type": approval_type,
            "incident_id": incident_id,
            "status": ApprovalStatus.PENDING.value,
            "data": data,
            "created_at": datetime.now().isoformat(),
            "timeout_minutes": 30
        }

        logger.info("hitl_approval_created",
                   approval_id=approval_id,
                   type=approval_type,
                   incident=incident_id)

        return approval_id

    async def wait_for_hitl_approval(
        self,
        approval_id: str,
        timeout_seconds: int = 1800  # 30 minutes
    ) -> Dict[str, Any]:
        """
        Wait for HITL approval (non-blocking in production)

        Returns:
            {
                "status": "approved/rejected/overridden/timeout",
                "updated_data": {...},  # For overrides
                "comment": "human comment"
            }
        """
        # In production, this would be event-driven (WebSocket/SSE)
        # For now, return pending status
        approval = self.pending_approvals.get(approval_id)

        if not approval:
            return {"status": "error", "message": "Approval not found"}

        return {
            "status": approval["status"],
            "data": approval.get("data"),
            "comment": approval.get("comment", "")
        }

    async def generate_execution_plan(
        self,
        agent: SubAgent,
        analysis: Dict[str, Any],
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Sub-agent generates execution plan

        Returns:
            {
                "plan_steps": [...],
                "terraform_required": bool,
                "ansible_required": bool,
                "estimated_duration": "5 minutes",
                "risk_level": "low/medium/high",
                "rollback_plan": [...]
            }
        """
        logger.info("generating_execution_plan", agent=agent.value, incident=incident_id)

        # Call sub-agent API to generate plan
        agent_url = self.agents.get(agent)

        if not agent_url:
            return {"error": "Agent not available"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{agent_url}/plan",
                    json={
                        "incident_id": incident_id,
                        "analysis": analysis
                    },
                    timeout=60.0
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Agent returned {response.status_code}"}

        except Exception as e:
            logger.error("execution_plan_error", error=str(e))

            # Fallback: Generate basic plan from analysis
            return {
                "plan_steps": analysis.get("recommended_actions", []),
                "terraform_required": analysis.get("requires_terraform", False),
                "ansible_required": analysis.get("requires_ansible", False),
                "gcloud_required": analysis.get("requires_gcloud", False),
                "estimated_duration": "5-10 minutes",
                "risk_level": "medium",
                "rollback_plan": ["Manual verification required"],
                "auto_generated": True
            }

    async def execute_plan(
        self,
        agent: SubAgent,
        plan: Dict[str, Any],
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Execute approved plan via sub-agent
        """
        logger.info("executing_plan", agent=agent.value, incident=incident_id)

        agent_url = self.agents.get(agent)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{agent_url}/execute",
                    json={
                        "incident_id": incident_id,
                        "plan": plan
                    },
                    timeout=600.0  # 10 minutes
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "status": "error",
                        "message": f"Execution failed: {response.status_code}"
                    }

        except Exception as e:
            logger.error("execution_error", error=str(e))
            return {"status": "error", "message": str(e)}

    async def resolve_issue(
        self,
        incident_id: str,
        incident_description: str,
        gcp_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main workflow with 2-step HITL

        Returns complete resolution report
        """
        workflow_log = []

        # Publish Kafka event: Incident created
        try:
            await incident_producer.publish_event(
                topic="incident.created",
                event={
                    "incident_id": incident_id,
                    "description": incident_description,
                    "gcp_context": gcp_context,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.warning("kafka_publish_failed", error=str(e))

        # Step 1: LLM + RAG Analysis
        workflow_log.append({
            "step": "llm_analysis",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })

        analysis = self.analyze_issue_with_llm(incident_description, gcp_context)

        workflow_log[-1].update({
            "status": "completed",
            "result": analysis
        })

        # Publish Kafka event: LLM analysis complete
        try:
            await incident_producer.publish_event(
                topic="incident.llm.analysis_complete",
                event={
                    "incident_id": incident_id,
                    "analysis": analysis,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.warning("kafka_publish_failed", error=str(e))

        # Check confidence threshold
        if analysis.get("confidence", 0) < 0.6:
            return {
                "status": "low_confidence",
                "message": "LLM confidence too low for autonomous action",
                "analysis": analysis,
                "workflow_log": workflow_log,
                "requires_manual_review": True
            }

        # Step 2: HITL - Agent Routing Approval
        workflow_log.append({
            "step": "hitl_routing_approval",
            "status": "waiting",
            "timestamp": datetime.now().isoformat()
        })

        routing_approval_id = self.create_hitl_approval_request(
            approval_type="routing",
            incident_id=incident_id,
            data={
                "recommended_agent": analysis["recommended_agent"],
                "issue_category": analysis["issue_category"],
                "confidence": analysis["confidence"],
                "reasoning": analysis.get("reasoning"),
                "alternative_agents": [
                    agent.value for agent in SubAgent
                    if agent.value != analysis["recommended_agent"]
                ]
            }
        )

        workflow_log[-1].update({
            "approval_id": routing_approval_id,
            "status": "pending_human_approval"
        })

        # Publish Kafka event: Approval requested
        try:
            await incident_producer.publish_event(
                topic="incident.approval.requested",
                event={
                    "incident_id": incident_id,
                    "approval_id": routing_approval_id,
                    "approval_type": "routing",
                    "recommended_agent": analysis["recommended_agent"],
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.warning("kafka_publish_failed", error=str(e))

        # Return here - frontend will handle approval
        return {
            "status": "awaiting_routing_approval",
            "approval_id": routing_approval_id,
            "analysis": analysis,
            "workflow_log": workflow_log,
            "next_step": "Human must approve or override agent selection"
        }

    async def continue_after_routing_approval(
        self,
        approval_id: str,
        approved_agent: str,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Continue workflow after routing approval
        """
        approval = self.pending_approvals.get(approval_id)
        if not approval:
            return {"error": "Approval not found"}

        workflow_log = [
            {
                "step": "hitl_routing_approval",
                "status": "approved",
                "selected_agent": approved_agent,
                "timestamp": datetime.now().isoformat()
            }
        ]

        # Step 3: Generate Execution Plan
        workflow_log.append({
            "step": "generate_execution_plan",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })

        agent = SubAgent(approved_agent)
        analysis = approval["data"]

        plan = await self.generate_execution_plan(agent, analysis, incident_id)

        workflow_log[-1].update({
            "status": "completed",
            "plan": plan
        })

        # Step 4: HITL - Execution Plan Approval
        workflow_log.append({
            "step": "hitl_execution_approval",
            "status": "waiting",
            "timestamp": datetime.now().isoformat()
        })

        execution_approval_id = self.create_hitl_approval_request(
            approval_type="execution",
            incident_id=incident_id,
            data={
                "agent": approved_agent,
                "plan": plan,
                "estimated_duration": plan.get("estimated_duration"),
                "risk_level": plan.get("risk_level"),
                "requires_terraform": plan.get("terraform_required"),
                "requires_ansible": plan.get("ansible_required")
            }
        )

        workflow_log[-1].update({
            "approval_id": execution_approval_id,
            "status": "pending_human_approval"
        })

        return {
            "status": "awaiting_execution_approval",
            "approval_id": execution_approval_id,
            "plan": plan,
            "workflow_log": workflow_log,
            "next_step": "Human must approve execution plan"
        }

    async def continue_after_execution_approval(
        self,
        approval_id: str,
        incident_id: str
    ) -> Dict[str, Any]:
        """
        Execute plan after approval
        INDUSTRY-STANDARD: Dynamic generation + GitHub PR + Jira ticket + Kafka events
        """
        approval = self.pending_approvals.get(approval_id)
        if not approval:
            return {"error": "Approval not found"}

        workflow_log = [
            {
                "step": "hitl_execution_approval",
                "status": "approved",
                "timestamp": datetime.now().isoformat()
            }
        ]

        # Publish Kafka event: Execution approved
        try:
            await incident_producer.publish_event(
                topic="incident.execution.approved",
                event={
                    "incident_id": incident_id,
                    "approval_id": approval_id,
                    "timestamp": datetime.now().isoformat(),
                    "agent": approval["data"]["agent"]
                }
            )
        except Exception as e:
            logger.warning("kafka_publish_failed", error=str(e))

        # Get RAG context for solution generation
        rag_context = self.rag.retrieve_context_for_incident(
            incident_description=approval["data"].get("plan", {}).get("incident_description", ""),
            service="gcp",
            limit=5
        )

        # Step 5A: Generate Dynamic Terraform Solution (if required)
        terraform_files = {}
        if approval["data"]["plan"].get("terraform_required"):
            workflow_log.append({
                "step": "generate_terraform_scripts",
                "status": "started",
                "timestamp": datetime.now().isoformat()
            })

            logger.info("generating_dynamic_terraform", incident=incident_id)

            terraform_result = await solution_generator.generate_terraform_solution(
                incident_analysis=approval["data"]["plan"],
                rag_context=rag_context
            )

            if terraform_result.get("success"):
                terraform_files = terraform_result["files"]
                workflow_log[-1].update({
                    "status": "completed",
                    "files_generated": list(terraform_files.keys())
                })
                logger.info("terraform_generated", files=len(terraform_files))
            else:
                workflow_log[-1].update({
                    "status": "failed",
                    "error": terraform_result.get("error")
                })

        # Step 5B: Generate Dynamic Ansible Solution (if required)
        ansible_files = {}
        if approval["data"]["plan"].get("ansible_required"):
            workflow_log.append({
                "step": "generate_ansible_scripts",
                "status": "started",
                "timestamp": datetime.now().isoformat()
            })

            logger.info("generating_dynamic_ansible", incident=incident_id)

            ansible_result = await solution_generator.generate_ansible_solution(
                incident_analysis=approval["data"]["plan"],
                rag_context=rag_context,
                vm_ip=approval["data"]["plan"].get("vm_ip")
            )

            if ansible_result.get("success"):
                ansible_files = ansible_result["files"]
                workflow_log[-1].update({
                    "status": "completed",
                    "files_generated": list(ansible_files.keys())
                })
                logger.info("ansible_generated", files=len(ansible_files))
            else:
                workflow_log[-1].update({
                    "status": "failed",
                    "error": ansible_result.get("error")
                })

        # Step 5C: Create GitHub Pull Request (Industry Standard)
        github_pr = None
        if terraform_files or ansible_files:
            workflow_log.append({
                "step": "create_github_pr",
                "status": "started",
                "timestamp": datetime.now().isoformat()
            })

            logger.info("creating_github_pr", incident=incident_id)

            pr_result = await solution_generator.create_github_pr(
                terraform_files=terraform_files,
                ansible_files=ansible_files,
                incident_id=incident_id,
                description=approval["data"]["plan"].get("incident_description", "")
            )

            if pr_result.get("success"):
                github_pr = {
                    "pr_number": pr_result["pr_number"],
                    "pr_url": pr_result["pr_url"],
                    "branch": pr_result["branch"]
                }
                workflow_log[-1].update({
                    "status": "completed",
                    "pr_url": pr_result["pr_url"]
                })
                logger.info("github_pr_created", pr_url=pr_result["pr_url"])

                # Publish Kafka event: GitHub PR created
                try:
                    await incident_producer.publish_event(
                        topic="incident.github.pr_created",
                        event={
                            "incident_id": incident_id,
                            "pr_url": pr_result["pr_url"],
                            "pr_number": pr_result["pr_number"],
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    logger.warning("kafka_publish_failed", error=str(e))
            else:
                workflow_log[-1].update({
                    "status": "failed",
                    "error": pr_result.get("error")
                })

        # Step 5D: Create Jira Ticket for Test Cases (Industry Standard)
        jira_ticket = None
        workflow_log.append({
            "step": "create_jira_ticket",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })

        logger.info("creating_jira_ticket", incident=incident_id)

        # Find Python files in the generated solution that need tests
        python_files = [
            f for f in list(terraform_files.keys()) + list(ansible_files.keys())
            if f.endswith(".py")
        ]

        if not python_files:
            # Create ticket for the resolver itself
            python_files = ["gcp_issue_resolver.py"]

        jira_result = await solution_generator.create_jira_ticket_for_tests(
            repo=f"{os.getenv('GITHUB_ORG', 'sam2881')}/{os.getenv('GITHUB_REPO', 'test_01')}",
            python_file=python_files[0],
            incident_id=incident_id
        )

        if jira_result.get("success"):
            jira_ticket = {
                "ticket_key": jira_result["ticket_key"],
                "ticket_url": jira_result["ticket_url"]
            }
            workflow_log[-1].update({
                "status": "completed",
                "ticket_url": jira_result["ticket_url"]
            })
            logger.info("jira_ticket_created", ticket_url=jira_result["ticket_url"])

            # Publish Kafka event: Jira ticket created
            try:
                await incident_producer.publish_event(
                    topic="incident.jira.ticket_created",
                    event={
                        "incident_id": incident_id,
                        "ticket_key": jira_result["ticket_key"],
                        "ticket_url": jira_result["ticket_url"],
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logger.warning("kafka_publish_failed", error=str(e))
        else:
            workflow_log[-1].update({
                "status": "failed",
                "error": jira_result.get("error")
            })

        # Step 5E: Execute Plan (Automated)
        workflow_log.append({
            "step": "execute_plan",
            "status": "started",
            "timestamp": datetime.now().isoformat()
        })

        agent = SubAgent(approval["data"]["agent"])
        plan = approval["data"]["plan"]

        # Add generated files to plan
        plan["terraform_files"] = terraform_files
        plan["ansible_files"] = ansible_files

        result = await self.execute_plan(agent, plan, incident_id)

        workflow_log[-1].update({
            "status": "completed" if result.get("status") == "success" else "failed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })

        # Publish Kafka event: Execution completed
        try:
            await incident_producer.publish_event(
                topic="incident.execution.completed",
                event={
                    "incident_id": incident_id,
                    "status": result.get("status"),
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.warning("kafka_publish_failed", error=str(e))

        return {
            "status": "completed",
            "execution_result": result,
            "github_pr": github_pr,
            "jira_ticket": jira_ticket,
            "terraform_files_generated": len(terraform_files),
            "ansible_files_generated": len(ansible_files),
            "workflow_log": workflow_log,
            "incident_id": incident_id
        }


# Global instance
resolver = GCPIssueResolver()
