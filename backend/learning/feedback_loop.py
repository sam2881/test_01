#!/usr/bin/env python3
"""
Learning Loop - STEP 7
Implements continuous learning from executed resolutions
- Stores successful resolutions in Vector DB
- Updates Neo4j graph with incident → solution relationships
- Enriches knowledge base over time
"""
from typing import Dict, List, Optional
from datetime import datetime
import structlog

from backend.rag.weaviate_client import WeaviateClient
from backend.rag.neo4j_client import Neo4jClient
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()


class LearningLoop:
    """
    Continuous learning system that improves from each resolution
    Implements STEP 7 of enhanced workflow
    """

    def __init__(
        self,
        weaviate_client: WeaviateClient,
        neo4j_client: Neo4jClient,
        embedding_model: Optional[SentenceTransformer] = None
    ):
        self.weaviate = weaviate_client
        self.neo4j = neo4j_client
        self.embedding_model = embedding_model or SentenceTransformer('all-MiniLM-L6-v2')

    async def learn_from_resolution(
        self,
        ticket_id: str,
        ticket_text: str,
        agent_name: str,
        resolution: Dict,
        execution_result: Dict,
        success: bool = True
    ):
        """
        Main learning function - called after incident resolution

        Args:
            ticket_id: Unique incident ID
            ticket_text: Original incident description
            agent_name: Which agent handled it
            resolution: The resolution plan that was executed
            execution_result: Outcome of execution
            success: Whether resolution was successful
        """
        if not success:
            logger.info("skipping_failed_resolution", ticket_id=ticket_id)
            return

        logger.info(
            "learning_from_resolution",
            ticket_id=ticket_id,
            agent=agent_name
        )

        # Step 1: Create embeddings
        await self._store_embeddings(
            ticket_id=ticket_id,
            ticket_text=ticket_text,
            resolution=resolution,
            agent_name=agent_name,
            execution_result=execution_result
        )

        # Step 2: Update knowledge graph
        await self._update_knowledge_graph(
            ticket_id=ticket_id,
            agent_name=agent_name,
            resolution=resolution,
            execution_result=execution_result
        )

        logger.info("learning_complete", ticket_id=ticket_id)

    # ===========================
    # Vector DB Updates
    # ===========================

    async def _store_embeddings(
        self,
        ticket_id: str,
        ticket_text: str,
        resolution: Dict,
        agent_name: str,
        execution_result: Dict
    ):
        """
        Store resolution in Vector DB for future similarity search
        Implements: "Push to Vector DB: new embeddings, new cluster examples"
        """
        # Extract resolution text
        resolution_text = self._extract_resolution_text(resolution)

        # Create combined text for embedding
        combined_text = f"""
        Incident: {ticket_text}

        Resolution:
        {resolution_text}

        Result: {execution_result.get('status', 'success')}
        """.strip()

        # Store as new incident with resolution
        incident_data = {
            "incident_id": ticket_id,
            "title": ticket_text[:100],  # Truncate
            "description": ticket_text,
            "resolution": resolution_text,
            "agent": agent_name,
            "resolved_at": datetime.utcnow().isoformat(),
            "execution_commands": resolution.get('commands', []),
            "risk_level": resolution.get('risk_level', 'unknown'),
            "success": True
        }

        try:
            # Add to Weaviate
            self.weaviate.add_incident(incident_data)

            logger.info(
                "embeddings_stored",
                ticket_id=ticket_id,
                agent=agent_name
            )

        except Exception as e:
            logger.error(
                "embedding_storage_failed",
                ticket_id=ticket_id,
                error=str(e)
            )

    def _extract_resolution_text(self, resolution: Dict) -> str:
        """Extract human-readable resolution text from plan"""
        parts = []

        # Add steps
        if 'steps' in resolution:
            parts.append("Steps:")
            for i, step in enumerate(resolution['steps'], 1):
                if isinstance(step, dict):
                    step_text = step.get('description', str(step))
                else:
                    step_text = str(step)
                parts.append(f"{i}. {step_text}")

        # Add commands
        if 'commands' in resolution and resolution['commands']:
            parts.append("\nCommands executed:")
            for cmd in resolution['commands']:
                parts.append(f"- {cmd}")

        # Add files modified
        if 'files_to_edit' in resolution and resolution['files_to_edit']:
            parts.append("\nFiles modified:")
            for file in resolution['files_to_edit']:
                parts.append(f"- {file}")

        return "\n".join(parts)

    # ===========================
    # Knowledge Graph Updates
    # ===========================

    async def _update_knowledge_graph(
        self,
        ticket_id: str,
        agent_name: str,
        resolution: Dict,
        execution_result: Dict
    ):
        """
        Update Neo4j with incident → solution relationships
        Implements:
        - (Incident) → (Resolved By) → (Agent)
        - (Incident) → (Solution Step)
        - (Incident) → (Related Incident)
        - (Solution) → (Tool Used)
        """
        try:
            # Create incident node (if not exists)
            self.neo4j.create_incident_if_not_exists(ticket_id)

            # Create agent node (if not exists)
            self.neo4j.create_agent_node(agent_name)

            # Relationship: Incident → RESOLVED_BY → Agent
            self.neo4j.create_resolved_by_relationship(
                incident_id=ticket_id,
                agent_name=agent_name,
                resolved_at=datetime.utcnow()
            )

            # Create solution nodes
            solution_id = f"solution_{ticket_id}"
            self.neo4j.create_solution_node(
                solution_id=solution_id,
                resolution_data=resolution
            )

            # Relationship: Incident → HAS_SOLUTION → Solution
            self.neo4j.create_incident_solution_relationship(
                incident_id=ticket_id,
                solution_id=solution_id
            )

            # Extract and link tools used
            tools_used = self._extract_tools_used(resolution)
            for tool in tools_used:
                self.neo4j.create_tool_node(tool)
                self.neo4j.create_solution_uses_tool_relationship(
                    solution_id=solution_id,
                    tool_name=tool
                )

            # Find and link related incidents (similarity)
            await self._link_related_incidents(ticket_id)

            logger.info(
                "graph_updated",
                ticket_id=ticket_id,
                agent=agent_name,
                tools=len(tools_used)
            )

        except Exception as e:
            logger.error(
                "graph_update_failed",
                ticket_id=ticket_id,
                error=str(e)
            )

    def _extract_tools_used(self, resolution: Dict) -> List[str]:
        """Extract list of tools/technologies used in resolution"""
        tools = set()

        # From commands
        commands = resolution.get('commands', [])
        for cmd in commands:
            # Extract tool names from commands
            if 'ansible' in cmd.lower():
                tools.add('Ansible')
            if 'terraform' in cmd.lower():
                tools.add('Terraform')
            if 'kubectl' in cmd.lower():
                tools.add('Kubernetes')
            if 'docker' in cmd.lower():
                tools.add('Docker')
            if 'psql' in cmd.lower() or 'sql' in cmd.lower():
                tools.add('PostgreSQL')
            if 'airflow' in cmd.lower():
                tools.add('Airflow')

        # From APIs called
        apis = resolution.get('apis_to_call', [])
        for api in apis:
            if 'servicenow' in api.lower():
                tools.add('ServiceNow')
            if 'jira' in api.lower():
                tools.add('Jira')
            if 'github' in api.lower():
                tools.add('GitHub')

        return list(tools)

    async def _link_related_incidents(self, ticket_id: str):
        """Find and link related incidents using similarity search"""
        # Get incident details
        incident = self.neo4j.get_incident(ticket_id)
        if not incident:
            return

        # Find similar incidents from Weaviate
        incident_text = f"{incident.get('title', '')} {incident.get('description', '')}"
        similar = self.weaviate.search_similar_incidents(incident_text, limit=3)

        # Create relationships to similar incidents
        for similar_incident in similar:
            similar_id = similar_incident.get('incident_id')
            if similar_id and similar_id != ticket_id:
                self.neo4j.create_related_incident_relationship(
                    incident_id=ticket_id,
                    related_incident_id=similar_id,
                    similarity_score=0.8  # Could calculate actual similarity
                )

        logger.info(
            "related_incidents_linked",
            ticket_id=ticket_id,
            count=len(similar)
        )

    # ===========================
    # Continuous Improvement
    # ===========================

    async def enrich_runbook_library(
        self,
        ticket_id: str,
        resolution: Dict,
        create_new_runbook: bool = True
    ):
        """
        Optionally create new runbook from successful resolution
        """
        if not create_new_runbook:
            return

        # Extract runbook content
        runbook = {
            "runbook_id": f"runbook_{ticket_id}",
            "title": f"Resolution for {ticket_id}",
            "description": self._extract_resolution_text(resolution),
            "steps": resolution.get('steps', []),
            "commands": resolution.get('commands', []),
            "created_from_incident": ticket_id,
            "created_at": datetime.utcnow().isoformat()
        }

        try:
            self.weaviate.add_runbook(runbook)

            logger.info(
                "runbook_created",
                runbook_id=runbook['runbook_id'],
                from_incident=ticket_id
            )

        except Exception as e:
            logger.error(
                "runbook_creation_failed",
                error=str(e)
            )

    async def get_learning_stats(self) -> Dict:
        """Get statistics about learning loop"""
        # Count resolved incidents
        resolved_count = self.neo4j.count_resolved_incidents()

        # Count solutions
        solution_count = self.neo4j.count_solutions()

        # Count tools
        tool_count = self.neo4j.count_tools()

        # Most used agents
        agent_stats = self.neo4j.get_agent_resolution_counts()

        # Most used tools
        tool_stats = self.neo4j.get_tool_usage_counts()

        return {
            "resolved_incidents": resolved_count,
            "solutions_stored": solution_count,
            "tools_identified": tool_count,
            "agent_stats": agent_stats,
            "tool_stats": tool_stats
        }
