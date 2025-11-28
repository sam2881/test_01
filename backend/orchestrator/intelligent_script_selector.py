"""
Intelligent Script Selector
Uses LLM + RAG to select best pre-existing script (NOT generate dynamically)

This is the INDUSTRY-STANDARD approach:
1. Maintain library of pre-tested Terraform/Ansible scripts
2. Use RAG (Weaviate) to find semantically similar scripts
3. Use LLM to select best match and extract parameters
4. Execute the proven, tested script
"""
import os
import sys
import json
import weaviate
from typing import Dict, List, Optional
from datetime import datetime
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = structlog.get_logger()


class IntelligentScriptSelector:
    """
    Intelligent selection of pre-existing scripts using LLM + RAG

    NOT dynamic generation - selects from curated, tested library
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4", temperature=0.1)
        self.weaviate_client = weaviate.Client(
            url=os.getenv("WEAVIATE_URL", "http://localhost:8081")
        )

    async def select_scripts(
        self,
        incident_analysis: Dict,
        gcp_context: Dict
    ) -> Dict:
        """
        Select best matching scripts from pre-existing library

        Returns:
        {
            "terraform_script": {
                "script_name": "start_vm_simple.tf",
                "script_content": "terraform {...}",
                "parameters": {
                    "vm_name": "test-vm-01",
                    "zone": "us-central1-a",
                    "project_id": "my-project"
                },
                "confidence": 0.95,
                "reason": "This script starts stopped VMs..."
            },
            "ansible_script": {
                "script_name": "restart_nginx.yml",
                "script_content": "---...",
                "parameters": {
                    "vm_ip": "${terraform.vm_ip}",
                    "ansible_user": "ansible"
                },
                "confidence": 0.90,
                "reason": "This script restarts nginx..."
            },
            "execution_order": ["terraform", "ansible"],
            "overall_confidence": 0.92
        }
        """
        logger.info("selecting_scripts_from_library",
                   issue=incident_analysis.get("issue_category"))

        # Step 1: RAG - Retrieve candidate scripts from Weaviate
        terraform_candidates = await self._search_scripts(
            query_text=self._build_query_text(incident_analysis, gcp_context),
            script_type="terraform",
            issue_category=incident_analysis.get("issue_category"),
            limit=5
        )

        ansible_candidates = await self._search_scripts(
            query_text=self._build_query_text(incident_analysis, gcp_context),
            script_type="ansible",
            issue_category=incident_analysis.get("issue_category"),
            limit=5
        )

        logger.info("rag_retrieved_candidates",
                   terraform_count=len(terraform_candidates),
                   ansible_count=len(ansible_candidates))

        # Step 2: LLM - Select best match and extract parameters
        selection = await self._llm_select_best(
            incident_analysis=incident_analysis,
            gcp_context=gcp_context,
            terraform_candidates=terraform_candidates,
            ansible_candidates=ansible_candidates
        )

        logger.info("llm_selected_scripts",
                   terraform=selection.get("terraform_script", {}).get("script_name"),
                   ansible=selection.get("ansible_script", {}).get("script_name"),
                   confidence=selection.get("overall_confidence"))

        return selection

    def _build_query_text(self, incident_analysis: Dict, gcp_context: Dict) -> str:
        """Build semantic search query from incident"""
        return f"""
Issue: {incident_analysis.get('issue_category')}
Description: {incident_analysis.get('root_cause', '')}
GCP Resource: {gcp_context.get('vm_name', '')} in {gcp_context.get('zone', '')}
Actions needed: {', '.join(incident_analysis.get('recommended_actions', []))}
        """.strip()

    async def _search_scripts(
        self,
        query_text: str,
        script_type: str,
        issue_category: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search Weaviate for matching scripts using semantic search
        """
        try:
            result = (
                self.weaviate_client.query
                .get("InfrastructureScript", [
                    "script_name",
                    "script_type",
                    "purpose",
                    "script_content",
                    "parameters",
                    "issue_types",
                    "gcp_resources",
                    "risk_level",
                    "tested_scenarios",
                    "success_count",
                    "prerequisites",
                    "success_criteria"
                ])
                .with_near_text({
                    "concepts": [query_text, issue_category],
                    "certainty": 0.6  # Minimum semantic similarity
                })
                .with_where({
                    "path": ["script_type"],
                    "operator": "Equal",
                    "valueText": script_type
                })
                .with_limit(limit)
                .do()
            )

            scripts = result.get("data", {}).get("Get", {}).get("InfrastructureScript", [])

            logger.info("weaviate_search_complete",
                       script_type=script_type,
                       results_count=len(scripts))

            return scripts

        except Exception as e:
            logger.error("weaviate_search_error", error=str(e))
            return []

    async def _llm_select_best(
        self,
        incident_analysis: Dict,
        gcp_context: Dict,
        terraform_candidates: List[Dict],
        ansible_candidates: List[Dict]
    ) -> Dict:
        """
        LLM analyzes candidate scripts and selects the best match

        Key: LLM extracts parameters from incident context for the selected script
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert DevOps engineer selecting the BEST pre-existing script for incident resolution.

Your task:
1. Analyze the incident details
2. Review the candidate scripts retrieved by RAG
3. Select the BEST matching script for each type (Terraform/Ansible)
4. Extract the required parameters from the incident context
5. Provide confidence score and reasoning

IMPORTANT:
- ONLY select from the provided candidates
- DO NOT suggest creating new scripts
- Extract parameters from incident context (vm_name, zone, etc.)
- If no good match, set selected: false

Respond in JSON format:
{{
    "terraform_script": {{
        "selected": true/false,
        "script_name": "start_vm_simple.tf",
        "reason": "This script handles VM down issues by starting stopped instances",
        "parameters": {{
            "vm_name": "test-incident-vm-01",
            "zone": "us-central1-a",
            "project_id": "agent-ai-test-461120"
        }},
        "confidence": 0.95,
        "risk_assessment": "Low risk - script has been tested 15 times successfully"
    }},
    "ansible_script": {{
        "selected": true/false,
        "script_name": "restart_nginx.yml",
        "reason": "After VM starts, this script restarts nginx and verifies HTTP 200",
        "parameters": {{
            "vm_ip": "${{terraform.vm_ip}}",
            "ansible_user": "ansible"
        }},
        "confidence": 0.90,
        "risk_assessment": "Low risk - tested 12 times"
    }},
    "execution_order": ["terraform", "ansible"],
    "overall_confidence": 0.92,
    "reasoning": "Combined approach: Terraform starts VM, Ansible restarts services"
}}

Incident Analysis:
{incident_analysis}

GCP Context:
{gcp_context}

Terraform Candidates (ranked by RAG similarity):
{terraform_candidates}

Ansible Candidates (ranked by RAG similarity):
{ansible_candidates}
"""),
            ("human", "Select the best pre-existing scripts for this incident.")
        ])

        chain = prompt | self.llm

        try:
            response = chain.invoke({
                "incident_analysis": json.dumps(incident_analysis, indent=2),
                "gcp_context": json.dumps(gcp_context, indent=2),
                "terraform_candidates": json.dumps(
                    self._format_candidates(terraform_candidates),
                    indent=2
                ),
                "ansible_candidates": json.dumps(
                    self._format_candidates(ansible_candidates),
                    indent=2
                )
            })

            selection = json.loads(response.content)

            # Add full script content to selection
            if selection.get("terraform_script", {}).get("selected"):
                tf_script = self._find_script_by_name(
                    terraform_candidates,
                    selection["terraform_script"]["script_name"]
                )
                if tf_script:
                    selection["terraform_script"]["script_content"] = tf_script.get("script_content", "")
                    selection["terraform_script"]["prerequisites"] = tf_script.get("prerequisites", "")
                    selection["terraform_script"]["success_criteria"] = tf_script.get("success_criteria", "")

            if selection.get("ansible_script", {}).get("selected"):
                ans_script = self._find_script_by_name(
                    ansible_candidates,
                    selection["ansible_script"]["script_name"]
                )
                if ans_script:
                    selection["ansible_script"]["script_content"] = ans_script.get("script_content", "")
                    selection["ansible_script"]["prerequisites"] = ans_script.get("prerequisites", "")
                    selection["ansible_script"]["success_criteria"] = ans_script.get("success_criteria", "")

            return selection

        except Exception as e:
            logger.error("llm_selection_error", error=str(e))
            return {
                "terraform_script": {"selected": False},
                "ansible_script": {"selected": False},
                "overall_confidence": 0.0,
                "error": str(e)
            }

    def _format_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Format candidates for LLM (remove script_content to reduce tokens)"""
        formatted = []
        for candidate in candidates:
            formatted.append({
                "script_name": candidate.get("script_name"),
                "purpose": candidate.get("purpose"),
                "issue_types": candidate.get("issue_types"),
                "gcp_resources": candidate.get("gcp_resources"),
                "parameters": candidate.get("parameters"),
                "risk_level": candidate.get("risk_level"),
                "tested_scenarios": candidate.get("tested_scenarios"),
                "success_count": candidate.get("success_count", 0),
                "prerequisites": candidate.get("prerequisites"),
                "success_criteria": candidate.get("success_criteria")
            })
        return formatted

    def _find_script_by_name(self, candidates: List[Dict], script_name: str) -> Optional[Dict]:
        """Find script by name in candidates list"""
        for candidate in candidates:
            if candidate.get("script_name") == script_name:
                return candidate
        return None


# Global instance
script_selector = IntelligentScriptSelector()
