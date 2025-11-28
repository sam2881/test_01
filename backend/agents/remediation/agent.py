"""
Enterprise Incident Remediation Agent
=====================================
7-Layer AIOps Remediation System with:
1. Runbook Catalog - Metadata-tagged scripts
2. RAG Matching - Vector + Graph hybrid search (Enterprise Pattern)
3. Safety/Governance - Risk-based approvals + LLM validation
4. Controlled Execution - Dry-run mode
5. Pre-Checks - Validation before execution
6. Post-Validation - Verify fix worked
7. Continuous Learning - Feed results back

Enterprise Matching Pattern (Netflix/Uber/Stripe/Google SRE):
Final Score = 0.5*Vector + 0.25*Metadata + 0.15*Graph + 0.10*Safety
"""

import os
import re
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import structlog
from openai import OpenAI

logger = structlog.get_logger()

# Flag to enable/disable enterprise matcher
USE_ENTERPRISE_MATCHER = os.getenv("USE_ENTERPRISE_MATCHER", "true").lower() == "true"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionMode(Enum):
    DRY_RUN = "dry_run"
    SAFE = "safe"
    FULL = "full"


@dataclass
class IncidentContext:
    """Parsed incident context from Step 1"""
    incident_id: str
    service: str
    component: str
    root_cause_hypothesis: str
    severity: str
    symptoms: List[str]
    affected_systems: List[str]
    keywords: List[str]
    confidence: float = 0.0


@dataclass
class RunbookMatch:
    """Matched runbook from Step 2"""
    script_id: str
    name: str
    path: str
    script_type: str
    confidence: float
    match_reason: str
    risk_level: RiskLevel
    requires_approval: bool
    estimated_time_minutes: int
    vector_score: float = 0.0
    graph_score: float = 0.0
    keyword_score: float = 0.0


@dataclass
class RemediationDecision:
    """Decision output from Step 3"""
    incident_id: str
    selected_script: Optional[RunbookMatch]
    all_matches: List[RunbookMatch]
    overall_confidence: float
    risk_assessment: str
    requires_approval: bool
    approvers: List[str]
    reasoning: str
    alternative_scripts: List[RunbookMatch]


@dataclass
class ExecutionStep:
    """Single step in execution plan"""
    step_number: int
    action: str
    command: str
    is_dry_run: bool
    expected_outcome: str
    rollback_command: Optional[str] = None
    timeout_seconds: int = 300


@dataclass
class ExecutionPlan:
    """Full execution plan from Step 4"""
    plan_id: str
    incident_id: str
    script_id: str
    mode: ExecutionMode
    pre_checks: List[ExecutionStep]
    main_steps: List[ExecutionStep]
    post_checks: List[ExecutionStep]
    rollback_steps: List[ExecutionStep]
    estimated_total_time_minutes: int
    requires_change_request: bool


@dataclass
class ValidationResult:
    """Post-validation result from Step 5"""
    validation_id: str
    incident_id: str
    all_checks_passed: bool
    checks: List[Dict[str, Any]]
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]
    improvement_percentage: float
    recommendations: List[str]


class RemediationAgent:
    """
    Enterprise Incident Remediation Agent

    Implements the 5-step workflow:
    1. UNDERSTAND THE INCIDENT
    2. RUNBOOK / SCRIPT MATCHING (Enterprise Hybrid Pattern)
    3. DECISION OUTPUT
    4. EXECUTION PLAN
    5. POST-VALIDATION

    Enterprise Matching Pattern:
    Final Score = 0.5*Vector + 0.25*Metadata + 0.15*Graph + 0.10*Safety
    """

    def __init__(self):
        self.registry_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "runbooks", "registry.json"
        )
        self.runbook_registry = self._load_registry()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize enterprise matcher
        self.enterprise_matcher = None
        if USE_ENTERPRISE_MATCHER:
            try:
                from agents.remediation.enterprise_matcher import EnterpriseHybridMatcher
                self.enterprise_matcher = EnterpriseHybridMatcher(self.registry_path)
                logger.info("enterprise_matcher_enabled",
                           pattern="0.5*Vector + 0.25*Metadata + 0.15*Graph + 0.10*Safety")
            except Exception as e:
                logger.warning("enterprise_matcher_init_failed", error=str(e))
                self.enterprise_matcher = None

        logger.info("remediation_agent_initialized",
                   registry_scripts=len(self.runbook_registry.get("scripts", [])),
                   enterprise_matcher=self.enterprise_matcher is not None)

    def _load_registry(self) -> Dict[str, Any]:
        """Load the runbook registry"""
        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("registry_load_failed", error=str(e))
            return {"scripts": [], "risk_levels": {}}

    async def remediate_incident(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        logs: Optional[str] = None,
        mode: ExecutionMode = ExecutionMode.DRY_RUN
    ) -> Dict[str, Any]:
        """
        Main entry point - Execute full 5-step remediation workflow

        Returns complete remediation response including:
        - Incident understanding
        - Matched runbooks
        - Decision with confidence
        - Execution plan
        - Validation steps
        """
        workflow_id = str(uuid.uuid4())
        logger.info("remediation_workflow_started",
                   workflow_id=workflow_id,
                   incident_id=incident_id,
                   mode=mode.value)

        try:
            # Step 1: Understand the Incident
            context = await self.step1_understand_incident(incident_id, incident_data, logs)

            # Step 2: Runbook/Script Matching
            matches = await self.step2_match_runbooks(context)

            # Step 3: Decision Output
            decision = await self.step3_make_decision(incident_id, context, matches)

            # Step 4: Execution Plan
            execution_plan = None
            if decision.selected_script:
                execution_plan = await self.step4_create_execution_plan(
                    incident_id,
                    decision.selected_script,
                    mode
                )

            # Step 5: Post-Validation Steps
            validation_plan = await self.step5_create_validation_plan(
                incident_id,
                context,
                decision
            )

            result = {
                "workflow_id": workflow_id,
                "incident_id": incident_id,
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "step1_context": asdict(context),
                "step2_matches": [asdict(m) for m in matches],
                "step3_decision": {
                    "selected_script": asdict(decision.selected_script) if decision.selected_script else None,
                    "overall_confidence": decision.overall_confidence,
                    "risk_assessment": decision.risk_assessment,
                    "requires_approval": decision.requires_approval,
                    "approvers": decision.approvers,
                    "reasoning": decision.reasoning,
                    "alternatives": [asdict(a) for a in decision.alternative_scripts[:2]]
                },
                "step4_execution_plan": asdict(execution_plan) if execution_plan else None,
                "step5_validation_plan": validation_plan
            }

            logger.info("remediation_workflow_completed",
                       workflow_id=workflow_id,
                       incident_id=incident_id,
                       selected_script=decision.selected_script.script_id if decision.selected_script else None,
                       confidence=decision.overall_confidence)

            return result

        except Exception as e:
            logger.error("remediation_workflow_failed",
                        workflow_id=workflow_id,
                        incident_id=incident_id,
                        error=str(e))
            return {
                "workflow_id": workflow_id,
                "incident_id": incident_id,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def step1_understand_incident(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        logs: Optional[str] = None
    ) -> IncidentContext:
        """
        Step 1: UNDERSTAND THE INCIDENT

        Extract:
        - Service affected
        - Component involved
        - Root cause hypothesis
        - Severity classification
        - Key symptoms and keywords
        """
        logger.info("step1_understanding_incident", incident_id=incident_id)

        # Combine all text for analysis
        description = incident_data.get("description", "") or ""
        short_desc = incident_data.get("short_description", "") or ""
        category = incident_data.get("category", "") or ""

        full_text = f"{short_desc}\n{description}"
        if logs:
            full_text += f"\n\nLogs:\n{logs}"

        # Use LLM to extract structured information
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert SRE incident analyzer. Extract structured information from the incident.

Return a JSON object with these exact fields:
{
    "service": "name of affected service (e.g., database, kubernetes, nginx, airflow)",
    "component": "specific component (e.g., scheduler, pod, cpu, disk)",
    "root_cause_hypothesis": "your best hypothesis for the root cause",
    "severity": "critical|high|medium|low",
    "symptoms": ["list", "of", "symptoms"],
    "affected_systems": ["list", "of", "systems"],
    "keywords": ["relevant", "technical", "keywords"],
    "confidence": 0.0-1.0
}"""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this incident:

Incident ID: {incident_id}
Category: {category}
Priority: {incident_data.get('priority', 'unknown')}

Description:
{full_text}

Extract the structured information in JSON format."""
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            analysis = json.loads(response.choices[0].message.content)

            return IncidentContext(
                incident_id=incident_id,
                service=analysis.get("service", "unknown"),
                component=analysis.get("component", "unknown"),
                root_cause_hypothesis=analysis.get("root_cause_hypothesis", ""),
                severity=analysis.get("severity", "medium"),
                symptoms=analysis.get("symptoms", []),
                affected_systems=analysis.get("affected_systems", []),
                keywords=analysis.get("keywords", []),
                confidence=analysis.get("confidence", 0.5)
            )

        except Exception as e:
            logger.warning("llm_analysis_failed", error=str(e))
            # Fallback to keyword-based extraction
            return self._extract_context_from_keywords(incident_id, incident_data, full_text)

    def _extract_context_from_keywords(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        text: str
    ) -> IncidentContext:
        """Fallback keyword-based context extraction"""
        text_lower = text.lower()

        # Service detection
        service_map = {
            "database": ["database", "db", "postgresql", "mysql", "sql", "query"],
            "kubernetes": ["pod", "k8s", "kubernetes", "container", "deployment", "crashloop"],
            "nginx": ["nginx", "gateway", "502", "504", "web server"],
            "airflow": ["airflow", "scheduler", "dag", "task", "heartbeat"],
            "redis": ["redis", "cache", "memory"],
            "gcp": ["gcp", "vm", "instance", "compute", "google cloud"]
        }

        detected_service = "unknown"
        for service, keywords in service_map.items():
            if any(kw in text_lower for kw in keywords):
                detected_service = service
                break

        # Component detection
        component_map = {
            "cpu": ["cpu", "processor", "utilization"],
            "memory": ["memory", "ram", "oom", "out of memory"],
            "disk": ["disk", "storage", "space", "filesystem"],
            "scheduler": ["scheduler", "heartbeat", "dag"],
            "pod": ["pod", "container", "crashloop"],
            "network": ["network", "connection", "timeout"]
        }

        detected_component = "unknown"
        for component, keywords in component_map.items():
            if any(kw in text_lower for kw in keywords):
                detected_component = component
                break

        # Extract keywords
        all_keywords = []
        for keywords_list in list(service_map.values()) + list(component_map.values()):
            for kw in keywords_list:
                if kw in text_lower:
                    all_keywords.append(kw)

        return IncidentContext(
            incident_id=incident_id,
            service=detected_service,
            component=detected_component,
            root_cause_hypothesis=f"Issue with {detected_service} {detected_component}",
            severity=self._map_priority_to_severity(incident_data.get("priority", "3")),
            symptoms=[text[:200]],
            affected_systems=[detected_service],
            keywords=list(set(all_keywords)),
            confidence=0.6
        )

    def _map_priority_to_severity(self, priority: str) -> str:
        """Map ServiceNow priority to severity"""
        priority_map = {
            "1": "critical",
            "2": "high",
            "3": "medium",
            "4": "low",
            "5": "low"
        }
        return priority_map.get(str(priority), "medium")

    async def step2_match_runbooks(
        self,
        context: IncidentContext
    ) -> List[RunbookMatch]:
        """
        Step 2: RUNBOOK / SCRIPT MATCHING

        Enterprise Hybrid Matching using (Netflix/Uber/Stripe pattern):
        Final Score = 0.5*Vector + 0.25*Metadata + 0.15*Graph + 0.10*Safety

        Components:
        1. OpenAI text-embedding-3-small - True semantic similarity
        2. Metadata matching - Service, component, keywords, patterns
        3. Neo4j FIXED_BY - Historical success scoring
        4. LLM Safety validation - GPT-4 risk assessment
        """
        logger.info("step2_matching_runbooks",
                   incident_id=context.incident_id,
                   service=context.service,
                   component=context.component,
                   keywords=context.keywords,
                   enterprise_matcher=self.enterprise_matcher is not None)

        # Use Enterprise Hybrid Matcher if available
        if self.enterprise_matcher:
            return await self._enterprise_hybrid_match(context)

        # Fallback to legacy matching
        return await self._legacy_match_runbooks(context)

    async def _enterprise_hybrid_match(
        self,
        context: IncidentContext
    ) -> List[RunbookMatch]:
        """
        Enterprise Hybrid Matching using:
        Final Score = 0.5*Vector + 0.25*Metadata + 0.15*Graph + 0.10*Safety
        """
        logger.info("enterprise_hybrid_match_started",
                   incident_id=context.incident_id,
                   pattern="0.5*Vector + 0.25*Metadata + 0.15*Graph + 0.10*Safety")

        # Convert IncidentContext to dict for the matcher
        incident_context = {
            "incident_id": context.incident_id,
            "service": context.service,
            "component": context.component,
            "root_cause_hypothesis": context.root_cause_hypothesis,
            "severity": context.severity,
            "symptoms": context.symptoms,
            "keywords": context.keywords,
            "affected_systems": context.affected_systems
        }

        # Run hybrid matching
        hybrid_results = self.enterprise_matcher.hybrid_match(incident_context, limit=5)

        # Convert to RunbookMatch objects
        matches = []
        for result in hybrid_results:
            matches.append(RunbookMatch(
                script_id=result.script_id,
                name=result.name,
                path=result.path,
                script_type=result.script_type,
                confidence=result.final_score,
                match_reason="; ".join(result.match_reasons),
                risk_level=RiskLevel(result.risk_level),
                requires_approval=result.requires_approval,
                estimated_time_minutes=result.estimated_time_minutes,
                keyword_score=result.metadata_score,  # Metadata includes keywords
                vector_score=result.vector_score,
                graph_score=result.graph_score
            ))

        if matches:
            top = matches[0]
            logger.info("enterprise_hybrid_match_completed",
                       incident_id=context.incident_id,
                       top_match=top.script_id,
                       final_score=f"{top.confidence:.2%}",
                       vector=f"{top.vector_score:.2%}",
                       metadata=f"{top.keyword_score:.2%}",
                       graph=f"{top.graph_score:.2%}",
                       match_reason=top.match_reason)

        return matches

    async def _legacy_match_runbooks(
        self,
        context: IncidentContext
    ) -> List[RunbookMatch]:
        """
        Legacy matching using keyword/service/pattern scoring
        (fallback when enterprise matcher is unavailable)
        """
        logger.info("legacy_match_started", incident_id=context.incident_id)

        matches = []
        scripts = self.runbook_registry.get("scripts", [])
        logger.info("step2_registry_scripts", count=len(scripts))

        for script in scripts:
            # Calculate composite match score
            keyword_score = self._calculate_keyword_score(context, script)
            service_score = self._calculate_service_score(context, script)
            pattern_score = self._calculate_pattern_score(context, script)

            # Debug logging for score calculation
            logger.debug("step2_score_calc",
                        script_id=script["id"],
                        keyword_score=keyword_score,
                        service_score=service_score,
                        pattern_score=pattern_score)

            # Weighted composite score
            composite_score = (
                keyword_score * 0.35 +
                service_score * 0.40 +
                pattern_score * 0.25
            )

            if composite_score > 0.2:  # Lowered threshold for better recall
                match_reasons = []
                if service_score > 0.3:
                    match_reasons.append(f"service match: {script.get('service')}")
                if keyword_score > 0.2:
                    match_reasons.append(f"keyword match: {', '.join(context.keywords[:3])}")
                if pattern_score > 0.2:
                    match_reasons.append("error pattern match")

                matches.append(RunbookMatch(
                    script_id=script["id"],
                    name=script["name"],
                    path=script["path"],
                    script_type=script["type"],
                    confidence=composite_score,
                    match_reason="; ".join(match_reasons) or "general match",
                    risk_level=RiskLevel(script.get("risk", "medium")),
                    requires_approval=script.get("requires_approval", True),
                    estimated_time_minutes=script.get("estimated_time_minutes", 10),
                    keyword_score=keyword_score,
                    vector_score=0.0,  # Would come from Weaviate
                    graph_score=0.0    # Would come from Neo4j
                ))

        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)

        # Enhance with vector search (simulated)
        matches = await self._enhance_with_vector_search(context, matches)

        # Enhance with graph reasoning (simulated)
        matches = await self._enhance_with_graph_search(context, matches)

        logger.info("step2_matches_found",
                   incident_id=context.incident_id,
                   match_count=len(matches),
                   top_match=matches[0].script_id if matches else None)

        return matches[:5]  # Return top 5 matches

    def _calculate_keyword_score(self, context: IncidentContext, script: Dict) -> float:
        """Calculate keyword overlap score with fuzzy matching"""
        script_keywords = set(kw.lower() for kw in script.get("keywords", []))

        # Split compound keywords into individual words for better matching
        # e.g., "High CPU Usage" -> ["high", "cpu", "usage"]
        context_words = set()
        for kw in context.keywords:
            # Add original keyword (lowercased)
            context_words.add(kw.lower())
            # Split by spaces and add individual words
            for word in kw.lower().split():
                if len(word) > 2:  # Skip very short words
                    context_words.add(word)

        # Also extract words from symptoms
        for symptom in context.symptoms:
            for word in symptom.lower().split():
                if len(word) > 2:
                    context_words.add(word)

        if not script_keywords or not context_words:
            return 0.0

        # Calculate overlap - check both exact match and partial word containment
        overlap = 0
        for script_kw in script_keywords:
            # Exact match
            if script_kw in context_words:
                overlap += 1
            else:
                # Partial match: check if script keyword is contained in any context word or vice versa
                for ctx_word in context_words:
                    if script_kw in ctx_word or ctx_word in script_kw:
                        overlap += 0.5
                        break

        return min(overlap / 3, 1.0)  # Normalize to 0-1

    def _calculate_service_score(self, context: IncidentContext, script: Dict) -> float:
        """Calculate service/component match score"""
        score = 0.0

        script_service = script.get("service", "").lower()
        script_component = script.get("component", "").lower()

        if context.service.lower() == script_service:
            score += 0.6
        elif context.service.lower() in script_service or script_service in context.service.lower():
            score += 0.3

        if context.component.lower() == script_component:
            score += 0.4
        elif context.component.lower() in script_component or script_component in context.component.lower():
            score += 0.2

        return min(score, 1.0)

    def _calculate_pattern_score(self, context: IncidentContext, script: Dict) -> float:
        """Calculate error pattern match score"""
        patterns = script.get("error_patterns", [])
        if not patterns:
            return 0.0

        # Combine all context text including keywords and affected systems
        context_text = f"{context.root_cause_hypothesis} {' '.join(context.symptoms)} {' '.join(context.keywords)} {' '.join(context.affected_systems)} {context.service} {context.component}".lower()

        match_count = 0
        for pattern in patterns:
            try:
                if re.search(pattern.lower(), context_text):
                    match_count += 1
                    continue
            except re.error:
                pass

            # Fallback: split pattern into words and check if all key words are present
            # e.g., "database.*cpu.*high" -> check if "database", "cpu", "high" are all in context
            pattern_words = [w for w in pattern.lower().replace(".*", " ").split() if len(w) > 2]
            if pattern_words:
                found_words = sum(1 for w in pattern_words if w in context_text)
                if found_words >= len(pattern_words) * 0.6:  # 60% word match threshold
                    match_count += 0.7

        return min(match_count / 2, 1.0)

    async def _enhance_with_vector_search(
        self,
        context: IncidentContext,
        matches: List[RunbookMatch]
    ) -> List[RunbookMatch]:
        """Enhance matches with vector similarity from Weaviate"""
        # In production, this would query Weaviate
        # For now, simulate with slight score adjustments
        for match in matches:
            # Simulate vector similarity boost for matching services
            if context.service.lower() in match.script_id.lower():
                match.vector_score = 0.85
                match.confidence = min(match.confidence * 1.1, 1.0)

        return matches

    async def _enhance_with_graph_search(
        self,
        context: IncidentContext,
        matches: List[RunbookMatch]
    ) -> List[RunbookMatch]:
        """Enhance matches with graph reasoning from Neo4j"""
        # In production, this would query Neo4j for:
        # - Past successful remediations
        # - Service dependency paths
        # - Similar incident patterns
        for match in matches:
            if match.risk_level == RiskLevel.LOW:
                match.graph_score = 0.9  # Low risk = high graph confidence
            elif match.risk_level == RiskLevel.MEDIUM:
                match.graph_score = 0.7

        return matches

    async def step3_make_decision(
        self,
        incident_id: str,
        context: IncidentContext,
        matches: List[RunbookMatch]
    ) -> RemediationDecision:
        """
        Step 3: DECISION OUTPUT

        Produce structured decision with:
        - Selected script
        - Confidence score
        - Risk assessment
        - Approval requirements
        - Reasoning
        """
        logger.info("step3_making_decision",
                   incident_id=incident_id,
                   match_count=len(matches))

        if not matches:
            return RemediationDecision(
                incident_id=incident_id,
                selected_script=None,
                all_matches=[],
                overall_confidence=0.0,
                risk_assessment="No matching runbooks found. Manual investigation required.",
                requires_approval=True,
                approvers=["sre-team"],
                reasoning="No automated remediation available for this incident type.",
                alternative_scripts=[]
            )

        # Select best match
        selected = matches[0]
        alternatives = matches[1:3] if len(matches) > 1 else []

        # Determine approval requirements based on risk
        risk_levels = self.runbook_registry.get("risk_levels", {})
        risk_config = risk_levels.get(selected.risk_level.value, {})

        approvers = []
        if selected.risk_level == RiskLevel.CRITICAL:
            approvers = ["senior-sre", "oncall-lead", "manager"]
        elif selected.risk_level == RiskLevel.HIGH:
            approvers = ["senior-sre", "oncall-lead"]
        elif selected.risk_level == RiskLevel.MEDIUM:
            approvers = ["sre-team"]

        # Generate reasoning
        reasoning = self._generate_decision_reasoning(context, selected, alternatives)

        return RemediationDecision(
            incident_id=incident_id,
            selected_script=selected,
            all_matches=matches,
            overall_confidence=selected.confidence,
            risk_assessment=self._assess_risk(selected, context),
            requires_approval=selected.requires_approval,
            approvers=approvers,
            reasoning=reasoning,
            alternative_scripts=alternatives
        )

    def _generate_decision_reasoning(
        self,
        context: IncidentContext,
        selected: RunbookMatch,
        alternatives: List[RunbookMatch]
    ) -> str:
        """Generate human-readable reasoning for the decision"""
        reasoning_parts = [
            f"Selected '{selected.name}' (ID: {selected.script_id}) with {selected.confidence:.0%} confidence.",
            f"Match reason: {selected.match_reason}.",
            f"Risk level: {selected.risk_level.value.upper()}.",
            f"Estimated execution time: {selected.estimated_time_minutes} minutes."
        ]

        if alternatives:
            alt_names = [a.name for a in alternatives]
            reasoning_parts.append(f"Alternatives considered: {', '.join(alt_names)}.")

        if selected.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            reasoning_parts.append("APPROVAL REQUIRED: High-risk operation requires senior approval before execution.")

        return " ".join(reasoning_parts)

    def _assess_risk(self, match: RunbookMatch, context: IncidentContext) -> str:
        """Generate risk assessment"""
        risk_factors = []

        if match.risk_level == RiskLevel.CRITICAL:
            risk_factors.append("Critical infrastructure change")
        if match.risk_level == RiskLevel.HIGH:
            risk_factors.append("Service restart may cause brief downtime")
        if context.severity == "critical":
            risk_factors.append("Incident severity is critical")
        if match.estimated_time_minutes > 10:
            risk_factors.append(f"Extended operation ({match.estimated_time_minutes} min)")

        if not risk_factors:
            return "Low risk. Standard remediation procedure."

        return f"Risk factors: {'; '.join(risk_factors)}"

    async def step4_create_execution_plan(
        self,
        incident_id: str,
        script: RunbookMatch,
        mode: ExecutionMode
    ) -> ExecutionPlan:
        """
        Step 4: EXECUTION PLAN

        Create safe execution plan with:
        - Pre-checks
        - Dry-run steps
        - Main execution steps
        - Post-checks
        - Rollback steps
        """
        logger.info("step4_creating_execution_plan",
                   incident_id=incident_id,
                   script_id=script.script_id,
                   mode=mode.value)

        plan_id = str(uuid.uuid4())

        # Find script config in registry
        script_config = None
        for s in self.runbook_registry.get("scripts", []):
            if s["id"] == script.script_id:
                script_config = s
                break

        if not script_config:
            script_config = {}

        # Build pre-checks
        pre_checks = self._build_pre_checks(script, script_config, mode)

        # Build main execution steps
        main_steps = self._build_main_steps(script, script_config, mode)

        # Build post-checks
        post_checks = self._build_post_checks(script, script_config, mode)

        # Build rollback steps
        rollback_steps = self._build_rollback_steps(script, script_config)

        return ExecutionPlan(
            plan_id=plan_id,
            incident_id=incident_id,
            script_id=script.script_id,
            mode=mode,
            pre_checks=pre_checks,
            main_steps=main_steps,
            post_checks=post_checks,
            rollback_steps=rollback_steps,
            estimated_total_time_minutes=script.estimated_time_minutes,
            requires_change_request=script.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )

    def _build_pre_checks(
        self,
        script: RunbookMatch,
        config: Dict,
        mode: ExecutionMode
    ) -> List[ExecutionStep]:
        """Build pre-execution checks"""
        pre_check_names = config.get("pre_checks", [])
        steps = []
        step_num = 1

        # Always add connectivity check
        steps.append(ExecutionStep(
            step_number=step_num,
            action="Verify target host connectivity",
            command=f"ansible {config.get('service', 'all')} -m ping --check" if mode == ExecutionMode.DRY_RUN else f"ansible {config.get('service', 'all')} -m ping",
            is_dry_run=mode == ExecutionMode.DRY_RUN,
            expected_outcome="All hosts respond to ping"
        ))
        step_num += 1

        for check in pre_check_names:
            if check == "verify_airflow_installed":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Verify Airflow installation",
                    command="which airflow && airflow version",
                    is_dry_run=False,
                    expected_outcome="Airflow binary found and version displayed"
                ))
            elif check == "check_scheduler_status":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Check current scheduler status",
                    command="systemctl status airflow-scheduler",
                    is_dry_run=False,
                    expected_outcome="Scheduler service status retrieved"
                ))
            elif check == "capture_cpu":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Capture current CPU usage",
                    command="top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",
                    is_dry_run=False,
                    expected_outcome="CPU percentage captured for comparison"
                ))
            elif check == "verify_kubectl":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Verify kubectl access",
                    command="kubectl cluster-info",
                    is_dry_run=False,
                    expected_outcome="Kubernetes cluster accessible"
                ))
            elif check == "check_disk_usage":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Check disk usage",
                    command="df -h",
                    is_dry_run=False,
                    expected_outcome="Disk usage information captured"
                ))
            else:
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action=f"Pre-check: {check}",
                    command=f"# {check}",
                    is_dry_run=False,
                    expected_outcome="Check passed"
                ))
            step_num += 1

        return steps

    def _build_main_steps(
        self,
        script: RunbookMatch,
        config: Dict,
        mode: ExecutionMode
    ) -> List[ExecutionStep]:
        """Build main execution steps"""
        steps = []
        is_dry_run = mode == ExecutionMode.DRY_RUN
        check_flag = "--check" if is_dry_run else ""

        if script.script_type == "ansible":
            steps.append(ExecutionStep(
                step_number=1,
                action=f"Execute Ansible playbook: {script.name}",
                command=f"ansible-playbook {script.path} {check_flag} -v",
                is_dry_run=is_dry_run,
                expected_outcome="Playbook executed successfully" if not is_dry_run else "Dry-run completed, changes would be applied",
                rollback_command=f"ansible-playbook {config.get('rollback_script', '')} -v" if config.get('rollback_script') else None,
                timeout_seconds=script.estimated_time_minutes * 60
            ))
        elif script.script_type == "shell":
            steps.append(ExecutionStep(
                step_number=1,
                action=f"Execute shell script: {script.name}",
                command=f"bash -{'n' if is_dry_run else 'x'} {script.path}",
                is_dry_run=is_dry_run,
                expected_outcome="Script executed successfully",
                timeout_seconds=script.estimated_time_minutes * 60
            ))
        elif script.script_type == "terraform":
            if is_dry_run:
                steps.append(ExecutionStep(
                    step_number=1,
                    action="Terraform plan (dry-run)",
                    command=f"terraform plan -out=tfplan {script.path}",
                    is_dry_run=True,
                    expected_outcome="Plan generated, review changes before apply"
                ))
            else:
                steps.append(ExecutionStep(
                    step_number=1,
                    action="Terraform apply",
                    command=f"terraform apply -auto-approve {script.path}",
                    is_dry_run=False,
                    expected_outcome="Infrastructure changes applied",
                    rollback_command="terraform destroy -auto-approve" if config.get('rollback_script') else None
                ))

        return steps

    def _build_post_checks(
        self,
        script: RunbookMatch,
        config: Dict,
        mode: ExecutionMode
    ) -> List[ExecutionStep]:
        """Build post-execution checks"""
        post_check_names = config.get("post_checks", [])
        steps = []
        step_num = 1

        for check in post_check_names:
            if check == "verify_process_running":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Verify process is running",
                    command=f"pgrep -f {config.get('component', 'service')}",
                    is_dry_run=False,
                    expected_outcome="Process running with PID"
                ))
            elif check == "verify_heartbeat":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Verify service heartbeat",
                    command="curl -s localhost:8080/health || echo 'Checking logs...'",
                    is_dry_run=False,
                    expected_outcome="Health check returns OK"
                ))
            elif check == "verify_pods_running":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Verify pods are running",
                    command="kubectl get pods | grep Running",
                    is_dry_run=False,
                    expected_outcome="All pods in Running state"
                ))
            elif check == "verify_cpu_reduced":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Verify CPU has reduced",
                    command="top -bn1 | grep 'Cpu(s)'",
                    is_dry_run=False,
                    expected_outcome="CPU usage below threshold"
                ))
            elif check == "verify_space_freed":
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action="Verify disk space freed",
                    command="df -h",
                    is_dry_run=False,
                    expected_outcome="Disk usage below threshold"
                ))
            else:
                steps.append(ExecutionStep(
                    step_number=step_num,
                    action=f"Post-check: {check}",
                    command=f"# {check}",
                    is_dry_run=False,
                    expected_outcome="Check passed"
                ))
            step_num += 1

        return steps

    def _build_rollback_steps(
        self,
        script: RunbookMatch,
        config: Dict
    ) -> List[ExecutionStep]:
        """Build rollback steps in case of failure"""
        steps = []
        rollback_script = config.get("rollback_script")

        if rollback_script:
            steps.append(ExecutionStep(
                step_number=1,
                action="Execute rollback",
                command=f"ansible-playbook {rollback_script} -v" if script.script_type == "ansible" else f"bash {rollback_script}",
                is_dry_run=False,
                expected_outcome="Service restored to previous state"
            ))

        steps.append(ExecutionStep(
            step_number=len(steps) + 1,
            action="Notify on-call team",
            command="# Page on-call: Rollback executed for incident",
            is_dry_run=False,
            expected_outcome="Team notified"
        ))

        return steps

    async def step5_create_validation_plan(
        self,
        incident_id: str,
        context: IncidentContext,
        decision: RemediationDecision
    ) -> Dict[str, Any]:
        """
        Step 5: POST-VALIDATION

        Define validation steps to verify the fix worked:
        - Metric checks
        - Service health verification
        - User impact validation
        """
        logger.info("step5_creating_validation_plan", incident_id=incident_id)

        validation_checks = []

        # Service-specific validations
        if context.service == "database":
            validation_checks.extend([
                {
                    "name": "Database CPU check",
                    "command": "SELECT pg_stat_get_db_blocks_hit(oid) FROM pg_database WHERE datname = current_database()",
                    "success_criteria": "CPU below 70%",
                    "timeout_seconds": 60
                },
                {
                    "name": "Query performance check",
                    "command": "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'",
                    "success_criteria": "Active queries < 50",
                    "timeout_seconds": 30
                }
            ])
        elif context.service == "kubernetes":
            validation_checks.extend([
                {
                    "name": "Pod status check",
                    "command": "kubectl get pods -o jsonpath='{.items[*].status.phase}'",
                    "success_criteria": "All pods Running",
                    "timeout_seconds": 120
                },
                {
                    "name": "No recent restarts",
                    "command": "kubectl get pods -o jsonpath='{.items[*].status.containerStatuses[*].restartCount}'",
                    "success_criteria": "No new restarts",
                    "timeout_seconds": 30
                }
            ])
        elif context.service == "airflow":
            validation_checks.extend([
                {
                    "name": "Scheduler heartbeat",
                    "command": "airflow jobs check --job-type SchedulerJob --hostname $(hostname)",
                    "success_criteria": "Scheduler heartbeat recent",
                    "timeout_seconds": 60
                },
                {
                    "name": "DAG parsing check",
                    "command": "airflow dags list",
                    "success_criteria": "DAGs listed without errors",
                    "timeout_seconds": 30
                }
            ])

        # Generic validation checks
        validation_checks.append({
            "name": "Incident metric improvement",
            "command": f"# Check that incident symptoms are resolved for {incident_id}",
            "success_criteria": "Key metrics returned to normal",
            "timeout_seconds": 300
        })

        return {
            "validation_id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "checks": validation_checks,
            "recommended_wait_time_minutes": 5,
            "escalation_if_failed": {
                "action": "Page on-call SRE",
                "channel": "#incident-response",
                "message": f"Automated remediation for {incident_id} validation failed. Manual investigation required."
            }
        }


# Global instance
remediation_agent = RemediationAgent()
