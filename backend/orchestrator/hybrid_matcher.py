"""
Hybrid Matching Algorithm for Enterprise Script Selection

This module implements the enterprise-grade script matching algorithm that combines:
1. Vector Search (RAG) - 50% weight
2. Metadata Scoring - 25% weight
3. Graph Context (Neo4j) - 15% weight
4. Safety Scoring - 10% weight

Minimum final score required: 0.75
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Optional imports for advanced features
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a script match operation."""
    script_id: str
    script_name: str
    script_path: str
    script_type: str
    vector_score: float
    metadata_score: float
    graph_score: float
    safety_score: float
    final_score: float
    confidence: str
    requires_approval: bool
    extracted_inputs: Dict[str, Any]
    match_explanation: str


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NO_MATCH = "no_match"


class HybridMatcher:
    """
    Enterprise Hybrid Matching Algorithm.

    Uses a weighted combination of:
    - Vector similarity (semantic understanding)
    - Metadata matching (keywords, patterns)
    - Graph context (service relationships)
    - Safety scoring (risk assessment)
    """

    def __init__(self, registry: Dict):
        self.registry = registry
        self.scripts = registry.get("scripts", [])
        self.matching_config = registry.get("matching_algorithm", {})

        # Weights from registry config
        weights = self.matching_config.get("weights", {})
        self.vector_weight = weights.get("vector_score", 0.50)
        self.metadata_weight = weights.get("metadata_score", 0.25)
        self.graph_weight = weights.get("graph_score", 0.15)
        self.safety_weight = weights.get("safety_score", 0.10)

        # Thresholds
        self.minimum_final_score = self.matching_config.get("minimum_final_score", 0.75)
        self.minimum_vector_score = self.matching_config.get("minimum_vector_score", 0.70)

        # Initialize OpenAI client if available
        self.openai_client = None
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            try:
                self.openai_client = OpenAI()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")

        # Initialize Neo4j if available
        self.neo4j_driver = None
        if NEO4J_AVAILABLE:
            try:
                neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                neo4j_user = os.getenv("NEO4J_USER", "neo4j")
                neo4j_password = os.getenv("NEO4J_PASSWORD", "adminadmin")
                self.neo4j_driver = GraphDatabase.driver(
                    neo4j_uri,
                    auth=(neo4j_user, neo4j_password)
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Neo4j: {e}")

    def match_incident(
        self,
        incident_description: str,
        incident_metadata: Dict = None,
        environment: str = "development",
        max_results: int = 5
    ) -> List[MatchResult]:
        """
        Match an incident to the best remediation scripts.

        Args:
            incident_description: The incident text/description
            incident_metadata: Additional metadata (service, component, severity, etc.)
            environment: Target environment for execution
            max_results: Maximum number of results to return

        Returns:
            List of MatchResult objects sorted by final score
        """
        incident_metadata = incident_metadata or {}
        results = []

        for script in self.scripts:
            # Skip scripts not allowed in this environment
            if environment not in script.get("environment_allowed", []):
                continue

            # Calculate all scores
            vector_score = self._calculate_vector_score(incident_description, script)
            metadata_score = self._calculate_metadata_score(incident_description, incident_metadata, script)
            graph_score = self._calculate_graph_score(incident_metadata, script)
            safety_score = self._calculate_safety_score(script, environment)

            # Calculate weighted final score
            final_score = (
                vector_score * self.vector_weight +
                metadata_score * self.metadata_weight +
                graph_score * self.graph_weight +
                safety_score * self.safety_weight
            )

            # Determine confidence level
            if final_score >= 0.85:
                confidence = ConfidenceLevel.HIGH
            elif final_score >= 0.75:
                confidence = ConfidenceLevel.MEDIUM
            elif final_score >= 0.60:
                confidence = ConfidenceLevel.LOW
            else:
                confidence = ConfidenceLevel.NO_MATCH

            # Extract input parameters from incident
            extracted_inputs = self._extract_inputs(incident_description, incident_metadata, script)

            # Determine if approval is required
            requires_approval = not script.get("auto_approve", False) or script.get("risk_level") in ["high", "critical"]

            # Generate explanation
            explanation = self._generate_match_explanation(
                script, vector_score, metadata_score, graph_score, safety_score, final_score
            )

            results.append(MatchResult(
                script_id=script.get("id"),
                script_name=script.get("name"),
                script_path=script.get("path"),
                script_type=script.get("type"),
                vector_score=round(vector_score, 3),
                metadata_score=round(metadata_score, 3),
                graph_score=round(graph_score, 3),
                safety_score=round(safety_score, 3),
                final_score=round(final_score, 3),
                confidence=confidence.value,
                requires_approval=requires_approval,
                extracted_inputs=extracted_inputs,
                match_explanation=explanation
            ))

        # Sort by final score
        results.sort(key=lambda x: x.final_score, reverse=True)

        # Filter by minimum score and limit
        results = [r for r in results if r.final_score >= self.minimum_final_score][:max_results]

        return results

    def _calculate_vector_score(self, incident_text: str, script: Dict) -> float:
        """
        Calculate semantic similarity using vector embeddings.

        Falls back to keyword-based matching if OpenAI is unavailable.
        """
        if self.openai_client:
            try:
                return self._calculate_openai_similarity(incident_text, script)
            except Exception as e:
                logger.warning(f"OpenAI vector scoring failed: {e}")

        # Fallback to keyword-based scoring
        return self._calculate_keyword_similarity(incident_text, script)

    def _calculate_openai_similarity(self, incident_text: str, script: Dict) -> float:
        """Calculate similarity using OpenAI embeddings."""
        # Create script text for embedding
        script_text = f"{script.get('name', '')} {script.get('description', '')} {' '.join(script.get('keywords', []))}"

        # Get embeddings
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[incident_text, script_text]
        )

        # Calculate cosine similarity
        incident_embedding = response.data[0].embedding
        script_embedding = response.data[1].embedding

        dot_product = sum(a * b for a, b in zip(incident_embedding, script_embedding))
        magnitude_a = sum(a * a for a in incident_embedding) ** 0.5
        magnitude_b = sum(b * b for b in script_embedding) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        similarity = dot_product / (magnitude_a * magnitude_b)
        return max(0.0, min(1.0, similarity))

    def _calculate_keyword_similarity(self, incident_text: str, script: Dict) -> float:
        """Calculate similarity based on keyword matching."""
        text_lower = incident_text.lower()
        score = 0.0
        max_score = 0.0

        # Check keywords
        keywords = script.get("keywords", [])
        for keyword in keywords:
            max_score += 1.0
            if keyword.lower() in text_lower:
                score += 1.0
            elif any(word in text_lower for word in keyword.lower().split("_")):
                score += 0.5

        # Check error patterns
        error_patterns = script.get("error_patterns", [])
        for pattern in error_patterns:
            max_score += 2.0
            try:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score += 2.0
            except re.error:
                if pattern.lower() in text_lower:
                    score += 1.5

        # Check name and description
        name = script.get("name", "").lower()
        description = script.get("description", "").lower()

        name_words = set(name.split())
        text_words = set(text_lower.split())
        name_overlap = len(name_words & text_words) / max(len(name_words), 1)
        score += name_overlap * 2
        max_score += 2

        if max_score == 0:
            return 0.5  # Default score if no matching criteria

        return min(1.0, score / max_score)

    def _calculate_metadata_score(
        self,
        incident_text: str,
        incident_metadata: Dict,
        script: Dict
    ) -> float:
        """
        Calculate score based on metadata matching.

        Matches: service, component, category, action, tags
        """
        score = 0.0
        matches = 0
        total_checks = 0

        text_lower = incident_text.lower()

        # Service matching
        if incident_metadata.get("service"):
            total_checks += 1
            if incident_metadata["service"].lower() == script.get("service", "").lower():
                score += 1.0
                matches += 1
            elif script.get("service", "").lower() in text_lower:
                score += 0.5

        # Component matching
        if incident_metadata.get("component"):
            total_checks += 1
            if incident_metadata["component"].lower() == script.get("component", "").lower():
                score += 1.0
                matches += 1
            elif script.get("component", "").lower() in text_lower:
                score += 0.5

        # Category matching
        if incident_metadata.get("category"):
            total_checks += 1
            if incident_metadata["category"].lower() == script.get("category", "").lower():
                score += 1.0
                matches += 1

        # Action matching from text
        action = script.get("action", "")
        if action and action.lower() in text_lower:
            score += 0.5
            total_checks += 1

        # Tag matching
        script_tags = set(t.lower() for t in script.get("tags", []))
        incident_tags = set(t.lower() for t in incident_metadata.get("tags", []))
        if script_tags and incident_tags:
            total_checks += 1
            tag_overlap = len(script_tags & incident_tags) / len(script_tags)
            score += tag_overlap
            if tag_overlap > 0:
                matches += 1

        # Check tags against incident text
        for tag in script_tags:
            if tag in text_lower:
                score += 0.2

        if total_checks == 0:
            # Fall back to text-based scoring
            return self._text_metadata_score(text_lower, script)

        return min(1.0, score / max(total_checks, 1))

    def _text_metadata_score(self, text_lower: str, script: Dict) -> float:
        """Score based on service/component/action appearing in text."""
        score = 0.0

        service = script.get("service", "").lower()
        component = script.get("component", "").lower()
        action = script.get("action", "").lower()
        category = script.get("category", "").lower()

        if service and service in text_lower:
            score += 0.3
        if component and component in text_lower:
            score += 0.3
        if action and action in text_lower:
            score += 0.2
        if category and category in text_lower:
            score += 0.2

        return min(1.0, score)

    def _calculate_graph_score(self, incident_metadata: Dict, script: Dict) -> float:
        """
        Calculate score based on graph relationships (Neo4j).

        Considers:
        - Service dependencies
        - Component relationships
        - Historical remediation patterns
        """
        if not self.neo4j_driver:
            # Fallback to static dependency checking
            return self._calculate_static_dependency_score(incident_metadata, script)

        try:
            with self.neo4j_driver.session() as session:
                # Query for service relationships
                service = incident_metadata.get("service", script.get("service", ""))
                if not service:
                    return 0.5

                result = session.run("""
                    MATCH (s:Service {name: $service})-[:REMEDIATES_WITH]->(script:Script {id: $script_id})
                    RETURN count(*) as relationship_count
                """, service=service, script_id=script.get("id"))

                record = result.single()
                if record and record["relationship_count"] > 0:
                    return 1.0

                # Check for component relationships
                result = session.run("""
                    MATCH (s:Service {name: $service})-[:HAS_COMPONENT]->(c:Component)
                    -[:REMEDIATES_WITH]->(script:Script {id: $script_id})
                    RETURN count(*) as relationship_count
                """, service=service, script_id=script.get("id"))

                record = result.single()
                if record and record["relationship_count"] > 0:
                    return 0.8

                # Check historical success
                result = session.run("""
                    MATCH (i:Incident)-[:RESOLVED_BY]->(script:Script {id: $script_id})
                    WHERE i.service = $service
                    RETURN count(*) as success_count
                """, service=service, script_id=script.get("id"))

                record = result.single()
                if record:
                    success_count = record["success_count"]
                    if success_count > 10:
                        return 0.9
                    elif success_count > 5:
                        return 0.7
                    elif success_count > 0:
                        return 0.6

                return 0.5  # Default when no graph data

        except Exception as e:
            logger.warning(f"Graph scoring failed: {e}")
            return 0.5

    def _calculate_static_dependency_score(self, incident_metadata: Dict, script: Dict) -> float:
        """Calculate dependency score without Neo4j."""
        score = 0.5  # Default

        # Check if script dependencies match incident context
        dependencies = script.get("dependencies", [])
        incident_service = incident_metadata.get("service", "").lower()

        for dep in dependencies:
            dep_lower = dep.lower()
            if incident_service in dep_lower:
                score += 0.2
            if "access" in dep_lower or "admin" in dep_lower:
                # Assume access is available
                score += 0.1

        return min(1.0, score)

    def _calculate_safety_score(self, script: Dict, environment: str) -> float:
        """
        Calculate safety score based on risk level and environment.

        Higher score = safer to execute
        """
        risk_level = script.get("risk_level", "medium")

        # Base scores by risk level
        risk_scores = {
            "low": 1.0,
            "medium": 0.8,
            "high": 0.6,
            "critical": 0.4
        }

        base_score = risk_scores.get(risk_level, 0.5)

        # Penalize high-risk in production
        if environment == "production":
            if risk_level == "critical":
                base_score *= 0.5
            elif risk_level == "high":
                base_score *= 0.7

        # Bonus for having rollback
        if script.get("rollback_script"):
            base_score = min(1.0, base_score + 0.1)

        # Bonus for pre/post checks
        if script.get("pre_checks") and script.get("post_checks"):
            base_score = min(1.0, base_score + 0.05)

        return base_score

    def _extract_inputs(
        self,
        incident_text: str,
        incident_metadata: Dict,
        script: Dict
    ) -> Dict[str, Any]:
        """
        Extract required input parameters from incident text and metadata.

        Uses regex patterns and AI (if available) to extract values.
        """
        extracted = {}
        required_inputs = script.get("required_inputs", [])

        # Common extraction patterns
        patterns = {
            "instance_name": [
                r"instance[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?",
                r"vm[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?",
                r"server[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?"
            ],
            "zone": [
                r"zone[:\s]+['\"]?([a-z]+-[a-z0-9]+-[a-z])['\"]?",
                r"in\s+([a-z]+-[a-z0-9]+-[a-z])"
            ],
            "namespace": [
                r"namespace[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?",
                r"ns[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?"
            ],
            "pod_name": [
                r"pod[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?",
                r"pod\s+([a-zA-Z0-9\-_]+)"
            ],
            "deployment_name": [
                r"deployment[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?",
                r"deploy\s+([a-zA-Z0-9\-_]+)"
            ],
            "target_host": [
                r"host[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?",
                r"server[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?"
            ],
            "db_host": [
                r"database.*host[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?",
                r"db.*server[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?"
            ],
            "db_name": [
                r"database[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?",
                r"db[:\s]+['\"]?([a-zA-Z0-9\-_]+)['\"]?"
            ],
            "redis_host": [
                r"redis.*host[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?",
                r"cache.*server[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?"
            ],
            "airflow_host": [
                r"airflow.*host[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?",
                r"scheduler.*server[:\s]+['\"]?([a-zA-Z0-9\.\-_]+)['\"]?"
            ]
        }

        text_lower = incident_text.lower()

        for input_name in required_inputs:
            # First check metadata
            if input_name in incident_metadata:
                extracted[input_name] = incident_metadata[input_name]
                continue

            # Try regex patterns
            if input_name in patterns:
                for pattern in patterns[input_name]:
                    match = re.search(pattern, incident_text, re.IGNORECASE)
                    if match:
                        extracted[input_name] = match.group(1)
                        break

            # Special handling for specific inputs
            if input_name not in extracted:
                if input_name == "zone" and incident_metadata.get("zone"):
                    extracted["zone"] = incident_metadata["zone"]
                elif input_name == "namespace" and "default" not in extracted:
                    extracted["namespace"] = "default"  # Safe default

        return extracted

    def _generate_match_explanation(
        self,
        script: Dict,
        vector_score: float,
        metadata_score: float,
        graph_score: float,
        safety_score: float,
        final_score: float
    ) -> str:
        """Generate a human-readable explanation of the match."""
        explanations = []

        # Vector/semantic match
        if vector_score >= 0.8:
            explanations.append(f"Strong semantic match ({vector_score:.0%})")
        elif vector_score >= 0.6:
            explanations.append(f"Good semantic match ({vector_score:.0%})")
        else:
            explanations.append(f"Weak semantic match ({vector_score:.0%})")

        # Metadata match
        if metadata_score >= 0.8:
            explanations.append(f"service/component match ({metadata_score:.0%})")

        # Safety
        risk = script.get("risk_level", "medium")
        if risk == "low":
            explanations.append("low-risk operation")
        elif risk == "critical":
            explanations.append("CRITICAL risk - requires approval")

        # Keywords
        keywords = script.get("keywords", [])[:3]
        if keywords:
            explanations.append(f"keywords: {', '.join(keywords)}")

        return f"Script '{script.get('name')}' selected: " + "; ".join(explanations)

    def get_mandatory_json_output(
        self,
        incident_id: str,
        incident_description: str,
        match_result: MatchResult
    ) -> Dict:
        """
        Generate the MANDATORY JSON OUTPUT format as specified in requirements.

        This is the standardized output format for script selection.
        """
        return {
            "incident_id": incident_id,
            "selected_script": {
                "id": match_result.script_id,
                "name": match_result.script_name,
                "path": match_result.script_path,
                "type": match_result.script_type,
                "scores": {
                    "vector_score": match_result.vector_score,
                    "metadata_score": match_result.metadata_score,
                    "graph_score": match_result.graph_score,
                    "safety_score": match_result.safety_score,
                    "final_score": match_result.final_score
                },
                "confidence": match_result.confidence,
                "requires_approval": match_result.requires_approval
            },
            "extracted_inputs": match_result.extracted_inputs,
            "explanation": match_result.match_explanation,
            "execution_ready": (
                match_result.final_score >= self.minimum_final_score and
                match_result.confidence in ["high", "medium"]
            )
        }


def create_matcher(registry: Dict) -> HybridMatcher:
    """Factory function to create a HybridMatcher instance."""
    return HybridMatcher(registry)
