"""Neo4j Graph DB Client - Incident relationship tracking and pattern discovery"""
import os
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import structlog

logger = structlog.get_logger()


class Neo4jGraphClient:
    """Client for Graph DB-based incident relationship tracking"""

    def __init__(self):
        """Initialize Neo4j client"""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            logger.info("neo4j_connected", uri=uri)
            self._create_constraints()
        except Exception as e:
            logger.error("neo4j_connection_failed", error=str(e))
            self.driver = None

    def _create_constraints(self):
        """Create uniqueness constraints and indexes"""
        if not self.driver:
            return

        try:
            with self.driver.session() as session:
                # Create constraints
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Agent) REQUIRE a.agent_id IS UNIQUE",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Solution) REQUIRE s.solution_id IS UNIQUE",
                    "CREATE INDEX IF NOT EXISTS FOR (i:Incident) ON (i.category)",
                    "CREATE INDEX IF NOT EXISTS FOR (i:Incident) ON (i.priority)",
                ]

                for constraint in constraints:
                    try:
                        session.run(constraint)
                    except Exception as e:
                        # Constraint might already exist
                        logger.debug("neo4j_constraint_skip", error=str(e))

                logger.info("neo4j_constraints_created")
        except Exception as e:
            logger.error("neo4j_constraint_error", error=str(e))

    def create_incident_node(self, incident_data: Dict[str, Any]) -> bool:
        """
        Create or update incident node in graph

        Args:
            incident_data: Incident information

        Returns:
            Success status
        """
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = """
                MERGE (i:Incident {incident_id: $incident_id})
                SET i.short_description = $short_description,
                    i.description = $description,
                    i.category = $category,
                    i.priority = $priority,
                    i.state = $state,
                    i.created_on = $created_on,
                    i.updated_on = datetime()
                RETURN i.incident_id
                """

                result = session.run(
                    query,
                    incident_id=incident_data.get("incident_id"),
                    short_description=incident_data.get("short_description", ""),
                    description=incident_data.get("description", ""),
                    category=incident_data.get("category", "unknown"),
                    priority=incident_data.get("priority", "medium"),
                    state=incident_data.get("state", "new"),
                    created_on=incident_data.get("created_on", "")
                )

                result.single()
                logger.info("neo4j_incident_created", incident_id=incident_data.get("incident_id"))
                return True

        except Exception as e:
            logger.error("neo4j_create_incident_error", error=str(e))
            return False

    def create_agent_handled_relationship(
        self,
        incident_id: str,
        agent_id: str,
        agent_name: str,
        confidence: float,
        reasoning: str
    ) -> bool:
        """
        Create HANDLED relationship between Agent and Incident

        Args:
            incident_id: Incident identifier
            agent_id: Agent identifier
            agent_name: Agent display name
            confidence: Confidence score
            reasoning: Agent reasoning

        Returns:
            Success status
        """
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (i:Incident {incident_id: $incident_id})
                MERGE (a:Agent {agent_id: $agent_id})
                SET a.name = $agent_name
                MERGE (a)-[r:HANDLED]->(i)
                SET r.confidence = $confidence,
                    r.reasoning = $reasoning,
                    r.handled_at = datetime()
                RETURN i.incident_id, a.agent_id
                """

                result = session.run(
                    query,
                    incident_id=incident_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    confidence=confidence,
                    reasoning=reasoning
                )

                result.single()
                logger.info("neo4j_handled_relationship_created", incident_id=incident_id, agent=agent_id)
                return True

        except Exception as e:
            logger.error("neo4j_create_handled_error", error=str(e))
            return False

    def create_solution_relationship(
        self,
        incident_id: str,
        solution_data: Dict[str, Any]
    ) -> bool:
        """
        Create FIXED_BY relationship with Solution node

        Args:
            incident_id: Incident identifier
            solution_data: Solution details

        Returns:
            Success status
        """
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = """
                MATCH (i:Incident {incident_id: $incident_id})
                CREATE (s:Solution {
                    solution_id: randomUUID(),
                    root_cause: $root_cause,
                    steps: $steps,
                    execution_time: $execution_time,
                    created_at: datetime()
                })
                CREATE (i)-[r:FIXED_BY]->(s)
                SET r.resolution_time = $resolution_time,
                    r.success = $success
                RETURN s.solution_id
                """

                result = session.run(
                    query,
                    incident_id=incident_id,
                    root_cause=solution_data.get("root_cause", ""),
                    steps=str(solution_data.get("steps", [])),
                    execution_time=solution_data.get("execution_time", 0),
                    resolution_time=solution_data.get("resolution_time", 0),
                    success=solution_data.get("success", True)
                )

                result.single()
                logger.info("neo4j_solution_relationship_created", incident_id=incident_id)
                return True

        except Exception as e:
            logger.error("neo4j_create_solution_error", error=str(e))
            return False

    def create_related_incident_relationship(
        self,
        incident_id: str,
        related_incident_id: str,
        relationship_type: str = "RELATED_TO"
    ) -> bool:
        """
        Create relationship between two related incidents

        Args:
            incident_id: Source incident
            related_incident_id: Target incident
            relationship_type: Type of relationship (RELATED_TO, SIMILAR_TO, CAUSED_BY)

        Returns:
            Success status
        """
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                query = f"""
                MATCH (i1:Incident {{incident_id: $incident_id}})
                MATCH (i2:Incident {{incident_id: $related_incident_id}})
                MERGE (i1)-[r:{relationship_type}]->(i2)
                SET r.created_at = datetime()
                RETURN i1.incident_id, i2.incident_id
                """

                result = session.run(
                    query,
                    incident_id=incident_id,
                    related_incident_id=related_incident_id
                )

                result.single()
                logger.info(
                    "neo4j_related_relationship_created",
                    incident=incident_id,
                    related=related_incident_id,
                    type=relationship_type
                )
                return True

        except Exception as e:
            logger.error("neo4j_create_related_error", error=str(e))
            return False

    def get_incident_relationships(self, incident_id: str) -> Dict[str, Any]:
        """
        Get all relationships for an incident

        Args:
            incident_id: Incident identifier

        Returns:
            Dictionary with related incidents, agents, and solutions
        """
        if not self.driver:
            return {}

        try:
            with self.driver.session() as session:
                # Get handled by agent
                agent_query = """
                MATCH (a:Agent)-[r:HANDLED]->(i:Incident {incident_id: $incident_id})
                RETURN a.agent_id as agent_id, a.name as agent_name,
                       r.confidence as confidence, r.reasoning as reasoning
                """
                agent_result = session.run(agent_query, incident_id=incident_id)
                agents = [dict(record) for record in agent_result]

                # Get solutions
                solution_query = """
                MATCH (i:Incident {incident_id: $incident_id})-[r:FIXED_BY]->(s:Solution)
                RETURN s.solution_id as solution_id, s.root_cause as root_cause,
                       s.steps as steps, r.resolution_time as resolution_time
                """
                solution_result = session.run(solution_query, incident_id=incident_id)
                solutions = [dict(record) for record in solution_result]

                # Get related incidents
                related_query = """
                MATCH (i:Incident {incident_id: $incident_id})-[r]->(related:Incident)
                RETURN related.incident_id as incident_id,
                       related.short_description as description,
                       type(r) as relationship_type
                """
                related_result = session.run(related_query, incident_id=incident_id)
                related = [dict(record) for record in related_result]

                return {
                    "agents": agents,
                    "solutions": solutions,
                    "related_incidents": related
                }

        except Exception as e:
            logger.error("neo4j_get_relationships_error", error=str(e))
            return {}

    def find_similar_incident_patterns(
        self,
        category: str,
        priority: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find incidents with similar patterns (category, priority, solution path)

        Args:
            category: Incident category
            priority: Optional priority filter
            limit: Maximum results

        Returns:
            List of similar incident patterns
        """
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                query = """
                MATCH (i:Incident {category: $category})
                OPTIONAL MATCH (a:Agent)-[h:HANDLED]->(i)
                OPTIONAL MATCH (i)-[f:FIXED_BY]->(s:Solution)
                WHERE ($priority IS NULL OR i.priority = $priority)
                RETURN i.incident_id as incident_id,
                       i.short_description as description,
                       i.priority as priority,
                       a.name as agent_used,
                       h.confidence as confidence,
                       s.root_cause as root_cause,
                       f.resolution_time as resolution_time
                ORDER BY f.resolution_time ASC
                LIMIT $limit
                """

                result = session.run(
                    query,
                    category=category,
                    priority=priority,
                    limit=limit
                )

                return [dict(record) for record in result]

        except Exception as e:
            logger.error("neo4j_find_patterns_error", error=str(e))
            return []

    def create_remediation_relationship(
        self,
        incident_id: str,
        script_id: str,
        confidence: float,
        status: str = "proposed"
    ) -> bool:
        """
        Create REMEDIATED_BY relationship between Incident and Runbook script

        Args:
            incident_id: Incident identifier
            script_id: Runbook script identifier
            confidence: Match confidence score
            status: Remediation status (proposed, approved, executed, verified)

        Returns:
            Success status
        """
        if not self.driver:
            logger.info("neo4j_remediation_mock", incident_id=incident_id, script_id=script_id)
            return True

        try:
            with self.driver.session() as session:
                query = """
                MATCH (i:Incident {incident_id: $incident_id})
                MERGE (r:Runbook {script_id: $script_id})
                MERGE (i)-[rel:REMEDIATED_BY]->(r)
                SET rel.confidence = $confidence,
                    rel.status = $status,
                    rel.proposed_at = datetime()
                RETURN i.incident_id, r.script_id
                """

                result = session.run(
                    query,
                    incident_id=incident_id,
                    script_id=script_id,
                    confidence=confidence,
                    status=status
                )

                result.single()
                logger.info(
                    "neo4j_remediation_relationship_created",
                    incident_id=incident_id,
                    script_id=script_id,
                    confidence=confidence
                )
                return True

        except Exception as e:
            logger.error("neo4j_create_remediation_error", error=str(e))
            return False

    # =========================================================================
    # RUNBOOK GRAPH METHODS
    # =========================================================================

    def create_runbook_node(self, runbook: Dict[str, Any]) -> bool:
        """
        Create or update a Runbook node with full metadata

        Args:
            runbook: Runbook data from registry

        Returns:
            Success status
        """
        if not self.driver:
            logger.info("neo4j_runbook_mock", script_id=runbook.get("id"))
            return True

        try:
            with self.driver.session() as session:
                query = """
                MERGE (r:Runbook {script_id: $script_id})
                SET r.name = $name,
                    r.type = $type,
                    r.service = $service,
                    r.component = $component,
                    r.action = $action,
                    r.risk = $risk,
                    r.path = $path,
                    r.keywords = $keywords,
                    r.estimated_time = $estimated_time,
                    r.updated_at = datetime()
                RETURN r.script_id
                """

                session.run(
                    query,
                    script_id=runbook.get("id"),
                    name=runbook.get("name", ""),
                    type=runbook.get("type", ""),
                    service=runbook.get("service", ""),
                    component=runbook.get("component", ""),
                    action=runbook.get("action", ""),
                    risk=runbook.get("risk", "medium"),
                    path=runbook.get("path", ""),
                    keywords=",".join(runbook.get("keywords", [])),
                    estimated_time=runbook.get("estimated_time_minutes", 10)
                )

                logger.info("neo4j_runbook_created", script_id=runbook.get("id"))
                return True

        except Exception as e:
            logger.error("neo4j_create_runbook_error", error=str(e))
            return False

    def create_runbook_service_relationship(
        self,
        script_id: str,
        service: str,
        component: str = None
    ) -> bool:
        """
        Create REMEDIATES relationship between Runbook and Service

        Args:
            script_id: Runbook identifier
            service: Service name
            component: Optional component name

        Returns:
            Success status
        """
        if not self.driver:
            return True

        try:
            with self.driver.session() as session:
                query = """
                MATCH (r:Runbook {script_id: $script_id})
                MERGE (s:Service {name: $service})
                MERGE (r)-[rel:REMEDIATES]->(s)
                SET rel.component = $component,
                    rel.created_at = datetime()
                RETURN r.script_id, s.name
                """

                session.run(
                    query,
                    script_id=script_id,
                    service=service,
                    component=component
                )

                logger.info("neo4j_runbook_service_relationship",
                           script_id=script_id, service=service)
                return True

        except Exception as e:
            logger.error("neo4j_runbook_service_error", error=str(e))
            return False

    def find_runbooks_for_service(
        self,
        service: str,
        component: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find runbooks that can remediate a specific service/component

        Args:
            service: Service name
            component: Optional component filter
            limit: Maximum results

        Returns:
            List of matching runbooks with success metrics
        """
        if not self.driver:
            # Return mock data
            return [
                {
                    "script_id": f"mock-{service}-runbook",
                    "name": f"Mock {service.title()} Remediation",
                    "success_count": 5,
                    "avg_resolution_time": 15
                }
            ]

        try:
            with self.driver.session() as session:
                query = """
                MATCH (r:Runbook)-[rel:REMEDIATES]->(s:Service {name: $service})
                WHERE $component IS NULL OR rel.component = $component
                OPTIONAL MATCH (i:Incident)-[rem:REMEDIATED_BY]->(r)
                WHERE rem.status = 'verified'
                WITH r, count(rem) as success_count,
                     avg(rem.resolution_time) as avg_time
                RETURN r.script_id as script_id,
                       r.name as name,
                       r.type as type,
                       r.risk as risk,
                       r.path as path,
                       success_count,
                       avg_time as avg_resolution_time
                ORDER BY success_count DESC
                LIMIT $limit
                """

                result = session.run(
                    query,
                    service=service,
                    component=component,
                    limit=limit
                )

                return [dict(record) for record in result]

        except Exception as e:
            logger.error("neo4j_find_runbooks_error", error=str(e))
            return []

    def find_successful_remediations(
        self,
        service: str = None,
        component: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find past successful remediations for learning

        Args:
            service: Optional service filter
            component: Optional component filter
            limit: Maximum results

        Returns:
            List of successful remediation records
        """
        if not self.driver:
            # Return mock successful remediations
            return [
                {
                    "incident_id": "INC0009001",
                    "script_id": "ansible-fix-database-cpu",
                    "service": "database",
                    "resolution_time": 15,
                    "confidence": 0.92
                },
                {
                    "incident_id": "INC0008500",
                    "script_id": "k8s-restart-deployment",
                    "service": "kubernetes",
                    "resolution_time": 5,
                    "confidence": 0.88
                }
            ]

        try:
            with self.driver.session() as session:
                query = """
                MATCH (i:Incident)-[rem:REMEDIATED_BY]->(r:Runbook)
                WHERE rem.status = 'verified'
                  AND ($service IS NULL OR i.category CONTAINS $service OR r.service = $service)
                RETURN i.incident_id as incident_id,
                       i.short_description as description,
                       r.script_id as script_id,
                       r.name as runbook_name,
                       r.service as service,
                       rem.confidence as confidence,
                       rem.resolution_time as resolution_time,
                       rem.executed_at as executed_at
                ORDER BY rem.executed_at DESC
                LIMIT $limit
                """

                result = session.run(
                    query,
                    service=service,
                    limit=limit
                )

                return [dict(record) for record in result]

        except Exception as e:
            logger.error("neo4j_find_remediations_error", error=str(e))
            return []

    def update_remediation_status(
        self,
        incident_id: str,
        script_id: str,
        status: str,
        resolution_time: int = None,
        notes: str = None
    ) -> bool:
        """
        Update the status of a remediation after execution

        Args:
            incident_id: Incident identifier
            script_id: Runbook identifier
            status: New status (approved, executing, executed, verified, failed)
            resolution_time: Time to resolve in minutes
            notes: Optional notes

        Returns:
            Success status
        """
        if not self.driver:
            logger.info("neo4j_update_remediation_mock",
                       incident_id=incident_id, status=status)
            return True

        try:
            with self.driver.session() as session:
                query = """
                MATCH (i:Incident {incident_id: $incident_id})-[rem:REMEDIATED_BY]->(r:Runbook {script_id: $script_id})
                SET rem.status = $status,
                    rem.updated_at = datetime()
                """

                if status == "executed" or status == "verified":
                    query += ", rem.executed_at = datetime()"

                if resolution_time:
                    query += f", rem.resolution_time = {resolution_time}"

                if notes:
                    query += ", rem.notes = $notes"

                query += " RETURN i.incident_id, r.script_id"

                session.run(
                    query,
                    incident_id=incident_id,
                    script_id=script_id,
                    status=status,
                    notes=notes
                )

                logger.info("neo4j_remediation_status_updated",
                           incident_id=incident_id,
                           script_id=script_id,
                           status=status)
                return True

        except Exception as e:
            logger.error("neo4j_update_remediation_error", error=str(e))
            return False

    def index_all_runbooks(self, registry_path: str) -> int:
        """
        Index all runbooks from registry into Neo4j graph

        Args:
            registry_path: Path to registry.json

        Returns:
            Number of runbooks indexed
        """
        import json

        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)

            scripts = registry.get("scripts", [])
            indexed = 0

            for script in scripts:
                if self.create_runbook_node(script):
                    # Create service relationship
                    service = script.get("service")
                    component = script.get("component")
                    if service:
                        self.create_runbook_service_relationship(
                            script.get("id"),
                            service,
                            component
                        )
                    indexed += 1

            logger.info("neo4j_runbooks_indexed", count=indexed)
            return indexed

        except Exception as e:
            logger.error("neo4j_index_runbooks_error", error=str(e))
            return 0

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("neo4j_connection_closed")


# Global instance
neo4j_graph_client = Neo4jGraphClient()
