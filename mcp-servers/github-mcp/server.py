#!/usr/bin/env python3
"""
GitHub MCP Server
Provides MCP protocol access to GitHub APIs
"""
import os
import sys
import asyncio
import time
from typing import Any, Dict, List, Optional
from github import Github
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Add parent directory for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.metrics import start_metrics_server, ToolMetrics, APIMetrics

# Server name and metrics port
SERVER_NAME = "github-mcp"
METRICS_PORT = int(os.getenv("METRICS_PORT", "8092"))


class GitHubMCPServer:
    """MCP Server for GitHub integration"""

    def __init__(self):
        # Initialize GitHub client
        self.github_token = os.getenv("GITHUB_TOKEN")

        if not self.github_token:
            raise ValueError("GitHub token not configured in environment")

        self.client = Github(self.github_token)

        # Create server
        self.server = Server("github-mcp")

        # Register tools
        self._register_tools()

    def _register_tools(self):
        """Register all GitHub tools"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_repository",
                    description="Get repository information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {
                                "type": "string",
                                "description": "Repository owner"
                            },
                            "repo": {
                                "type": "string",
                                "description": "Repository name"
                            }
                        },
                        "required": ["owner", "repo"]
                    }
                ),
                Tool(
                    name="create_pull_request",
                    description="Create a new pull request",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"},
                            "title": {"type": "string"},
                            "body": {"type": "string"},
                            "head": {
                                "type": "string",
                                "description": "Source branch"
                            },
                            "base": {
                                "type": "string",
                                "description": "Target branch (default: main)"
                            }
                        },
                        "required": ["owner", "repo", "title", "head"]
                    }
                ),
                Tool(
                    name="create_issue",
                    description="Create a new GitHub issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"},
                            "title": {"type": "string"},
                            "body": {"type": "string"},
                            "labels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Issue labels (optional)"
                            }
                        },
                        "required": ["owner", "repo", "title"]
                    }
                ),
                Tool(
                    name="get_pull_request",
                    description="Get pull request details",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"},
                            "pr_number": {
                                "type": "integer",
                                "description": "PR number"
                            }
                        },
                        "required": ["owner", "repo", "pr_number"]
                    }
                ),
                Tool(
                    name="merge_pull_request",
                    description="Merge a pull request",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"},
                            "pr_number": {"type": "integer"},
                            "merge_method": {
                                "type": "string",
                                "enum": ["merge", "squash", "rebase"],
                                "default": "merge"
                            }
                        },
                        "required": ["owner", "repo", "pr_number"]
                    }
                ),
                Tool(
                    name="list_pull_requests",
                    description="List repository pull requests",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"},
                            "state": {
                                "type": "string",
                                "enum": ["open", "closed", "all"],
                                "default": "open"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 10
                            }
                        },
                        "required": ["owner", "repo"]
                    }
                ),
                Tool(
                    name="create_branch",
                    description="Create a new branch",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "owner": {"type": "string"},
                            "repo": {"type": "string"},
                            "branch_name": {"type": "string"},
                            "from_branch": {
                                "type": "string",
                                "description": "Source branch (default: main)",
                                "default": "main"
                            }
                        },
                        "required": ["owner", "repo", "branch_name"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            with ToolMetrics(SERVER_NAME, name):
                if name == "get_repository":
                    return await self._get_repository(
                        arguments["owner"],
                        arguments["repo"]
                    )

                elif name == "create_pull_request":
                    return await self._create_pull_request(
                        arguments["owner"],
                        arguments["repo"],
                        arguments["title"],
                        arguments.get("body", ""),
                        arguments["head"],
                        arguments.get("base", "main")
                    )

                elif name == "create_issue":
                    return await self._create_issue(
                        arguments["owner"],
                        arguments["repo"],
                        arguments["title"],
                        arguments.get("body", ""),
                        arguments.get("labels", [])
                    )

                elif name == "get_pull_request":
                    return await self._get_pull_request(
                        arguments["owner"],
                        arguments["repo"],
                        arguments["pr_number"]
                    )

                elif name == "merge_pull_request":
                    return await self._merge_pull_request(
                        arguments["owner"],
                        arguments["repo"],
                        arguments["pr_number"],
                        arguments.get("merge_method", "merge")
                    )

                elif name == "list_pull_requests":
                    return await self._list_pull_requests(
                        arguments["owner"],
                        arguments["repo"],
                        arguments.get("state", "open"),
                        arguments.get("limit", 10)
                    )

                elif name == "create_branch":
                    return await self._create_branch(
                        arguments["owner"],
                        arguments["repo"],
                        arguments["branch_name"],
                        arguments.get("from_branch", "main")
                    )

                else:
                    raise ValueError(f"Unknown tool: {name}")

    async def _get_repository(self, owner: str, repo: str) -> List[TextContent]:
        """Get repository information"""
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")

            text = f"""
Repository: {repository.full_name}
Description: {repository.description or 'None'}
Stars: {repository.stargazers_count}
Forks: {repository.forks_count}
Open Issues: {repository.open_issues_count}
Default Branch: {repository.default_branch}
Language: {repository.language or 'Unknown'}
Created: {repository.created_at}
URL: {repository.html_url}
            """.strip()

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> List[TextContent]:
        """Create pull request"""
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")

            pr = repository.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )

            text = f"""
Created Pull Request #{pr.number}
Title: {pr.title}
Branch: {head} → {base}
URL: {pr.html_url}
            """.strip()

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: List[str] = None
    ) -> List[TextContent]:
        """Create GitHub issue"""
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")

            issue = repository.create_issue(
                title=title,
                body=body,
                labels=labels or []
            )

            text = f"""
Created Issue #{issue.number}
Title: {issue.title}
Labels: {', '.join(labels) if labels else 'None'}
URL: {issue.html_url}
            """.strip()

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[TextContent]:
        """Get PR details"""
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            pr = repository.get_pull(pr_number)

            text = f"""
Pull Request #{pr.number}
Title: {pr.title}
State: {pr.state}
Branch: {pr.head.ref} → {pr.base.ref}
Author: {pr.user.login}
Created: {pr.created_at}
Mergeable: {pr.mergeable}
URL: {pr.html_url}
            """.strip()

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        merge_method: str = "merge"
    ) -> List[TextContent]:
        """Merge pull request"""
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            pr = repository.get_pull(pr_number)

            result = pr.merge(merge_method=merge_method)

            if result.merged:
                text = f"Successfully merged PR #{pr_number} using {merge_method}"
            else:
                text = f"Failed to merge PR #{pr_number}: {result.message}"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 10
    ) -> List[TextContent]:
        """List pull requests"""
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")
            prs = repository.get_pulls(state=state)[:limit]

            if not prs:
                return [TextContent(type="text", text=f"No {state} pull requests found")]

            text_lines = [f"Pull Requests ({state}):\n"]

            for pr in prs:
                text_lines.append(
                    f"- #{pr.number}: {pr.title} [{pr.state}]"
                )

            return [TextContent(type="text", text="\n".join(text_lines))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> List[TextContent]:
        """Create new branch"""
        try:
            repository = self.client.get_repo(f"{owner}/{repo}")

            # Get source branch SHA
            source = repository.get_branch(from_branch)
            sha = source.commit.sha

            # Create new branch
            repository.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=sha
            )

            text = f"Created branch '{branch_name}' from '{from_branch}'"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    # Start metrics server in background
    start_metrics_server(METRICS_PORT, SERVER_NAME)
    print(f"GitHub MCP Server starting (metrics on port {METRICS_PORT})")

    server = GitHubMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
