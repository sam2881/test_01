"""
Main Reasoning Engine - Enterprise-grade incident analysis and resolution orchestration
Implements the 8-step workflow with RAG + Graph DB integration
"""
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import openai
import structlog

from utils.weaviate_client import weaviate_rag_client
from utils.neo4j_client import neo4j_graph_client
from utils.kafka_client import kafka_client
from utils.postgres_client import postgres_client

logger = structlog.get_logger()

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


class ReasoningEngine:
    """
    Main reasoning engine for incident analysis and resolution
    Follows the 8-step enterprise workflow
    """

    # Agent capabilities mapping
    AGENT_CAPABILITIES = {
        "airflow-agent": {
            "name": "Airflow Agent",
            "capabilities": ["DAG failures", "task errors", "scheduling issues", "dependency problems"],
            "keywords": ["airflow", "dag", "task", "scheduler", "executor", "pipeline"],
            "priority": ["critical", "high"]
        },
        "platform-agent": {
            "name": "Platform Agent",
            "capabilities": ["GCP", "Kubernetes", "VM", "network", "infrastructure"],
            "keywords": ["gcp", "kubernetes", "k8s", "vm", "instance", "pod", "node", "cluster", "cpu", "memory"],
            "priority": ["critical", "high", "medium"]
        },
        "data-agent": {
            "name": "Data Agent",
            "capabilities": ["SQL", "ETL", "data pipeline", "database", "query"],
            "keywords": ["sql", "database", "query", "etl", "data", "table", "postgres", "mysql", "bigquery"],
            "priority": ["high", "medium"]
        },
        "fallback-agent": {
            "name": "Fallback Agent",
            "capabilities": ["general", "unclassified", "unknown"],
            "keywords": [],
            "priority": ["low"]
        }
    }

    def __init__(self):
        """Initialize reasoning engine"""
        self.rag_client = weaviate_rag_client
        self.graph_client = neo4j_graph_client

    async def step1_main_agent_analysis(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        logs: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Step 1: Main Agent Analysis
        Deep contextual analysis using RAG + Graph DB + LLM

        Returns:
            {
                "classification": str,
                "category": str,
                "severity": str,
                "reasoning": str,
                "confidence": float,
                "recommended_agent": str,
                "rag_context": List[Dict],
                "graph_context": Dict,
                "key_signals": List[str]
            }
        """
        logger.info("step1_analysis_start", incident_id=incident_id)

        try:
            # Extract incident details
            short_desc = incident_data.get("short_description", "")
            description = incident_data.get("description", "")
            category = incident_data.get("category", "unknown")
            priority = incident_data.get("priority", "medium")

            # Build analysis query
            analysis_query = f"{short_desc}\n{description}"
            if logs:
                analysis_query += f"\n\nLogs:\n{logs[:1000]}"  # Limit log size

            # Step 1a: RAG - Get similar past incidents
            similar_incidents = self.rag_client.search_similar_incidents(
                query=analysis_query,
                limit=3,
                category=category if category != "unknown" else None
            )

            # Step 1b: Graph DB - Get pattern insights
            graph_patterns = self.graph_client.find_similar_incident_patterns(
                category=category,
                priority=priority,
                limit=5
            )

            # Step 1c: LLM Analysis
            llm_analysis = await self._llm_deep_analysis(
                incident_data=incident_data,
                logs=logs,
                similar_incidents=similar_incidents,
                graph_patterns=graph_patterns,
                metadata=metadata
            )

            # Step 1d: Determine recommended agent
            recommended_agent, agent_confidence, agent_reasoning = self._select_agent(
                llm_analysis=llm_analysis,
                incident_data=incident_data,
                priority=priority
            )

            result = {
                "classification": llm_analysis.get("classification", "unknown"),
                "category": llm_analysis.get("category", category),
                "severity": llm_analysis.get("severity", "medium"),
                "reasoning": llm_analysis.get("reasoning", ""),
                "confidence": llm_analysis.get("confidence", 0.5),
                "recommended_agent": recommended_agent,
                "agent_confidence": agent_confidence,
                "agent_reasoning": agent_reasoning,
                "rag_context": similar_incidents,
                "graph_context": {"patterns": graph_patterns},
                "key_signals": llm_analysis.get("key_signals", []),
                "root_cause_hypothesis": llm_analysis.get("root_cause_hypothesis", ""),
                "timestamp": datetime.now().isoformat()
            }

            # Log to Kafka
            kafka_client.publish_event(
                topic="agent.events",
                event={
                    "incident_id": incident_id,
                    "step": "step1_analysis",
                    "type": "analysis_complete",
                    "data": result
                },
                key=incident_id
            )

            logger.info(
                "step1_analysis_complete",
                incident_id=incident_id,
                recommended_agent=recommended_agent,
                confidence=agent_confidence
            )

            return result

        except Exception as e:
            logger.error("step1_analysis_error", incident_id=incident_id, error=str(e))
            return {
                "error": str(e),
                "classification": "error",
                "recommended_agent": "fallback-agent",
                "confidence": 0.0
            }

    async def _llm_deep_analysis(
        self,
        incident_data: Dict[str, Any],
        logs: Optional[str],
        similar_incidents: List[Dict],
        graph_patterns: List[Dict],
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Use GPT-4 for deep incident analysis"""

        # Build context
        rag_context = "\n\n".join([
            f"Similar Incident {i+1} (Similarity: {inc.get('similarity_score', 0):.2f}):\n"
            f"Description: {inc.get('short_description', 'N/A')}\n"
            f"Root Cause: {inc.get('root_cause', 'N/A')}\n"
            f"Solution: {inc.get('solution', 'N/A')}\n"
            f"Agent Used: {inc.get('agent_used', 'N/A')}"
            for i, inc in enumerate(similar_incidents[:3])
        ]) if similar_incidents else "No similar incidents found."

        graph_context = "\n".join([
            f"Pattern {i+1}: {p.get('description', 'N/A')} - "
            f"Agent: {p.get('agent_used', 'N/A')}, "
            f"Resolution Time: {p.get('resolution_time', 'N/A')}min"
            for i, p in enumerate(graph_patterns[:3])
        ]) if graph_patterns else "No pattern data available."

        prompt = f"""You are an enterprise AI incident analysis system. Perform deep analysis of this incident.

**Incident Details:**
ID: {incident_data.get('incident_id', 'N/A')}
Short Description: {incident_data.get('short_description', 'N/A')}
Full Description: {incident_data.get('description', 'N/A')}
Category: {incident_data.get('category', 'unknown')}
Priority: {incident_data.get('priority', 'medium')}

**Logs (if available):**
{logs[:2000] if logs else 'No logs provided'}

**Similar Past Incidents (RAG):**
{rag_context}

**Historical Patterns (Graph DB):**
{graph_context}

**Additional Metadata:**
{metadata if metadata else 'None'}

**Analysis Required:**
1. Classify the incident type (infrastructure, data, application, network, etc.)
2. Determine actual category and severity
3. Identify key signals and patterns
4. Formulate root cause hypothesis
5. Provide reasoning and confidence score (0.0-1.0)
6. Extract critical keywords

Respond in JSON format:
{{
  "classification": "incident type",
  "category": "refined category",
  "severity": "low|medium|high|critical",
  "reasoning": "detailed reasoning based on logs, RAG, and patterns",
  "confidence": 0.0-1.0,
  "key_signals": ["signal1", "signal2", ...],
  "root_cause_hypothesis": "likely root cause",
  "critical_keywords": ["keyword1", "keyword2", ...]
}}
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an expert incident analysis AI. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            import json
            analysis = json.loads(response.choices[0].message.content)
            return analysis

        except Exception as e:
            logger.error("llm_analysis_error", error=str(e))
            return {
                "classification": "unknown",
                "category": incident_data.get("category", "unknown"),
                "severity": "medium",
                "reasoning": f"LLM analysis failed: {str(e)}",
                "confidence": 0.3,
                "key_signals": [],
                "root_cause_hypothesis": "Unable to determine",
                "critical_keywords": []
            }

    def _select_agent(
        self,
        llm_analysis: Dict[str, Any],
        incident_data: Dict[str, Any],
        priority: str
    ) -> Tuple[str, float, str]:
        """
        Select the most appropriate specialized agent

        Returns:
            (agent_id, confidence, reasoning)
        """
        keywords = llm_analysis.get("critical_keywords", [])
        category = llm_analysis.get("category", "unknown").lower()
        classification = llm_analysis.get("classification", "").lower()

        # Combine all text for keyword matching
        text = f"{classification} {category} {incident_data.get('short_description', '')} {incident_data.get('description', '')}".lower()

        # Score each agent
        agent_scores = {}

        for agent_id, config in self.AGENT_CAPABILITIES.items():
            score = 0.0

            # Keyword matching
            matched_keywords = sum(1 for kw in config["keywords"] if kw in text)
            score += matched_keywords * 0.3

            # Priority matching
            if priority in config["priority"]:
                score += 0.2

            # Category matching
            if any(cap.lower() in text for cap in config["capabilities"]):
                score += 0.4

            # LLM confidence boost
            if llm_analysis.get("confidence", 0) > 0.7:
                score += 0.1

            agent_scores[agent_id] = score

        # Select agent with highest score
        selected_agent = max(agent_scores, key=agent_scores.get)
        confidence = min(agent_scores[selected_agent], 1.0)

        # Fallback if confidence too low
        if confidence < 0.3:
            selected_agent = "fallback-agent"
            confidence = 0.5

        reasoning = f"Selected {self.AGENT_CAPABILITIES[selected_agent]['name']} based on: "
        reasoning += f"keyword match, category={category}, priority={priority}, LLM confidence={llm_analysis.get('confidence', 0):.2f}"

        return selected_agent, confidence, reasoning

    async def step2_auto_select_agent(
        self,
        incident_id: str,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 2: Auto Select Specialized Agent
        Returns agent selection with full reasoning
        """
        logger.info("step2_agent_selection", incident_id=incident_id)

        result = {
            "selected_agent": analysis_result.get("recommended_agent"),
            "agent_name": self.AGENT_CAPABILITIES.get(
                analysis_result.get("recommended_agent"),
                {"name": "Unknown"}
            )["name"],
            "confidence": analysis_result.get("agent_confidence", 0.0),
            "reasoning": analysis_result.get("agent_reasoning", ""),
            "alternative_agents": [],
            "timestamp": datetime.now().isoformat()
        }

        # Publish to Kafka
        kafka_client.publish_event(
            topic="agent.routing",
            event={
                "incident_id": incident_id,
                "step": "step2_agent_selection",
                "type": "agent_selected",
                "data": result
            },
            key=incident_id
        )

        logger.info(
            "step2_agent_selected",
            incident_id=incident_id,
            agent=result["selected_agent"],
            confidence=result["confidence"]
        )

        return result


# Global instance
reasoning_engine = ReasoningEngine()
