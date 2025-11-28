"""LangGraph router for multi-agent orchestration"""
from typing import Any, Dict, Literal, TypedDict
from langgraph.graph import StateGraph, END
import dspy
import structlog

logger = structlog.get_logger()


class AgentState(TypedDict):
    """State shared across all agents"""
    task_id: str
    task_type: str
    description: str
    context: Dict[str, Any]
    current_agent: str
    results: Dict[str, Any]
    status: str
    error: str


class EventClassifier(dspy.Signature):
    """Classify incoming event to route to appropriate agent"""
    event_description = dspy.InputField()

    agent = dspy.OutputField(desc="Target agent: servicenow, jira, github, infra, data")
    confidence = dspy.OutputField(desc="Confidence score 0-100")
    reasoning = dspy.OutputField(desc="Reasoning for classification")


class AgentRouter:
    """Route tasks to appropriate agents using DSPy"""

    def __init__(self):
        self.classifier = dspy.ChainOfThought(EventClassifier)

    def route_task(self, state: AgentState) -> Literal["servicenow", "jira", "github", "infra", "data", "gcp_monitor", "end"]:
        """Route task to appropriate agent"""

        # Simple keyword-based routing as fallback
        description_lower = state["description"].lower()

        # Check for GCP-specific alerts
        if any(word in description_lower for word in ["gcp", "gce", "cloud sql", "gke", "compute engine", "cloud monitoring"]):
            state["current_agent"] = "gcp_monitor"
            return "gcp_monitor"
        elif any(word in description_lower for word in ["incident", "outage", "down", "p1", "p2"]):
            state["current_agent"] = "servicenow"
            return "servicenow"
        elif any(word in description_lower for word in ["story", "feature", "epic", "jira"]):
            state["current_agent"] = "jira"
            return "jira"
        elif any(word in description_lower for word in ["pr", "pull request", "merge", "github"]):
            state["current_agent"] = "github"
            return "github"
        elif any(word in description_lower for word in ["terraform", "ansible", "infrastructure", "deploy"]):
            state["current_agent"] = "infra"
            return "infra"
        elif any(word in description_lower for word in ["sql", "query", "etl", "data"]):
            state["current_agent"] = "data"
            return "data"
        else:
            # Use DSPy classifier for ambiguous cases
            try:
                result = self.classifier(event_description=state["description"])
                state["current_agent"] = result.agent
                logger.info("dspy_classification", agent=result.agent, confidence=result.confidence)
                return result.agent
            except:
                return "end"


def create_workflow() -> StateGraph:
    """Create LangGraph workflow"""

    workflow = StateGraph(AgentState)
    router = AgentRouter()

    # Add routing node
    workflow.add_node("router", lambda state: state)

    # Add agent nodes (placeholders - actual HTTP calls to agent services)
    workflow.add_node("servicenow", lambda state: {**state, "status": "processed"})
    workflow.add_node("jira", lambda state: {**state, "status": "processed"})
    workflow.add_node("github", lambda state: {**state, "status": "processed"})
    workflow.add_node("infra", lambda state: {**state, "status": "processed"})
    workflow.add_node("data", lambda state: {**state, "status": "processed"})
    workflow.add_node("gcp_monitor", lambda state: {**state, "status": "processed"})

    # Set entry point
    workflow.set_entry_point("router")

    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        router.route_task,
        {
            "servicenow": "servicenow",
            "jira": "jira",
            "github": "github",
            "infra": "infra",
            "data": "data",
            "gcp_monitor": "gcp_monitor",
            "end": END
        }
    )

    # All agents go to END
    workflow.add_edge("servicenow", END)
    workflow.add_edge("jira", END)
    workflow.add_edge("github", END)
    workflow.add_edge("infra", END)
    workflow.add_edge("data", END)
    workflow.add_edge("gcp_monitor", END)

    return workflow.compile()
