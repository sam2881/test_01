"""Jira Agent for story processing and task management"""
import os
import sys
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from jira import JIRA

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent
from agents.jira.dspy_modules import JiraModule
import structlog

logger = structlog.get_logger()

app = FastAPI(title="Jira Agent")


class JiraTask(BaseModel):
    """Jira task schema"""
    task_id: str
    task_type: str
    story_id: Optional[str] = None
    description: str
    project_key: Optional[str] = None


class JiraAgent(BaseAgent):
    """Agent for handling Jira stories and tasks"""

    def __init__(self):
        super().__init__(agent_name="JiraAgent", agent_type="devops_automation")

        # Initialize Jira client
        self.jira_url = os.getenv("JIRA_URL", "")
        self.jira_username = os.getenv("JIRA_USERNAME", "")
        self.jira_token = os.getenv("JIRA_API_TOKEN", "")
        self.project_key = os.getenv("JIRA_PROJECT_KEY", "ENG")

        try:
            self.jira_client = JIRA(
                server=self.jira_url,
                basic_auth=(self.jira_username, self.jira_token)
            )
            logger.info("jira_client_initialized", url=self.jira_url)
        except Exception as e:
            logger.warning("jira_client_init_failed", error=str(e))
            self.jira_client = None

        # Initialize DSPy module
        self.dspy_module = JiraModule()

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate task input"""
        return "task_id" in task and "description" in task

    def get_story_from_jira(self, story_id: str) -> Optional[Dict[str, Any]]:
        """Fetch story from Jira"""
        if not self.jira_client:
            return None

        try:
            issue = self.jira_client.issue(story_id)
            return {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None
            }
        except Exception as e:
            logger.error("jira_get_story_error", error=str(e), story_id=story_id)
            return None

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process Jira story task"""
        description = task["description"]
        story_id = task.get("story_id")

        logger.info("processing_jira_story", task_id=task["task_id"], story_id=story_id)

        # Get story details if available
        story_context = ""
        if story_id and self.jira_client:
            story = self.get_story_from_jira(story_id)
            if story:
                story_context = f"Story: {story['summary']}\n{story.get('description', '')}"

        # Run DSPy module
        result = self.dspy_module(
            story_description=description or story_context,
            codebase_context="Standard Python/JavaScript patterns",
            coding_standards="PEP 8 for Python, ESLint for JavaScript"
        )

        # Create sub-tasks in Jira if story_id provided
        if story_id and self.jira_client:
            try:
                for i, task_desc in enumerate(result.tasks.split("\n")[:5]):
                    if task_desc.strip():
                        self.jira_client.create_issue(
                            project=self.project_key,
                            summary=f"Task {i+1}: {task_desc[:50]}",
                            description=task_desc,
                            issuetype={"name": "Sub-task"},
                            parent={"key": story_id}
                        )
                logger.info("subtasks_created", story_id=story_id)
            except Exception as e:
                logger.error("subtask_creation_error", error=str(e))

        return {
            "breakdown": {
                "tasks": result.tasks,
                "technical_approach": result.technical_approach,
                "dependencies": result.dependencies,
                "estimated_effort": result.estimated_effort
            }
        }


agent = JiraAgent()


@app.post("/process")
async def process_story(task: JiraTask):
    """Process Jira story"""
    try:
        result = agent.run(task.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "JiraAgent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8011)
