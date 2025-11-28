"""
Enterprise-Grade Hybrid Script Matcher
======================================
Implements Netflix/Uber/Stripe/Google SRE pattern:

Final Score = 0.5 * Vector_Similarity + 0.25 * Metadata_Match + 0.15 * Graph_FIXED_BY + 0.10 * LLM_Safety

Components:
1. OpenAI Embeddings (text-embedding-3-small) - True semantic similarity
2. Weaviate Vector DB - Fast vector search with metadata filtering
3. Neo4j Graph DB - FIXED_BY relationship scoring (historical success)
4. LLM Safety Layer - GPT-4 validation before selection
"""

import os
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import structlog
from openai import OpenAI

logger = structlog.get_logger()


@dataclass
class EmbeddingResult:
    """Result from embedding generation"""
    text: str
    embedding: List[float]
    model: str
    token_count: int


@dataclass
class VectorSearchResult:
    """Result from vector similarity search"""
    script_id: str
    name: str
    similarity_score: float  # 0.0 - 1.0
    metadata: Dict[str, Any]


@dataclass
class GraphScoreResult:
    """Result from Neo4j graph scoring"""
    script_id: str
    fixed_by_count: int  # Number of times this script fixed similar incidents
    avg_resolution_time: float  # Average resolution time in minutes
    success_rate: float  # 0.0 - 1.0
    last_used: Optional[str]
    graph_score: float  # 0.0 - 1.0


@dataclass
class SafetyCheckResult:
    """Result from LLM safety validation"""
    script_id: str
    is_safe: bool
    safety_score: float  # 0.0 - 1.0
    concerns: List[str]
    recommendation: str


@dataclass
class HybridMatchResult:
    """Final hybrid match result with all scores"""
    script_id: str
    name: str
    path: str
    script_type: str

    # Individual scores
    vector_score: float  # 50% weight
    metadata_score: float  # 25% weight
    graph_score: float  # 15% weight
    safety_score: float  # 10% weight

    # Final composite score
    final_score: float

    # Additional context
    match_reasons: List[str]
    risk_level: str
    requires_approval: bool
    estimated_time_minutes: int
    historical_success_count: int
    safety_concerns: List[str]


class EnterpriseHybridMatcher:
    """
    Enterprise-grade hybrid matcher using:
    - OpenAI embeddings for semantic similarity
    - Weaviate for vector search
    - Neo4j for graph-based FIXED_BY scoring
    - GPT-4 for safety validation
    """

    # Scoring weights (Netflix/Uber/Stripe pattern)
    VECTOR_WEIGHT = 0.50
    METADATA_WEIGHT = 0.25
    GRAPH_WEIGHT = 0.15
    SAFETY_WEIGHT = 0.10

    # Embedding model
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    def __init__(self, registry_path: str = None):
        """Initialize the enterprise matcher"""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Load registry
        if registry_path is None:
            registry_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "runbooks", "registry.json"
            )
        self.registry_path = registry_path
        self.registry = self._load_registry()

        # Cache for runbook embeddings
        self.runbook_embeddings: Dict[str, List[float]] = {}

        # Import clients (lazy loading to avoid circular imports)
        self._weaviate_client = None
        self._neo4j_client = None

        logger.info("enterprise_matcher_initialized",
                   registry_scripts=len(self.registry.get("scripts", [])),
                   embedding_model=self.EMBEDDING_MODEL)

    def _load_registry(self) -> Dict[str, Any]:
        """Load runbook registry"""
        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("registry_load_failed", error=str(e))
            return {"scripts": [], "risk_levels": {}}

    @property
    def weaviate_client(self):
        """Lazy-load Weaviate client"""
        if self._weaviate_client is None:
            from utils.weaviate_client import weaviate_rag_client
            self._weaviate_client = weaviate_rag_client
        return self._weaviate_client

    @property
    def neo4j_client(self):
        """Lazy-load Neo4j client"""
        if self._neo4j_client is None:
            from utils.neo4j_client import neo4j_graph_client
            self._neo4j_client = neo4j_graph_client
        return self._neo4j_client

    # =========================================================================
    # STEP 1: OpenAI Embedding Generation
    # =========================================================================

    def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding using OpenAI text-embedding-3-small

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with vector
        """
        try:
            # Clean and truncate text (max 8191 tokens for this model)
            clean_text = text[:32000]  # Approximate character limit

            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=clean_text
            )

            embedding = response.data[0].embedding
            token_count = response.usage.total_tokens

            logger.debug("embedding_generated",
                        text_length=len(text),
                        token_count=token_count)

            return EmbeddingResult(
                text=clean_text[:500],  # Store truncated text for reference
                embedding=embedding,
                model=self.EMBEDDING_MODEL,
                token_count=token_count
            )

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Return zero vector as fallback
            return EmbeddingResult(
                text=text[:500],
                embedding=[0.0] * self.EMBEDDING_DIMENSIONS,
                model=self.EMBEDDING_MODEL,
                token_count=0
            )

    def generate_runbook_embedding(self, script: Dict[str, Any]) -> List[float]:
        """
        Generate embedding for a runbook script

        Creates rich text representation combining:
        - Name and description
        - Keywords and tags
        - Error patterns
        - Service and component
        """
        # Build rich text for embedding
        parts = [
            f"Runbook: {script.get('name', '')}",
            f"Service: {script.get('service', '')}",
            f"Component: {script.get('component', '')}",
            f"Action: {script.get('action', '')}",
            f"Keywords: {', '.join(script.get('keywords', []))}",
            f"Error patterns: {', '.join(script.get('error_patterns', []))}",
            f"Tags: {', '.join(script.get('tags', []))}"
        ]

        embedding_text = " | ".join(parts)
        result = self.generate_embedding(embedding_text)
        return result.embedding

    def precompute_runbook_embeddings(self) -> int:
        """
        Precompute embeddings for all runbooks in registry

        Returns:
            Number of embeddings generated
        """
        scripts = self.registry.get("scripts", [])
        count = 0

        for script in scripts:
            script_id = script.get("id")
            if script_id not in self.runbook_embeddings:
                embedding = self.generate_runbook_embedding(script)
                self.runbook_embeddings[script_id] = embedding
                count += 1

        logger.info("runbook_embeddings_precomputed", count=count)
        return count

    # =========================================================================
    # STEP 2: Vector Similarity Search
    # =========================================================================

    def calculate_cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0.0 - 1.0)
        """
        arr1 = np.array(vec1)
        arr2 = np.array(vec2)

        # Handle zero vectors
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = np.dot(arr1, arr2) / (norm1 * norm2)
        return float(max(0.0, min(1.0, similarity)))

    def vector_search(
        self,
        incident_text: str,
        service_filter: Optional[str] = None,
        limit: int = 10
    ) -> List[VectorSearchResult]:
        """
        Search for similar runbooks using vector similarity

        Args:
            incident_text: Incident description/symptoms
            service_filter: Optional service to filter by
            limit: Maximum results

        Returns:
            List of VectorSearchResult
        """
        # Generate incident embedding
        incident_embedding = self.generate_embedding(incident_text).embedding

        # Ensure runbook embeddings are computed
        if not self.runbook_embeddings:
            self.precompute_runbook_embeddings()

        results = []
        scripts = self.registry.get("scripts", [])

        for script in scripts:
            script_id = script.get("id")

            # Apply flexible service filter - allow partial matches
            if service_filter:
                script_service = script.get("service", "").lower()
                filter_lower = service_filter.lower()

                # Check for any word overlap (fuzzy matching)
                filter_words = set(w for w in filter_lower.split() if len(w) > 2)
                service_words = set(w for w in script_service.split() if len(w) > 2)

                # Allow if: exact match, partial containment, or word overlap
                is_match = (
                    script_service == filter_lower or
                    script_service in filter_lower or
                    filter_lower in script_service or
                    bool(filter_words & service_words) or
                    any(w in filter_lower for w in script_service.split())
                )

                if not is_match:
                    continue

            # Get runbook embedding
            if script_id in self.runbook_embeddings:
                runbook_embedding = self.runbook_embeddings[script_id]
            else:
                runbook_embedding = self.generate_runbook_embedding(script)
                self.runbook_embeddings[script_id] = runbook_embedding

            # Calculate similarity
            similarity = self.calculate_cosine_similarity(
                incident_embedding,
                runbook_embedding
            )

            results.append(VectorSearchResult(
                script_id=script_id,
                name=script.get("name", ""),
                similarity_score=similarity,
                metadata={
                    "service": script.get("service"),
                    "component": script.get("component"),
                    "risk": script.get("risk"),
                    "type": script.get("type"),
                    "path": script.get("path")
                }
            ))

        # Sort by similarity
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        logger.info("vector_search_completed",
                   query_length=len(incident_text),
                   service_filter=service_filter,
                   results=len(results[:limit]))

        return results[:limit]

    # =========================================================================
    # STEP 3: Metadata Matching
    # =========================================================================

    def calculate_metadata_score(
        self,
        incident_context: Dict[str, Any],
        script: Dict[str, Any]
    ) -> float:
        """
        Calculate metadata matching score

        Considers:
        - Service/component match
        - Keyword overlap
        - Error pattern matching
        - Tag relevance

        Args:
            incident_context: Extracted incident context
            script: Runbook script metadata

        Returns:
            Metadata score (0.0 - 1.0)
        """
        score = 0.0

        # Service match (0.3)
        incident_service = str(incident_context.get("service", "")).lower()
        script_service = str(script.get("service", "")).lower()

        if incident_service and script_service:
            if incident_service == script_service:
                score += 0.30
            elif incident_service in script_service or script_service in incident_service:
                score += 0.15

        # Component match (0.2)
        incident_component = str(incident_context.get("component", "")).lower()
        script_component = str(script.get("component", "")).lower()

        if incident_component and script_component:
            if incident_component == script_component:
                score += 0.20
            elif incident_component in script_component or script_component in incident_component:
                score += 0.10

        # Keyword overlap (0.25)
        incident_keywords = set()
        for kw in incident_context.get("keywords", []):
            incident_keywords.add(kw.lower())
            for word in kw.lower().split():
                if len(word) > 2:
                    incident_keywords.add(word)

        script_keywords = set(kw.lower() for kw in script.get("keywords", []))

        if incident_keywords and script_keywords:
            overlap = len(incident_keywords & script_keywords)
            keyword_score = min(overlap / 3, 1.0) * 0.25
            score += keyword_score

        # Error pattern matching (0.25)
        context_text = " ".join([
            str(incident_context.get("root_cause_hypothesis", "")),
            " ".join(incident_context.get("symptoms", [])),
            " ".join(incident_context.get("keywords", [])),
            str(incident_context.get("service", "")),
            str(incident_context.get("component", ""))
        ]).lower()

        patterns = script.get("error_patterns", [])
        pattern_matches = 0

        for pattern in patterns:
            try:
                if re.search(pattern.lower(), context_text):
                    pattern_matches += 1
            except re.error:
                # Fallback to word matching
                pattern_words = [w for w in pattern.lower().replace(".*", " ").split() if len(w) > 2]
                if pattern_words:
                    found = sum(1 for w in pattern_words if w in context_text)
                    if found >= len(pattern_words) * 0.6:
                        pattern_matches += 0.7

        if patterns:
            pattern_score = min(pattern_matches / len(patterns), 1.0) * 0.25
            score += pattern_score

        return min(score, 1.0)

    # =========================================================================
    # STEP 4: Neo4j Graph FIXED_BY Scoring
    # =========================================================================

    def get_graph_score(
        self,
        script_id: str,
        service: Optional[str] = None
    ) -> GraphScoreResult:
        """
        Get graph-based score from Neo4j FIXED_BY relationships

        Queries:
        - Number of times this script successfully fixed incidents
        - Average resolution time
        - Success rate
        - Recent usage

        Args:
            script_id: Runbook script ID
            service: Optional service filter

        Returns:
            GraphScoreResult
        """
        try:
            # Query successful remediations from Neo4j
            successful_remediations = self.neo4j_client.find_successful_remediations(
                service=service,
                limit=50
            )

            # Calculate metrics for this script
            script_remediations = [
                r for r in successful_remediations
                if r.get("script_id") == script_id
            ]

            fixed_count = len(script_remediations)

            if fixed_count > 0:
                # Calculate average resolution time
                resolution_times = [
                    r.get("resolution_time", 0)
                    for r in script_remediations
                    if r.get("resolution_time")
                ]
                avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0

                # Calculate success rate (based on verified status)
                success_rate = fixed_count / max(len(successful_remediations), 1)

                # Get last used date
                last_used = script_remediations[0].get("executed_at") if script_remediations else None

                # Calculate graph score
                # Higher score for more fixes, faster resolution, recent usage
                base_score = min(fixed_count / 10, 0.5)  # Up to 0.5 for 10+ fixes
                time_bonus = max(0, 0.3 - (avg_resolution / 60) * 0.1)  # Bonus for fast resolution
                recency_bonus = 0.2 if last_used else 0.0  # Bonus for recent usage

                graph_score = min(base_score + time_bonus + recency_bonus, 1.0)
            else:
                avg_resolution = 0
                success_rate = 0.0
                last_used = None
                graph_score = 0.1  # Baseline score for untested scripts

            return GraphScoreResult(
                script_id=script_id,
                fixed_by_count=fixed_count,
                avg_resolution_time=avg_resolution,
                success_rate=success_rate,
                last_used=last_used,
                graph_score=graph_score
            )

        except Exception as e:
            logger.warning("graph_score_failed", script_id=script_id, error=str(e))
            # Return baseline score on error
            return GraphScoreResult(
                script_id=script_id,
                fixed_by_count=0,
                avg_resolution_time=0,
                success_rate=0.0,
                last_used=None,
                graph_score=0.1
            )

    # =========================================================================
    # STEP 5: LLM Safety Validation
    # =========================================================================

    def validate_safety(
        self,
        script: Dict[str, Any],
        incident_context: Dict[str, Any]
    ) -> SafetyCheckResult:
        """
        Validate script safety using GPT-4

        Checks:
        - Risk appropriateness for incident severity
        - Potential side effects
        - Required approvals
        - Rollback capability

        Args:
            script: Runbook script metadata
            incident_context: Incident context

        Returns:
            SafetyCheckResult
        """
        try:
            prompt = f"""You are a Site Reliability Engineer safety validator.
Analyze if this remediation script is safe to run for the given incident.

INCIDENT CONTEXT:
- Service: {incident_context.get('service', 'unknown')}
- Component: {incident_context.get('component', 'unknown')}
- Severity: {incident_context.get('severity', 'medium')}
- Symptoms: {', '.join(incident_context.get('symptoms', []))}
- Root cause hypothesis: {incident_context.get('root_cause_hypothesis', 'unknown')}

REMEDIATION SCRIPT:
- Name: {script.get('name', 'unknown')}
- ID: {script.get('id', 'unknown')}
- Type: {script.get('type', 'unknown')}
- Service target: {script.get('service', 'unknown')}
- Component target: {script.get('component', 'unknown')}
- Action: {script.get('action', 'unknown')}
- Risk level: {script.get('risk', 'unknown')}
- Requires approval: {script.get('requires_approval', True)}
- Has rollback: {bool(script.get('rollback_script'))}

Respond with JSON:
{{
    "is_safe": true/false,
    "safety_score": 0.0-1.0,
    "concerns": ["list", "of", "concerns"],
    "recommendation": "brief recommendation"
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an SRE safety validator. Respond only with JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            return SafetyCheckResult(
                script_id=script.get("id", ""),
                is_safe=result.get("is_safe", True),
                safety_score=result.get("safety_score", 0.8),
                concerns=result.get("concerns", []),
                recommendation=result.get("recommendation", "")
            )

        except Exception as e:
            logger.warning("safety_validation_failed", error=str(e))
            # Return safe result with baseline score on error
            return SafetyCheckResult(
                script_id=script.get("id", ""),
                is_safe=True,
                safety_score=0.7,  # Conservative baseline
                concerns=["Safety validation unavailable"],
                recommendation="Proceed with caution"
            )

    # =========================================================================
    # MAIN: Hybrid Match Function
    # =========================================================================

    def hybrid_match(
        self,
        incident_context: Dict[str, Any],
        limit: int = 5
    ) -> List[HybridMatchResult]:
        """
        Main hybrid matching function using enterprise pattern

        Formula: 0.5*Vector + 0.25*Metadata + 0.15*Graph + 0.10*Safety

        Args:
            incident_context: Parsed incident context with:
                - incident_id
                - service
                - component
                - root_cause_hypothesis
                - severity
                - symptoms
                - keywords

            limit: Maximum results to return

        Returns:
            List of HybridMatchResult sorted by final_score
        """
        logger.info("hybrid_match_started",
                   incident_id=incident_context.get("incident_id"),
                   service=incident_context.get("service"))

        # Build search text from incident context
        search_text = " ".join([
            str(incident_context.get("root_cause_hypothesis", "")),
            " ".join(incident_context.get("symptoms", [])),
            " ".join(incident_context.get("keywords", [])),
            str(incident_context.get("service", "")),
            str(incident_context.get("component", ""))
        ])

        # Step 1: Vector search
        vector_results = self.vector_search(
            incident_text=search_text,
            service_filter=incident_context.get("service"),
            limit=limit * 2  # Get more candidates for filtering
        )

        # Get all scripts for additional processing
        scripts_map = {s["id"]: s for s in self.registry.get("scripts", [])}

        results = []

        for vr in vector_results:
            script = scripts_map.get(vr.script_id)
            if not script:
                continue

            # Step 2: Metadata score
            metadata_score = self.calculate_metadata_score(incident_context, script)

            # Step 3: Graph score (FIXED_BY)
            graph_result = self.get_graph_score(
                vr.script_id,
                incident_context.get("service")
            )

            # Step 4: Safety validation (only for top candidates)
            if vr.similarity_score > 0.3 or metadata_score > 0.3:
                safety_result = self.validate_safety(script, incident_context)
            else:
                # Skip safety check for low-scoring candidates
                safety_result = SafetyCheckResult(
                    script_id=vr.script_id,
                    is_safe=True,
                    safety_score=0.5,
                    concerns=[],
                    recommendation=""
                )

            # Calculate final hybrid score
            final_score = (
                self.VECTOR_WEIGHT * vr.similarity_score +
                self.METADATA_WEIGHT * metadata_score +
                self.GRAPH_WEIGHT * graph_result.graph_score +
                self.SAFETY_WEIGHT * safety_result.safety_score
            )

            # Build match reasons
            match_reasons = []
            if vr.similarity_score > 0.5:
                match_reasons.append(f"High semantic similarity ({vr.similarity_score:.0%})")
            if metadata_score > 0.4:
                match_reasons.append(f"Strong metadata match ({metadata_score:.0%})")
            if graph_result.fixed_by_count > 0:
                match_reasons.append(f"Previously fixed {graph_result.fixed_by_count} similar incidents")
            if safety_result.is_safe and safety_result.safety_score > 0.8:
                match_reasons.append("Validated safe for this incident")

            results.append(HybridMatchResult(
                script_id=vr.script_id,
                name=script.get("name", ""),
                path=script.get("path", ""),
                script_type=script.get("type", ""),

                vector_score=vr.similarity_score,
                metadata_score=metadata_score,
                graph_score=graph_result.graph_score,
                safety_score=safety_result.safety_score,

                final_score=final_score,

                match_reasons=match_reasons if match_reasons else ["General match"],
                risk_level=script.get("risk", "medium"),
                requires_approval=script.get("requires_approval", True),
                estimated_time_minutes=script.get("estimated_time_minutes", 10),
                historical_success_count=graph_result.fixed_by_count,
                safety_concerns=safety_result.concerns
            ))

        # Sort by final score
        results.sort(key=lambda x: x.final_score, reverse=True)

        # Log results
        if results:
            top = results[0]
            logger.info("hybrid_match_completed",
                       incident_id=incident_context.get("incident_id"),
                       top_match=top.script_id,
                       final_score=f"{top.final_score:.2%}",
                       vector_score=f"{top.vector_score:.2%}",
                       metadata_score=f"{top.metadata_score:.2%}",
                       graph_score=f"{top.graph_score:.2%}",
                       safety_score=f"{top.safety_score:.2%}")
        else:
            logger.warning("hybrid_match_no_results",
                          incident_id=incident_context.get("incident_id"))

        return results[:limit]

    def explain_match(self, result: HybridMatchResult) -> str:
        """
        Generate human-readable explanation of the match

        Args:
            result: HybridMatchResult to explain

        Returns:
            Explanation string
        """
        explanation = f"""
## Runbook Match Analysis: {result.name}

**Final Score: {result.final_score:.1%}**

### Score Breakdown (Netflix/Uber/Stripe Pattern):
| Component | Weight | Score | Contribution |
|-----------|--------|-------|--------------|
| Vector Similarity | 50% | {result.vector_score:.1%} | {result.vector_score * 0.5:.1%} |
| Metadata Match | 25% | {result.metadata_score:.1%} | {result.metadata_score * 0.25:.1%} |
| Graph FIXED_BY | 15% | {result.graph_score:.1%} | {result.graph_score * 0.15:.1%} |
| LLM Safety | 10% | {result.safety_score:.1%} | {result.safety_score * 0.1:.1%} |

### Match Reasons:
{chr(10).join('- ' + r for r in result.match_reasons)}

### Details:
- **Script ID**: {result.script_id}
- **Type**: {result.script_type}
- **Risk Level**: {result.risk_level.upper()}
- **Requires Approval**: {'Yes' if result.requires_approval else 'No'}
- **Estimated Time**: {result.estimated_time_minutes} minutes
- **Historical Successes**: {result.historical_success_count}

### Safety Assessment:
{'⚠️ Concerns: ' + ', '.join(result.safety_concerns) if result.safety_concerns else '✅ No safety concerns identified'}
"""
        return explanation.strip()


# Global instance
enterprise_matcher = EnterpriseHybridMatcher()
