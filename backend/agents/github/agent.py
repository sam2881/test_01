"""GitHub Agent for PR creation and repository management"""
import os
import sys
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from github import Github

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent
import structlog

logger = structlog.get_logger()

app = FastAPI(title="GitHub Agent")


class GitHubTask(BaseModel):
    """GitHub task schema"""
    task_id: str
    task_type: str
    branch_name: str
    pr_title: str
    pr_description: str
    code_changes: Dict[str, str]  # file_path: content


class GitHubAgent(BaseAgent):
    """Agent for handling GitHub operations"""

    def __init__(self):
        super().__init__(agent_name="GitHubAgent", agent_type="version_control")

        # Initialize GitHub client
        github_token = os.getenv("GITHUB_TOKEN", "")
        self.org = os.getenv("GITHUB_ORG", "")
        self.repo_name = os.getenv("GITHUB_REPO", "")

        try:
            self.gh = Github(github_token)
            self.repo = self.gh.get_repo(f"{self.org}/{self.repo_name}")
            logger.info("github_client_initialized", repo=f"{self.org}/{self.repo_name}")
        except Exception as e:
            logger.warning("github_client_init_failed", error=str(e))
            self.gh = None

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate task input"""
        return all(k in task for k in ["task_id", "branch_name", "pr_title"])

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process GitHub task - create branch and PR"""
        if not self.gh:
            raise ValueError("GitHub client not configured")

        branch_name = task["branch_name"]
        pr_title = task["pr_title"]
        pr_description = task.get("pr_description", "")
        code_changes = task.get("code_changes", {})

        logger.info("processing_github_task", branch=branch_name)

        try:
            # Get main branch
            main_branch = self.repo.get_branch("main")
            main_sha = main_branch.commit.sha

            # Create new branch
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=main_sha
            )
            logger.info("branch_created", branch=branch_name)

            # Create/update files
            for file_path, content in code_changes.items():
                try:
                    # Try to get existing file
                    file = self.repo.get_contents(file_path, ref=branch_name)
                    self.repo.update_file(
                        path=file_path,
                        message=f"Update {file_path}",
                        content=content,
                        sha=file.sha,
                        branch=branch_name
                    )
                except:
                    # File doesn't exist, create it
                    self.repo.create_file(
                        path=file_path,
                        message=f"Create {file_path}",
                        content=content,
                        branch=branch_name
                    )
                logger.info("file_committed", file=file_path, branch=branch_name)

            # Create pull request
            pr = self.repo.create_pull(
                title=pr_title,
                body=pr_description,
                head=branch_name,
                base="main"
            )
            logger.info("pr_created", pr_number=pr.number, url=pr.html_url)

            return {
                "branch": branch_name,
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "files_changed": list(code_changes.keys())
            }

        except Exception as e:
            logger.error("github_operation_error", error=str(e))
            raise


agent = GitHubAgent()


@app.post("/process")
async def process_github_task(task: GitHubTask):
    """Process GitHub task"""
    try:
        result = agent.run(task.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "GitHubAgent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8012)
