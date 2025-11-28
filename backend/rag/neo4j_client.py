"""Neo4j client for graph-based causal reasoning and RCA"""
import os
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
import structlog

logger = structlog.get_logger()


class Neo4jClient:
    """Neo4j client for causal knowledge graph and root cause analysis"""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password123")
        self._driver: Optional[Driver] = None

    @property
    def driver(self) -> Driver:
        """Get or create Neo4j driver"""
        if not self._driver:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            logger.info("neo4j_connected", uri=self.uri)
        return self._driver

    def close(self):
        """Close Neo4j connection"""
        if self._driver:
            self._driver.close()

    def create_indexes(self):
        """Create indexes for better query performance"""
        with self.driver.session() as session:
            # Create indexes
            session.run("CREATE INDEX IF NOT EXISTS FOR (s:Service) ON (s.name)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (i:Incident) ON (i.incident_id)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (t:Topic) ON (t.name)")
            logger.info("neo4j_indexes_created")

    def add_service(self, service_name: str, properties: Optional[Dict[str, Any]] = None) -> str:
        """Add or update service node"""
        with self.driver.session() as session:
            props = properties or {}
            result = session.run(
                """
                MERGE (s:Service {name: $name})
                SET s += $properties
                RETURN s
                """,
                name=service_name,
                properties=props
            )
            logger.info("service_added", service=service_name)
            return service_name

    def add_incident(self, incident_id: str, service: str, topic: str, properties: Dict[str, Any]):
        """Add incident node and relationships"""
        with self.driver.session() as session:
            session.run(
                """
                MERGE (i:Incident {incident_id: $incident_id})
                SET i += $properties

                MERGE (s:Service {name: $service})
                MERGE (t:Topic {name: $topic})

                MERGE (i)-[:AFFECTS]->(s)
                MERGE (i)-[:BELONGS_TO]->(t)
                """,
                incident_id=incident_id,
                service=service,
                topic=topic,
                properties=properties
            )
            logger.info("incident_added_to_graph", incident_id=incident_id)

    def add_causal_relationship(
        self,
        from_entity: str,
        to_entity: str,
        relationship: str,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Add causal relationship between entities"""
        with self.driver.session() as session:
            props = properties or {}
            session.run(
                f"""
                MATCH (a), (b)
                WHERE a.name = $from OR a.incident_id = $from
                AND b.name = $to OR b.incident_id = $to
                MERGE (a)-[r:{relationship}]->(b)
                SET r += $properties
                """,
                **{"from": from_entity, "to": to_entity, "properties": props}
            )
            logger.info("relationship_added", from_=from_entity, to=to_entity, rel=relationship)

    def find_root_causes(self, incident_id: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Find potential root causes for an incident using graph traversal"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (i:Incident {incident_id: $incident_id})-[:CAUSED_BY*1..]-(root)
                WHERE NOT (root)-[:CAUSED_BY]->()
                WITH path, length(path) as depth
                WHERE depth <= $max_depth
                RETURN path, root, depth
                ORDER BY depth ASC
                LIMIT 10
                """,
                incident_id=incident_id,
                max_depth=max_depth
            )

            causes = []
            for record in result:
                causes.append({
                    "root_cause": dict(record["root"]),
                    "depth": record["depth"],
                    "path_length": len(record["path"])
                })

            logger.info("root_causes_found", incident_id=incident_id, count=len(causes))
            return causes

    def find_similar_incidents_by_service(self, service: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar incidents affecting the same service"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (i:Incident)-[:AFFECTS]->(s:Service {name: $service})
                RETURN i
                ORDER BY i.created_at DESC
                LIMIT $limit
                """,
                service=service,
                limit=limit
            )

            incidents = [dict(record["i"]) for record in result]
            logger.info("similar_incidents_found", service=service, count=len(incidents))
            return incidents

    def find_impact_chain(self, service: str) -> List[Dict[str, Any]]:
        """Find downstream dependencies and potential impact chain"""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH path = (s:Service {name: $service})-[:DEPENDS_ON*]->(downstream)
                RETURN path, downstream, length(path) as depth
                ORDER BY depth ASC
                """,
                service=service
            )

            chain = []
            for record in result:
                chain.append({
                    "service": dict(record["downstream"]),
                    "depth": record["depth"]
                })

            logger.info("impact_chain_found", service=service, count=len(chain))
            return chain

    def add_resolution(self, incident_id: str, resolution_steps: List[str], success: bool = True):
        """Add resolution steps to incident"""
        with self.driver.session() as session:
            session.run(
                """
                MATCH (i:Incident {incident_id: $incident_id})
                SET i.resolution_steps = $steps,
                    i.resolved = $success,
                    i.resolved_at = datetime()
                """,
                incident_id=incident_id,
                steps=resolution_steps,
                success=success
            )
            logger.info("resolution_added", incident_id=incident_id, success=success)

    def query_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute custom Cypher query"""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]


# Global Neo4j client instance
neo4j_client = Neo4jClient()
