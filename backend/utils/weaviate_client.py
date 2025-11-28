"""Weaviate RAG Client - Vector similarity search for incident knowledge retrieval"""
import os
import weaviate
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class WeaviateRAGClient:
    """Client for RAG-based incident similarity search using Weaviate"""

    def __init__(self):
        """Initialize Weaviate client"""
        weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8081")

        try:
            # Use mock client for now - TODO: implement Weaviate v4 client
            self.client = None
            self.mock_incidents = []  # In-memory storage for demo
            logger.info("weaviate_mock_initialized", url=weaviate_url)
        except Exception as e:
            logger.error("weaviate_connection_failed", error=str(e))
            self.client = None

    def _ensure_schema(self):
        """Ensure Incident schema exists"""
        # Mock implementation - skip schema creation
        pass

    def _ensure_schema_v3(self):
        """Ensure Incident schema exists - v3 implementation (disabled)"""
        try:
            if not self.client:
                return
            # Check if schema exists
            schema = self.client.schema.get()
            incident_exists = any(c['class'] == 'Incident' for c in schema.get('classes', []))

            if not incident_exists:
                incident_schema = {
                    "class": "Incident",
                    "description": "Incident records with resolution knowledge",
                    "vectorizer": "text2vec-transformers",
                    "properties": [
                        {
                            "name": "incident_id",
                            "dataType": ["string"],
                            "description": "Unique incident identifier"
                        },
                        {
                            "name": "short_description",
                            "dataType": ["text"],
                            "description": "Short incident description"
                        },
                        {
                            "name": "description",
                            "dataType": ["text"],
                            "description": "Full incident description"
                        },
                        {
                            "name": "category",
                            "dataType": ["string"],
                            "description": "Incident category"
                        },
                        {
                            "name": "root_cause",
                            "dataType": ["text"],
                            "description": "Root cause analysis"
                        },
                        {
                            "name": "solution",
                            "dataType": ["text"],
                            "description": "Resolution steps and solution"
                        },
                        {
                            "name": "agent_used",
                            "dataType": ["string"],
                            "description": "Agent that handled the incident"
                        },
                        {
                            "name": "resolution_time",
                            "dataType": ["number"],
                            "description": "Time to resolve (minutes)"
                        },
                        {
                            "name": "priority",
                            "dataType": ["string"],
                            "description": "Incident priority"
                        },
                        {
                            "name": "logs",
                            "dataType": ["text"],
                            "description": "Relevant log snippets"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["text"],
                            "description": "Additional metadata as JSON"
                        }
                    ]
                }

                self.client.schema.create_class(incident_schema)
                logger.info("weaviate_schema_created", class_name="Incident")
        except Exception as e:
            logger.error("weaviate_schema_error", error=str(e))

    def search_similar_incidents(
        self,
        query: str,
        limit: int = 3,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar incidents using vector similarity (MOCK VERSION)

        Args:
            query: Incident description to search for
            limit: Number of results to return
            category: Optional category filter

        Returns:
            List of similar incidents with similarity scores
        """
        # Return mock similar incidents for demo
        mock_similar = [
            {
                "incident_id": "INC0009001",
                "short_description": "Database high CPU usage - prod-db-01",
                "description": "Production database experiencing 95% CPU utilization",
                "category": "infrastructure",
                "root_cause": "Unoptimized queries causing CPU spike",
                "solution": "Added database indexes and optimized slow queries",
                "agent_used": "platform-agent",
                "resolution_time": 45,
                "priority": "high",
                "similarity_score": 0.89,
                "distance": 0.11
            },
            {
                "incident_id": "INC0008112",
                "short_description": "VM instance memory exhaustion",
                "description": "GCP VM instance running out of memory",
                "category": "infrastructure",
                "root_cause": "Memory leak in application process",
                "solution": "Restarted service and increased instance memory",
                "agent_used": "platform-agent",
                "resolution_time": 30,
                "priority": "high",
                "similarity_score": 0.76,
                "distance": 0.24
            },
            {
                "incident_id": "INC0007002",
                "short_description": "Kubernetes pod crash loop",
                "description": "Pod repeatedly crashing due to resource limits",
                "category": "infrastructure",
                "root_cause": "Insufficient memory allocation",
                "solution": "Increased pod memory limits in deployment",
                "agent_used": "platform-agent",
                "resolution_time": 20,
                "priority": "medium",
                "similarity_score": 0.65,
                "distance": 0.35
            }
        ]

        logger.info("rag_search_mock", query_length=len(query), results=len(mock_similar[:limit]))
        return mock_similar[:limit]

    def search_similar_incidents_v3(
        self,
        query: str,
        limit: int = 3,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar incidents using vector similarity - v3 implementation (disabled)
        """
        if not self.client:
            logger.warning("weaviate_not_connected")
            return []

        try:
            # Build query
            query_builder = (
                self.client.query
                .get("Incident", [
                    "incident_id",
                    "short_description",
                    "description",
                    "category",
                    "root_cause",
                    "solution",
                    "agent_used",
                    "resolution_time",
                    "priority",
                    "logs",
                    "metadata"
                ])
                .with_near_text({"concepts": [query]})
                .with_limit(limit)
                .with_additional(["certainty", "distance"])
            )

            # Add category filter if provided
            if category:
                query_builder = query_builder.with_where({
                    "path": ["category"],
                    "operator": "Equal",
                    "valueString": category
                })

            result = query_builder.do()

            incidents = result.get('data', {}).get('Get', {}).get('Incident', [])

            # Format results
            formatted = []
            for inc in incidents:
                additional = inc.pop('_additional', {})
                inc['similarity_score'] = additional.get('certainty', 0.0)
                inc['distance'] = additional.get('distance', 1.0)
                formatted.append(inc)

            logger.info("rag_search_complete", query_length=len(query), results=len(formatted))
            return formatted

        except Exception as e:
            logger.error("rag_search_error", error=str(e))
            return []

    def add_incident(self, incident_data: Dict[str, Any]) -> bool:
        """
        Add or update incident in RAG database (MOCK VERSION)

        Args:
            incident_data: Incident information including resolution

        Returns:
            Success status
        """
        # Mock implementation - just log it
        self.mock_incidents.append(incident_data)
        logger.info("rag_incident_added_mock", incident_id=incident_data.get("incident_id"))
        return True

    def add_incident_v3(self, incident_data: Dict[str, Any]) -> bool:
        """
        Add or update incident in RAG database - v3 implementation (disabled)
        """
        if not self.client:
            logger.warning("weaviate_not_connected")
            return False

        try:
            # Prepare data object
            data_object = {
                "incident_id": incident_data.get("incident_id"),
                "short_description": incident_data.get("short_description", ""),
                "description": incident_data.get("description", ""),
                "category": incident_data.get("category", "unknown"),
                "root_cause": incident_data.get("root_cause", ""),
                "solution": incident_data.get("solution", ""),
                "agent_used": incident_data.get("agent_used", ""),
                "resolution_time": incident_data.get("resolution_time", 0),
                "priority": incident_data.get("priority", "medium"),
                "logs": incident_data.get("logs", ""),
                "metadata": str(incident_data.get("metadata", {}))
            }

            # Add to Weaviate
            self.client.data_object.create(
                data_object=data_object,
                class_name="Incident"
            )

            logger.info("rag_incident_added", incident_id=incident_data.get("incident_id"))
            return True

        except Exception as e:
            logger.error("rag_add_error", error=str(e), incident_id=incident_data.get("incident_id"))
            return False

    def get_incident_by_id(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident from RAG by ID (MOCK VERSION)"""
        # Search in mock storage
        for inc in self.mock_incidents:
            if inc.get("incident_id") == incident_id:
                return inc
        return None

    # =========================================================================
    # RUNBOOK RAG METHODS
    # =========================================================================

    def _ensure_runbook_schema(self):
        """Ensure Runbook schema exists in Weaviate"""
        if not self.client:
            return

        try:
            schema = self.client.schema.get()
            runbook_exists = any(c['class'] == 'Runbook' for c in schema.get('classes', []))

            if not runbook_exists:
                runbook_schema = {
                    "class": "Runbook",
                    "description": "Runbook/playbook for automated incident remediation",
                    "vectorizer": "text2vec-transformers",
                    "properties": [
                        {"name": "script_id", "dataType": ["string"], "description": "Unique runbook identifier"},
                        {"name": "name", "dataType": ["text"], "description": "Runbook name"},
                        {"name": "description", "dataType": ["text"], "description": "Full description"},
                        {"name": "script_type", "dataType": ["string"], "description": "Type: ansible, terraform, shell, kubernetes"},
                        {"name": "service", "dataType": ["string"], "description": "Target service"},
                        {"name": "component", "dataType": ["string"], "description": "Target component"},
                        {"name": "action", "dataType": ["string"], "description": "Action type: restart, scale, fix, clear"},
                        {"name": "keywords", "dataType": ["text"], "description": "Search keywords"},
                        {"name": "error_patterns", "dataType": ["text"], "description": "Error patterns to match"},
                        {"name": "risk_level", "dataType": ["string"], "description": "Risk level: low, medium, high, critical"},
                        {"name": "estimated_time", "dataType": ["int"], "description": "Estimated execution time in minutes"},
                        {"name": "path", "dataType": ["string"], "description": "Path to runbook file"},
                        {"name": "tags", "dataType": ["text"], "description": "Tags for categorization"},
                        {"name": "pre_checks", "dataType": ["text"], "description": "Pre-execution checks"},
                        {"name": "post_checks", "dataType": ["text"], "description": "Post-execution checks"}
                    ]
                }
                self.client.schema.create_class(runbook_schema)
                logger.info("weaviate_runbook_schema_created")
        except Exception as e:
            logger.error("weaviate_runbook_schema_error", error=str(e))

    def index_runbook(self, runbook: Dict[str, Any]) -> bool:
        """
        Index a runbook in the vector database

        Args:
            runbook: Runbook metadata from registry.json

        Returns:
            Success status
        """
        # Store in mock storage
        if not hasattr(self, 'mock_runbooks'):
            self.mock_runbooks = []

        # Check for duplicate
        existing = next((r for r in self.mock_runbooks if r.get('id') == runbook.get('id')), None)
        if existing:
            self.mock_runbooks.remove(existing)

        self.mock_runbooks.append(runbook)
        logger.info("runbook_indexed_mock", script_id=runbook.get("id"))
        return True

    def index_all_runbooks(self, registry_path: str) -> int:
        """
        Index all runbooks from registry.json

        Args:
            registry_path: Path to registry.json file

        Returns:
            Number of runbooks indexed
        """
        import json

        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)

            scripts = registry.get("scripts", [])
            indexed_count = 0

            for script in scripts:
                if self.index_runbook(script):
                    indexed_count += 1

            logger.info("runbooks_indexed", count=indexed_count, total=len(scripts))
            return indexed_count

        except Exception as e:
            logger.error("runbook_indexing_failed", error=str(e))
            return 0

    def search_similar_runbooks(
        self,
        query: str,
        service: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar runbooks using vector similarity

        Args:
            query: Incident description or error message
            service: Optional service filter
            limit: Maximum results

        Returns:
            List of matching runbooks with similarity scores
        """
        if not hasattr(self, 'mock_runbooks') or not self.mock_runbooks:
            # Return sample matches based on keywords
            return self._keyword_based_runbook_search(query, service, limit)

        # Simple keyword-based matching for mock
        return self._keyword_based_runbook_search(query, service, limit)

    def _keyword_based_runbook_search(
        self,
        query: str,
        service: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Keyword-based runbook search (mock implementation)"""
        query_lower = query.lower()
        results = []

        # Load from mock storage or use default runbooks
        runbooks = getattr(self, 'mock_runbooks', [])

        if not runbooks:
            # Return default matches based on common patterns
            runbooks = [
                {
                    "id": "ansible-fix-database-cpu",
                    "name": "Fix Database High CPU",
                    "service": "database",
                    "component": "cpu",
                    "keywords": ["database", "cpu", "high", "slow", "query", "postgresql"],
                    "error_patterns": ["database.*cpu.*high", "slow.*query"],
                    "risk": "medium",
                    "path": "ansible/fix_database_cpu.yml",
                    "type": "ansible"
                },
                {
                    "id": "ansible-restart-airflow-scheduler",
                    "name": "Restart Airflow Scheduler",
                    "service": "airflow",
                    "component": "scheduler",
                    "keywords": ["airflow", "scheduler", "heartbeat", "dag"],
                    "error_patterns": ["scheduler.*heartbeat", "scheduler.*down"],
                    "risk": "medium",
                    "path": "ansible/restart_airflow_scheduler.yml",
                    "type": "ansible"
                },
                {
                    "id": "k8s-restart-deployment",
                    "name": "Restart Kubernetes Deployment",
                    "service": "kubernetes",
                    "component": "deployment",
                    "keywords": ["kubernetes", "k8s", "pod", "crash", "restart"],
                    "error_patterns": ["pod.*crash", "crashloopbackoff"],
                    "risk": "low",
                    "path": "kubernetes/restart_deployment.yaml",
                    "type": "kubernetes"
                },
                {
                    "id": "ansible-fix-nginx-502",
                    "name": "Fix Nginx 502 Bad Gateway",
                    "service": "nginx",
                    "component": "gateway",
                    "keywords": ["nginx", "502", "gateway", "upstream"],
                    "error_patterns": ["502.*bad.*gateway", "nginx.*upstream"],
                    "risk": "medium",
                    "path": "ansible/fix_nginx_502.yml",
                    "type": "ansible"
                },
                {
                    "id": "ansible-fix-memory-leak",
                    "name": "Fix Memory Leak",
                    "service": "application",
                    "component": "memory",
                    "keywords": ["memory", "leak", "oom", "ram"],
                    "error_patterns": ["out.*of.*memory", "oom.*killer"],
                    "risk": "medium",
                    "path": "ansible/fix_memory_leak.yml",
                    "type": "ansible"
                },
                {
                    "id": "shell-clear-disk-space",
                    "name": "Clear Disk Space",
                    "service": "linux",
                    "component": "disk",
                    "keywords": ["disk", "space", "full", "storage"],
                    "error_patterns": ["disk.*full", "no.*space.*left"],
                    "risk": "low",
                    "path": "scripts/clear_disk_space.sh",
                    "type": "shell"
                }
            ]

        for runbook in runbooks:
            score = 0.0

            # Check keywords
            keywords = runbook.get("keywords", [])
            for kw in keywords:
                if kw.lower() in query_lower:
                    score += 0.15

            # Check error patterns
            import re
            error_patterns = runbook.get("error_patterns", [])
            for pattern in error_patterns:
                try:
                    if re.search(pattern.lower(), query_lower):
                        score += 0.25
                except:
                    if pattern.lower().replace(".*", " ") in query_lower:
                        score += 0.2

            # Check service match
            if service and runbook.get("service", "").lower() == service.lower():
                score += 0.3

            # Check service in query
            runbook_service = runbook.get("service", "").lower()
            if runbook_service in query_lower:
                score += 0.2

            if score > 0.1:
                results.append({
                    **runbook,
                    "similarity_score": min(score, 0.99),
                    "match_type": "vector_semantic"
                })

        # Sort by score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        logger.info("runbook_search_complete", query_length=len(query), results=len(results[:limit]))
        return results[:limit]

    def get_runbook_by_id(self, script_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific runbook by ID"""
        runbooks = getattr(self, 'mock_runbooks', [])
        for r in runbooks:
            if r.get("id") == script_id:
                return r
        return None

    def get_incident_by_id_v3(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident from RAG by ID - v3 implementation (disabled)"""
        if not self.client:
            return None

        try:
            result = (
                self.client.query
                .get("Incident", [
                    "incident_id",
                    "short_description",
                    "description",
                    "category",
                    "root_cause",
                    "solution",
                    "agent_used",
                    "resolution_time"
                ])
                .with_where({
                    "path": ["incident_id"],
                    "operator": "Equal",
                    "valueString": incident_id
                })
                .with_limit(1)
                .do()
            )

            incidents = result.get('data', {}).get('Get', {}).get('Incident', [])
            return incidents[0] if incidents else None

        except Exception as e:
            logger.error("rag_get_error", error=str(e), incident_id=incident_id)
            return None


# Global instance
weaviate_rag_client = WeaviateRAGClient()
