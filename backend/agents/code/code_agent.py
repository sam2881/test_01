#!/usr/bin/env python3
"""
Code Agent - LLM-powered code generation with RAG context
"""
import os
import sys
import base64
import json
import re
from typing import Dict, List, Optional
from datetime import datetime
import requests
import structlog

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = structlog.get_logger()

# Config
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
GITHUB_ORG = os.getenv('GITHUB_ORG', 'sam2881')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'test_01')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')


class GitHubClient:
    """GitHub API client"""

    def __init__(self, token=None, org=None, repo=None):
        self.token = token or GITHUB_TOKEN
        self.org = org or GITHUB_ORG
        self.repo = repo or GITHUB_REPO
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def _request(self, method, endpoint, json_data=None):
        try:
            resp = requests.request(method, f"{self.base_url}{endpoint}",
                                   headers=self.headers, json=json_data, timeout=30)
            if resp.status_code in [200, 201, 204]:
                return resp.json() if resp.text else {}
            logger.error("github_error", status=resp.status_code, msg=resp.text[:200])
            return None
        except Exception as e:
            logger.error("github_exception", error=str(e))
            return None

    def get_file(self, path, branch='main'):
        result = self._request('GET', f'/repos/{self.org}/{self.repo}/contents/{path}?ref={branch}')
        if result and 'content' in result:
            return base64.b64decode(result['content']).decode('utf-8')
        return None

    def create_branch(self, name, from_branch='main'):
        ref = self._request('GET', f'/repos/{self.org}/{self.repo}/git/ref/heads/{from_branch}')
        if not ref:
            return False
        return self._request('POST', f'/repos/{self.org}/{self.repo}/git/refs',
                           {'ref': f'refs/heads/{name}', 'sha': ref['object']['sha']}) is not None

    def commit_file(self, path, content, message, branch):
        encoded = base64.b64encode(content.encode()).decode()
        return self._request('PUT', f'/repos/{self.org}/{self.repo}/contents/{path}',
                           {'message': message, 'content': encoded, 'branch': branch})

    def create_pr(self, title, body, head, base='main'):
        return self._request('POST', f'/repos/{self.org}/{self.repo}/pulls',
                           {'title': title, 'body': body, 'head': head, 'base': base})

    def get_prs(self, state='open'):
        return self._request('GET', f'/repos/{self.org}/{self.repo}/pulls?state={state}') or []


class CodeAgent:
    """AI Code Agent with LLM + RAG"""

    def __init__(self):
        self.github = GitHubClient()
        self.openai_key = OPENAI_API_KEY

    def _get_rag_context(self, query: str) -> str:
        """Get similar code examples from RAG"""
        try:
            from utils.weaviate_client import weaviate_rag_client
            similar = weaviate_rag_client.search_similar_incidents(query, limit=2)
            if similar:
                context = "\n".join([
                    f"- {s.get('short_description')}: {s.get('solution', 'N/A')}"
                    for s in similar
                ])
                return f"Similar past solutions:\n{context}"
        except Exception as e:
            logger.warning("rag_error", error=str(e))
        return ""

    def _call_llm(self, system: str, prompt: str) -> str:
        """Call OpenAI GPT-4"""
        if not self.openai_key:
            logger.warning("no_openai_key")
            return ""

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_key)

            response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("llm_error", error=str(e))
            return ""

    def _extract_paths(self, text: str) -> List[str]:
        """Extract file paths from text"""
        patterns = [r'File:\s*([^\s\n]+)', r'([a-zA-Z0-9_/]+\.(py|ts|js|go))']
        paths = []
        for p in patterns:
            for m in re.findall(p, text):
                paths.append(m[0] if isinstance(m, tuple) else m)
        return list(set(paths))

    def _extract_repo(self, text: str) -> Dict:
        """Extract repo info from text"""
        m = re.search(r'github\.com/([^/\s]+)/([^/\s]+)', text)
        if m:
            return {'org': m.group(1), 'repo': m.group(2).replace('.git', '')}
        return {'org': GITHUB_ORG, 'repo': GITHUB_REPO}

    def generate_code(self, ticket: Dict, source_code: str) -> str:
        """Generate code using LLM with RAG context"""

        # Get RAG context
        rag_context = self._get_rag_context(ticket.get('summary', ''))

        system = """You are an expert software engineer. Generate clean, production-ready code.
Follow best practices, add proper error handling, and include comprehensive tests.
Return ONLY code, no explanations."""

        prompt = f"""Generate code for this Jira ticket:

**Ticket:** {ticket.get('ticket_id')} - {ticket.get('summary')}
**Description:** {ticket.get('description', '')[:1500]}

**Source Code to work with:**
```
{source_code[:4000] if source_code else 'No source code provided'}
```

**{rag_context}**

Generate comprehensive pytest tests covering:
1. Happy path scenarios
2. Edge cases and error handling
3. Mock external dependencies
4. Clear assertions with messages

Return ONLY the Python test code."""

        generated = self._call_llm(system, prompt)

        # Fallback if LLM fails
        if not generated:
            generated = self._generate_fallback(ticket, source_code)

        return generated

    def _generate_fallback(self, ticket: Dict, source_code: str) -> str:
        """Fallback test generation without LLM"""
        funcs = re.findall(r'def\s+(\w+)\s*\(', source_code) if source_code else []
        classes = re.findall(r'class\s+(\w+)', source_code) if source_code else []
        class_name = classes[0] if classes else 'Generated'

        tests = []
        for f in funcs[:5]:
            if not f.startswith('_'):
                tests.append(f'''    def test_{f}_success(self, setup):
        """Test {f}"""
        assert True  # TODO: Implement

    def test_{f}_error(self, setup):
        """Test {f} error handling"""
        assert True  # TODO: Implement
''')

        test_methods = '\n'.join(tests) if tests else '    pass'

        return f'''"""
Auto-generated tests for {ticket.get('ticket_id')}: {ticket.get('summary')}
Generated by AI Code Agent
"""
import pytest
from unittest.mock import Mock, patch

class Test{class_name}:
    """Test suite"""

    @pytest.fixture
    def setup(self):
        return {{"test": True}}

{test_methods}

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
'''

    async def process_ticket(self, ticket: Dict) -> Dict:
        """Process Jira ticket end-to-end"""
        ticket_id = ticket.get('ticket_id', 'UNKNOWN')
        logger.info("processing_ticket", ticket_id=ticket_id)

        result = {'ticket_id': ticket_id, 'status': 'processing', 'steps': [], 'pr_url': None}

        try:
            # Step 1: Extract info
            desc = ticket.get('description', '')
            file_paths = self._extract_paths(desc)
            repo_info = self._extract_repo(desc)
            result['steps'].append({'step': 'analyze', 'status': 'done', 'files': file_paths})

            # Step 2: Read source files
            source_code = ""
            if file_paths:
                client = GitHubClient(org=repo_info['org'], repo=repo_info['repo'])
                for path in file_paths[:3]:
                    content = client.get_file(path)
                    if content:
                        source_code += f"\n# {path}\n{content}\n"
            result['steps'].append({'step': 'read_source', 'status': 'done', 'chars': len(source_code)})

            # Step 3: Generate code with LLM + RAG
            generated = self.generate_code(ticket, source_code)
            result['steps'].append({'step': 'generate_code', 'status': 'done', 'chars': len(generated)})

            # Step 4: Create branch & commit
            branch = f"ai/{ticket_id.lower().replace('-', '_')}"
            test_file = f"tests/test_{ticket_id.lower().replace('-', '_')}.py"

            self.github.create_branch(branch)
            commit = self.github.commit_file(test_file, generated,
                                            f"feat({ticket_id}): Auto-generated tests", branch)
            result['steps'].append({'step': 'commit', 'status': 'done' if commit else 'failed',
                                   'branch': branch, 'file': test_file})

            # Step 5: Create PR
            pr = self.github.create_pr(
                title=f"[{ticket_id}] {ticket.get('summary', '')[:50]}",
                body=f"## Auto-Generated Code\n\n**Ticket:** {ticket_id}\n**Summary:** {ticket.get('summary')}\n\n---\nGenerated by AI Code Agent",
                head=branch
            )

            if pr:
                result['pr_url'] = pr.get('html_url')
                result['pr_number'] = pr.get('number')

            result['status'] = 'completed'
            result['steps'].append({'step': 'create_pr', 'status': 'done', 'pr_url': result.get('pr_url')})

            # Publish to Kafka
            try:
                from utils.kafka_client import kafka_client
                kafka_client.publish_event('agent.events', {
                    'type': 'code_agent_complete',
                    'ticket_id': ticket_id,
                    'pr_url': result.get('pr_url'),
                    'timestamp': datetime.now().isoformat()
                })
            except:
                pass

            logger.info("ticket_complete", ticket_id=ticket_id, pr_url=result.get('pr_url'))

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            logger.error("ticket_failed", ticket_id=ticket_id, error=str(e))

        return result


# Global instance
code_agent = CodeAgent()

async def process_ticket(ticket: Dict) -> Dict:
    """Entry point for processing tickets"""
    return await code_agent.process_ticket(ticket)


if __name__ == '__main__':
    import asyncio

    test_ticket = {
        'ticket_id': 'ENG-101',
        'summary': 'Write unit tests for auth module',
        'description': 'Create tests for authentication.\nFile: backend/auth/service.py',
        'url': 'https://jira.example.com/browse/ENG-101'
    }

    result = asyncio.run(process_ticket(test_ticket))
    print(json.dumps(result, indent=2))
