"""DSPy modules for ServiceNow agent - optimized prompts and reasoning"""
import dspy
from typing import List, Optional


class IncidentClassifier(dspy.Signature):
    """Classify incident severity and category"""
    incident_description = dspy.InputField(desc="Description of the incident")
    historical_context = dspy.InputField(desc="Similar historical incidents")

    severity = dspy.OutputField(desc="Severity level: P1, P2, P3, P4")
    category = dspy.OutputField(desc="Incident category: Infrastructure, Application, Network, Database, Security")
    urgency = dspy.OutputField(desc="Urgency level: High, Medium, Low")
    reasoning = dspy.OutputField(desc="Reasoning for classification")


class RootCauseAnalyzer(dspy.Signature):
    """Perform root cause analysis for incidents"""
    incident_description = dspy.InputField(desc="Incident description and symptoms")
    service_context = dspy.InputField(desc="Service information and dependencies")
    historical_patterns = dspy.InputField(desc="Historical root cause patterns")

    root_cause = dspy.OutputField(desc="Identified root cause")
    confidence_score = dspy.OutputField(desc="Confidence score 0-100")
    supporting_evidence = dspy.OutputField(desc="Evidence supporting the root cause")
    alternative_causes = dspy.OutputField(desc="Alternative possible causes")


class ResolutionGenerator(dspy.Signature):
    """Generate resolution steps for incidents"""
    incident_description = dspy.InputField()
    root_cause = dspy.InputField()
    runbooks = dspy.InputField(desc="Relevant runbook procedures")

    resolution_steps = dspy.OutputField(desc="Step-by-step resolution procedure")
    estimated_time = dspy.OutputField(desc="Estimated resolution time")
    risk_level = dspy.OutputField(desc="Risk level: Low, Medium, High")
    rollback_plan = dspy.OutputField(desc="Rollback procedure if resolution fails")


class ServiceNowModule(dspy.Module):
    """Complete DSPy module for ServiceNow incident processing"""

    def __init__(self):
        super().__init__()
        self.classifier = dspy.ChainOfThought(IncidentClassifier)
        self.rca_analyzer = dspy.ChainOfThought(RootCauseAnalyzer)
        self.resolution_gen = dspy.ChainOfThought(ResolutionGenerator)

    def forward(
        self,
        incident_description: str,
        historical_context: str,
        service_context: str,
        runbooks: str
    ):
        """Process incident through classification, RCA, and resolution generation"""

        # Step 1: Classify incident
        classification = self.classifier(
            incident_description=incident_description,
            historical_context=historical_context
        )

        # Step 2: Root cause analysis
        rca = self.rca_analyzer(
            incident_description=incident_description,
            service_context=service_context,
            historical_patterns=historical_context
        )

        # Step 3: Generate resolution
        resolution = self.resolution_gen(
            incident_description=incident_description,
            root_cause=rca.root_cause,
            runbooks=runbooks
        )

        return dspy.Prediction(
            severity=classification.severity,
            category=classification.category,
            urgency=classification.urgency,
            classification_reasoning=classification.reasoning,
            root_cause=rca.root_cause,
            confidence_score=rca.confidence_score,
            supporting_evidence=rca.supporting_evidence,
            alternative_causes=rca.alternative_causes,
            resolution_steps=resolution.resolution_steps,
            estimated_time=resolution.estimated_time,
            risk_level=resolution.risk_level,
            rollback_plan=resolution.rollback_plan
        )


class IncidentVerifier(dspy.Signature):
    """Verify that incident resolution is complete and correct"""
    incident_description = dspy.InputField()
    resolution_applied = dspy.InputField()
    post_resolution_state = dspy.InputField()

    is_resolved = dspy.OutputField(desc="Boolean: true if incident is resolved")
    verification_details = dspy.OutputField(desc="Details of verification checks")
    remaining_issues = dspy.OutputField(desc="Any remaining issues or concerns")
