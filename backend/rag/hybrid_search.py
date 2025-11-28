"""Hybrid search combining Weaviate (vector) and Neo4j (graph) for intelligent retrieval"""
from typing import Any, Dict, List, Optional
from .weaviate_client import weaviate_client
from .neo4j_client import neo4j_client
import structlog

logger = structlog.get_logger()


class HybridRAG:
    """Hybrid RAG combining vector search and graph reasoning"""

    def __init__(self):
        self.weaviate = weaviate_client
        self.neo4j = neo4j_client

    def retrieve_context_for_incident(
        self,
        incident_description: str,
        service: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive context for incident resolution:
        - Similar incidents (Weaviate)
        - Relevant runbooks (Weaviate)
        - Historical incidents for same service (Neo4j)
        - Root cause patterns (Neo4j)
        """
        context = {
            "similar_incidents": [],
            "runbooks": [],
            "service_history": [],
            "causal_patterns": []
        }

        try:
            # Vector search for similar incidents
            filters = {"path": ["service"], "operator": "Equal", "valueString": service} if service else None
            context["similar_incidents"] = self.weaviate.search_similar_incidents(
                query=incident_description,
                limit=limit,
                filters=filters
            )

            # Vector search for relevant runbooks
            context["runbooks"] = self.weaviate.search_runbooks(
                query=incident_description,
                limit=3
            )

            # Graph search for service history
            if service:
                context["service_history"] = self.neo4j.find_similar_incidents_by_service(
                    service=service,
                    limit=limit
                )

                # Get impact chain
                context["impact_chain"] = self.neo4j.find_impact_chain(service)

            logger.info(
                "hybrid_context_retrieved",
                similar_count=len(context["similar_incidents"]),
                runbook_count=len(context["runbooks"]),
                history_count=len(context["service_history"])
            )

        except Exception as e:
            logger.error("hybrid_retrieval_error", error=str(e))

        return context

    def retrieve_for_rca(self, incident_id: str, service: str) -> Dict[str, Any]:
        """Retrieve context specifically for Root Cause Analysis"""
        context = {
            "root_causes": [],
            "similar_patterns": [],
            "service_dependencies": []
        }

        try:
            # Find root causes from graph
            context["root_causes"] = self.neo4j.find_root_causes(incident_id)

            # Find similar incidents that affected same service
            similar_incidents = self.neo4j.find_similar_incidents_by_service(service)
            context["similar_patterns"] = similar_incidents

            # Get service dependencies
            context["service_dependencies"] = self.neo4j.find_impact_chain(service)

            logger.info("rca_context_retrieved", incident_id=incident_id)

        except Exception as e:
            logger.error("rca_retrieval_error", error=str(e))

        return context

    def store_incident_with_graph(
        self,
        incident_id: str,
        incident_data: Dict[str, Any],
        service: str,
        topic: str
    ):
        """Store incident in both Weaviate (vector) and Neo4j (graph)"""
        try:
            # Store in Weaviate for semantic search
            self.weaviate.add_incident(incident_data)

            # Store in Neo4j for graph reasoning
            self.neo4j.add_incident(
                incident_id=incident_id,
                service=service,
                topic=topic,
                properties=incident_data
            )

            logger.info("incident_stored_hybrid", incident_id=incident_id)

        except Exception as e:
            logger.error("hybrid_storage_error", error=str(e))
            raise


# Global Hybrid RAG instance
hybrid_rag = HybridRAG()
