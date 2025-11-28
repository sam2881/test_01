"""Weaviate client for vector-based semantic search and retrieval"""
import os
from typing import Any, Dict, List, Optional
import weaviate
from weaviate.classes.init import Auth
import structlog

logger = structlog.get_logger()


class WeaviateClient:
    """Weaviate client for semantic memory and knowledge retrieval"""

    def __init__(self):
        self.url = os.getenv("WEAVIATE_URL", "http://weaviate:8081")
        self.api_key = os.getenv("WEAVIATE_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self._client: Optional[weaviate.Client] = None

    @property
    def client(self) -> weaviate.Client:
        """Get or create Weaviate client"""
        if not self._client:
            self._client = weaviate.Client(
                url=self.url,
                additional_headers={
                    "X-OpenAI-Api-Key": self.openai_api_key
                }
            )
            logger.info("weaviate_connected", url=self.url)
        return self._client

    def create_schema(self):
        """Create schema for Incidents and Runbooks"""
        incident_schema = {
            "class": "Incident",
            "description": "Historical incidents and resolutions",
            "vectorizer": "text2vec-openai",
            "properties": [
                {
                    "name": "incident_id",
                    "dataType": ["string"],
                    "description": "Unique incident identifier"
                },
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "Incident title"
                },
                {
                    "name": "description",
                    "dataType": ["text"],
                    "description": "Incident description"
                },
                {
                    "name": "resolution",
                    "dataType": ["text"],
                    "description": "How the incident was resolved"
                },
                {
                    "name": "topic",
                    "dataType": ["string"],
                    "description": "BERTopic cluster topic"
                },
                {
                    "name": "severity",
                    "dataType": ["string"]
                },
                {
                    "name": "service",
                    "dataType": ["string"]
                },
                {
                    "name": "created_at",
                    "dataType": ["date"]
                }
            ]
        }

        runbook_schema = {
            "class": "Runbook",
            "description": "Operational runbooks and procedures",
            "vectorizer": "text2vec-openai",
            "properties": [
                {
                    "name": "runbook_id",
                    "dataType": ["string"]
                },
                {
                    "name": "title",
                    "dataType": ["text"]
                },
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Runbook steps and procedures"
                },
                {
                    "name": "topic",
                    "dataType": ["string"]
                },
                {
                    "name": "service",
                    "dataType": ["string"]
                },
                {
                    "name": "tags",
                    "dataType": ["string[]"]
                }
            ]
        }

        try:
            # Create schemas if they don't exist
            if not self.client.schema.exists("Incident"):
                self.client.schema.create_class(incident_schema)
                logger.info("schema_created", schema="Incident")

            if not self.client.schema.exists("Runbook"):
                self.client.schema.create_class(runbook_schema)
                logger.info("schema_created", schema="Runbook")
        except Exception as e:
            logger.error("schema_creation_error", error=str(e))

    def search_similar_incidents(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar incidents using semantic search"""
        try:
            query_builder = (
                self.client.query
                .get("Incident", ["incident_id", "title", "description", "resolution", "topic", "severity", "service"])
                .with_near_text({"concepts": [query]})
                .with_limit(limit)
            )

            if filters:
                query_builder = query_builder.with_where(filters)

            result = query_builder.do()
            incidents = result.get("data", {}).get("Get", {}).get("Incident", [])

            logger.info("incidents_retrieved", count=len(incidents), query=query)
            return incidents
        except Exception as e:
            logger.error("incident_search_error", error=str(e), query=query)
            return []

    def search_runbooks(
        self,
        query: str,
        limit: int = 3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant runbooks"""
        try:
            query_builder = (
                self.client.query
                .get("Runbook", ["runbook_id", "title", "content", "topic", "service", "tags"])
                .with_near_text({"concepts": [query]})
                .with_limit(limit)
            )

            if filters:
                query_builder = query_builder.with_where(filters)

            result = query_builder.do()
            runbooks = result.get("data", {}).get("Get", {}).get("Runbook", [])

            logger.info("runbooks_retrieved", count=len(runbooks), query=query)
            return runbooks
        except Exception as e:
            logger.error("runbook_search_error", error=str(e), query=query)
            return []

    def add_incident(self, incident_data: Dict[str, Any]) -> str:
        """Add incident to Weaviate"""
        try:
            uuid = self.client.data_object.create(
                data_object=incident_data,
                class_name="Incident"
            )
            logger.info("incident_added", uuid=uuid)
            return uuid
        except Exception as e:
            logger.error("incident_add_error", error=str(e))
            raise

    def add_runbook(self, runbook_data: Dict[str, Any]) -> str:
        """Add runbook to Weaviate"""
        try:
            uuid = self.client.data_object.create(
                data_object=runbook_data,
                class_name="Runbook"
            )
            logger.info("runbook_added", uuid=uuid)
            return uuid
        except Exception as e:
            logger.error("runbook_add_error", error=str(e))
            raise

    def hybrid_search(
        self,
        query: str,
        class_name: str = "Incident",
        alpha: float = 0.7,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector and keyword search"""
        try:
            result = (
                self.client.query
                .get(class_name, ["*"])
                .with_hybrid(query=query, alpha=alpha)
                .with_limit(limit)
                .do()
            )
            items = result.get("data", {}).get("Get", {}).get(class_name, [])
            logger.info("hybrid_search_complete", count=len(items), query=query)
            return items
        except Exception as e:
            logger.error("hybrid_search_error", error=str(e))
            return []


# Global Weaviate client instance
weaviate_client = WeaviateClient()
