"""Base Agent class with common functionality for all domain agents"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import os
import uuid
from datetime import datetime
from langfuse import Langfuse
from openai import OpenAI
from anthropic import Anthropic
import dspy
import structlog

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Base class for all domain agents"""

    def __init__(self, agent_name: str, agent_type: str):
        self.agent_name = agent_name
        self.agent_type = agent_type

        # LLM Clients
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        # LangFuse for observability
        self.langfuse = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
        )

        # DSPy Configuration
        dspy.settings.configure(
            lm=dspy.OpenAI(
                model="gpt-4",
                api_key=os.getenv("OPENAI_API_KEY")
            )
        )

        logger.info("agent_initialized", agent=agent_name, type=agent_type)

    def create_trace(self, task_id: str, task_name: str) -> Any:
        """Create LangFuse trace for observability"""
        return self.langfuse.trace(
            name=f"{self.agent_name}_{task_name}",
            id=task_id,
            metadata={
                "agent": self.agent_name,
                "type": self.agent_type,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def create_span(self, trace, span_name: str, **metadata) -> Any:
        """Create span within trace"""
        return trace.span(
            name=span_name,
            metadata={
                "agent": self.agent_name,
                **metadata
            }
        )

    def log_event(self, event_type: str, payload: Dict[str, Any], status: str = "pending"):
        """Log agent event"""
        event_id = str(uuid.uuid4())
        logger.info(
            "agent_event",
            event_id=event_id,
            agent=self.agent_name,
            event_type=event_type,
            status=status,
            payload=payload
        )
        return event_id

    @abstractmethod
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process task - must be implemented by subclasses"""
        pass

    @abstractmethod
    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate input task - must be implemented by subclasses"""
        pass

    def handle_error(self, error: Exception, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors gracefully"""
        logger.error(
            "agent_error",
            agent=self.agent_name,
            error=str(error),
            task_id=task.get("task_id")
        )
        return {
            "status": "error",
            "agent": self.agent_name,
            "error": str(error),
            "task_id": task.get("task_id")
        }

    def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method with error handling and tracing"""
        task_id = task.get("task_id", str(uuid.uuid4()))

        try:
            # Validate input
            if not self.validate_input(task):
                raise ValueError("Invalid task input")

            # Create trace
            trace = self.create_trace(task_id, task.get("task_type", "unknown"))

            # Process task
            with self.create_span(trace, "process_task", task_type=task.get("task_type")):
                result = self.process_task(task)

            # Log success
            self.log_event(
                event_type=f"{self.agent_name}_completed",
                payload={"task_id": task_id, "result": result},
                status="success"
            )

            return {
                "status": "success",
                "agent": self.agent_name,
                "task_id": task_id,
                "result": result
            }

        except Exception as e:
            return self.handle_error(e, task)
