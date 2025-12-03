"""
LLM-Based Intelligence for Incident Resolution
Uses OpenAI to understand incidents and match remediation scripts
"""
import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
import structlog

logger = structlog.get_logger()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =============================================================================
# LLM-Based Incident Analysis
# =============================================================================

def analyze_incident_with_llm(incident: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to deeply analyze an incident and extract:
    - Root cause
    - Affected components
    - Severity level
    - Recommended remediation approach
    - Required parameters
    """
    try:
        prompt = f"""You are an expert SRE analyzing a production incident. Analyze this incident and provide structured insights:

INCIDENT:
ID: {incident.get('incident_id')}
Title: {incident.get('short_description')}
Description: {incident.get('description')}
Category: {incident.get('category', 'unknown')}
Priority: {incident.get('priority', 'unknown')}

TASK: Analyze this incident and provide:
1. Root cause analysis
2. Affected services/components
3. Required remediation actions
4. Technical parameters needed for remediation
5. Risk assessment

Respond in JSON format:
{{
  "root_cause": "...",
  "affected_components": ["component1", "component2"],
  "service_type": "gcp|kubernetes|database|network|application",
  "severity": "critical|high|medium|low",
  "remediation_approach": "restart|scale|repair|rollback|configure",
  "required_params": {{
    "instance_name": "extracted value or null",
    "zone": "extracted value or null",
    "namespace": "extracted value or null",
    "pod_name": "extracted value or null"
  }},
  "risk_level": "low|medium|high|critical",
  "confidence": 0.0-1.0
}}
"""

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert SRE with deep knowledge of cloud infrastructure, Kubernetes, databases, and incident remediation. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)
        logger.info("llm_analysis_completed", incident_id=incident.get('incident_id'), analysis=analysis)
        return analysis

    except Exception as e:
        logger.error("llm_analysis_failed", error=str(e))
        # Return fallback analysis
        return {
            "root_cause": "Analysis failed - using fallback",
            "affected_components": [],
            "service_type": "unknown",
            "severity": "medium",
            "remediation_approach": "investigate",
            "required_params": {},
            "risk_level": "medium",
            "confidence": 0.3
        }


def match_scripts_with_llm(
    incident: Dict[str, Any],
    available_scripts: List[Dict[str, Any]],
    incident_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Use LLM to intelligently match incident to remediation scripts
    """
    try:
        # Prepare script summaries for LLM
        scripts_info = []
        for script in available_scripts:
            scripts_info.append({
                "script_id": script.get("script_id"),
                "name": script.get("name"),
                "description": script.get("description"),
                "type": script.get("type"),
                "service": script.get("service"),
                "action": script.get("action"),
                "keywords": script.get("keywords", []),
                "risk_level": script.get("risk_level", "medium")
            })

        prompt = f"""You are an expert SRE matching incidents to remediation scripts.

INCIDENT ANALYSIS:
{json.dumps(incident_analysis, indent=2)}

INCIDENT DETAILS:
ID: {incident.get('incident_id')}
Title: {incident.get('short_description')}
Description: {incident.get('description')}

AVAILABLE REMEDIATION SCRIPTS:
{json.dumps(scripts_info, indent=2)}

TASK: Match the BEST remediation scripts for this incident. Consider:
1. Root cause alignment
2. Service type match
3. Remediation approach compatibility
4. Risk level appropriateness
5. Parameter availability

Rank the top 5 scripts by relevance and provide confidence scores.

Respond in JSON format:
{{
  "matches": [
    {{
      "script_id": "...",
      "confidence": 0.0-1.0,
      "reasoning": "why this script matches",
      "extracted_params": {{
        "param_name": "extracted_value"
      }},
      "risk_assessment": "low|medium|high|critical",
      "recommended": true|false
    }}
  ]
}}
"""

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert SRE with deep knowledge of incident remediation. Match incidents to remediation scripts with high precision. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        matches = result.get("matches", [])

        logger.info("llm_matching_completed",
                   incident_id=incident.get('incident_id'),
                   match_count=len(matches))

        return matches

    except Exception as e:
        logger.error("llm_matching_failed", error=str(e))
        return []


def generate_execution_plan_with_llm(
    incident: Dict[str, Any],
    script: Dict[str, Any],
    extracted_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use LLM to generate detailed execution plan
    """
    try:
        prompt = f"""You are an expert SRE creating an execution plan for incident remediation.

INCIDENT:
{json.dumps(incident, indent=2)}

SELECTED SCRIPT:
{json.dumps(script, indent=2)}

EXTRACTED PARAMETERS:
{json.dumps(extracted_params, indent=2)}

TASK: Create a detailed execution plan including:
1. Pre-execution validation steps
2. Execution steps
3. Post-execution verification
4. Rollback plan if needed
5. Risk mitigation strategies

Respond in JSON format:
{{
  "plan_id": "unique_id",
  "pre_checks": [
    {{"step": "...", "expected": "...", "validation": "..."}}
  ],
  "execution_steps": [
    {{"step": "...", "command": "...", "expected_outcome": "..."}}
  ],
  "verification_steps": [
    {{"step": "...", "check": "...", "success_criteria": "..."}}
  ],
  "rollback_plan": [
    {{"step": "...", "action": "..."}}
  ],
  "estimated_duration": "5-10 minutes",
  "risk_level": "low|medium|high|critical",
  "approval_required": true|false,
  "safety_score": 0.0-1.0
}}
"""

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert SRE creating detailed, safe execution plans. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        plan = json.loads(response.choices[0].message.content)
        logger.info("execution_plan_generated", plan_id=plan.get("plan_id"))
        return plan

    except Exception as e:
        logger.error("execution_plan_generation_failed", error=str(e))
        return {
            "plan_id": "fallback_plan",
            "pre_checks": [],
            "execution_steps": [{"step": "Execute script", "command": script.get("github_workflow"), "expected_outcome": "Success"}],
            "verification_steps": [],
            "rollback_plan": [],
            "estimated_duration": "unknown",
            "risk_level": "medium",
            "approval_required": True,
            "safety_score": 0.5
        }


def validate_plan_safety_with_llm(
    incident: Dict[str, Any],
    plan: Dict[str, Any],
    script: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use LLM to validate execution plan safety
    """
    try:
        prompt = f"""You are a senior SRE reviewing an execution plan for safety.

INCIDENT:
{json.dumps(incident, indent=2)}

EXECUTION PLAN:
{json.dumps(plan, indent=2)}

SCRIPT:
{json.dumps(script, indent=2)}

TASK: Perform a safety review and determine:
1. Is this plan safe to execute?
2. What are the potential risks?
3. Are there any missing safeguards?
4. Should this require human approval?
5. Any recommendations for improvement?

Respond in JSON format:
{{
  "safe_to_execute": true|false,
  "safety_score": 0.0-1.0,
  "risks": ["risk1", "risk2"],
  "missing_safeguards": ["safeguard1"],
  "requires_approval": true|false,
  "approval_reason": "...",
  "recommendations": ["rec1", "rec2"],
  "final_decision": "approve|reject|needs_review"
}}
"""

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a senior SRE performing safety reviews. Be conservative and prioritize safety. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        validation = json.loads(response.choices[0].message.content)
        logger.info("safety_validation_completed", decision=validation.get("final_decision"))
        return validation

    except Exception as e:
        logger.error("safety_validation_failed", error=str(e))
        return {
            "safe_to_execute": False,
            "safety_score": 0.5,
            "risks": ["Validation failed"],
            "missing_safeguards": [],
            "requires_approval": True,
            "approval_reason": "Safety validation failed - manual review required",
            "recommendations": [],
            "final_decision": "needs_review"
        }


def extract_parameters_with_llm(
    incident: Dict[str, Any],
    required_params: List[str]
) -> Dict[str, Any]:
    """
    Use LLM to extract required parameters from incident description
    """
    try:
        prompt = f"""You are an expert at extracting technical parameters from incident descriptions.

INCIDENT:
Title: {incident.get('short_description')}
Description: {incident.get('description')}

REQUIRED PARAMETERS:
{json.dumps(required_params)}

TASK: Extract the values for these parameters from the incident description.
Look for:
- instance_name: GCP VM instance names (e.g., test-vm-01, my-instance)
- zone: GCP zones (e.g., us-central1-a, us-east1-b)
- namespace: Kubernetes namespaces
- pod_name: Kubernetes pod names
- deployment_name: Kubernetes deployment names
- project: GCP project ID

Be precise and extract exact values mentioned in the text.

Respond in JSON format:
{{
  "extracted": {{
    "param_name": "exact_value" or null
  }},
  "confidence": 0.0-1.0
}}
"""

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an expert at extracting technical parameters. Be precise and only extract values explicitly mentioned. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        extracted = result.get("extracted", {})

        logger.info("parameters_extracted",
                   incident_id=incident.get('incident_id'),
                   extracted=extracted)

        return extracted

    except Exception as e:
        logger.error("parameter_extraction_failed", error=str(e))
        return {}
