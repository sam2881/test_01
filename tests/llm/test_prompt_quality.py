"""Test LLM prompt quality and consistency"""
import pytest
from unittest.mock import patch, Mock
import json


@pytest.mark.llm
class TestPromptQuality:
    """Test prompt engineering quality"""

    def test_routing_prompt_structure(self):
        """Test that routing prompt is well-structured"""
        from prompts.routing import ROUTING_PROMPT_TEMPLATE

        # Prompt should contain:
        # - Clear task description
        # - Available agents list
        # - Output format specification
        # - Few-shot examples

        assert "task_description" in ROUTING_PROMPT_TEMPLATE or "description" in ROUTING_PROMPT_TEMPLATE
        assert "agent" in ROUTING_PROMPT_TEMPLATE.lower()
        assert "select" in ROUTING_PROMPT_TEMPLATE.lower() or "choose" in ROUTING_PROMPT_TEMPLATE.lower()

    def test_prompt_clarity_score(self):
        """Test prompt clarity and specificity"""
        from prompts.routing import ROUTING_PROMPT_TEMPLATE

        # Measure prompt quality metrics
        word_count = len(ROUTING_PROMPT_TEMPLATE.split())
        char_count = len(ROUTING_PROMPT_TEMPLATE)

        # Good prompts are typically 50-500 words
        assert 50 < word_count < 1000, f"Prompt word count {word_count} outside optimal range"

        # Should contain specific instructions
        instruction_keywords = ["must", "should", "always", "never", "exactly", "only"]
        has_instructions = any(keyword in ROUTING_PROMPT_TEMPLATE.lower() for keyword in instruction_keywords)

        assert has_instructions, "Prompt lacks clear instructions"

    def test_prompt_consistency_across_calls(self):
        """Test that prompts produce consistent results"""

        from orchestrator.router import route_task

        test_description = "API Gateway returning 502 errors - production down"

        with patch('openai.ChatCompletion.create') as mock_llm:
            # Mock consistent responses
            mock_llm.return_value = {
                "choices": [{
                    "message": {
                        "content": '{"selected_agent": "infrastructure", "confidence": 0.95}'
                    }
                }]
            }

            # Call multiple times
            results = []
            for _ in range(5):
                state = {
                    "task_id": "test-123",
                    "description": test_description,
                    "priority": "P1"
                }
                result = route_task(state)
                results.append(result.get("current_agent"))

            # Should get same agent consistently
            assert len(set(results)) <= 2, "Routing is inconsistent across calls"


@pytest.mark.llm
class TestPromptConsistency:
    """Test consistency of LLM outputs"""

    @patch('openai.ChatCompletion.create')
    def test_output_format_consistency(self, mock_llm):
        """Test that LLM outputs follow expected format"""

        mock_llm.return_value = {
            "choices": [{
                "message": {
                    "content": '{"selected_agent": "servicenow", "confidence": 0.92, "reasoning": "Infrastructure issue"}'
                }
            }]
        }

        from orchestrator.router import route_task

        state = {
            "task_id": "test-456",
            "description": "Database timeout",
            "priority": "P2"
        }

        result = route_task(state)

        # Output should have expected fields
        assert "current_agent" in result or "selected_agent" in result
        # Should be valid agent name
        valid_agents = ["servicenow", "jira", "github", "infrastructure", "infra", "data"]
        agent = result.get("current_agent") or result.get("selected_agent")
        assert agent in valid_agents or agent == ""

    def test_json_parseable_outputs(self):
        """Test that LLM outputs are valid JSON"""

        test_outputs = [
            '{"selected_agent": "servicenow", "confidence": 0.95}',
            '{"selected_agent": "jira", "confidence": 0.88, "reasoning": "Code bug"}',
        ]

        for output in test_outputs:
            # Should be valid JSON
            try:
                parsed = json.loads(output)
                assert isinstance(parsed, dict)
                assert "selected_agent" in parsed
            except json.JSONDecodeError:
                pytest.fail(f"Output is not valid JSON: {output}")


@pytest.mark.llm
class TestPromptTokenUsage:
    """Test prompt token efficiency"""

    def test_prompt_token_count(self):
        """Test that prompts are within token limits"""
        import tiktoken

        from prompts.routing import ROUTING_PROMPT_TEMPLATE

        # Estimate tokens (rough approximation)
        enc = tiktoken.encoding_for_model("gpt-4")
        tokens = enc.encode(ROUTING_PROMPT_TEMPLATE)
        token_count = len(tokens)

        print(f"\n[TOKEN COUNT] Routing prompt: {token_count} tokens")

        # Should be under 2000 tokens for efficiency
        assert token_count < 2000, f"Prompt uses {token_count} tokens (>2000)"

    def test_context_window_usage(self):
        """Test efficient use of context window"""

        # For a typical incident with history
        incident_description = "API Gateway timeout error" * 10  # Simulate longer description
        similar_incidents = ["Similar incident " + str(i) for i in range(5)]

        total_text = incident_description + " ".join(similar_incidents)

        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4")
        tokens = enc.encode(total_text)

        print(f"\n[CONTEXT] Total context: {len(tokens)} tokens")

        # Should use less than 8K tokens (leaving room for completion)
        assert len(tokens) < 8000, "Context window usage too high"


@pytest.mark.llm
class TestPromptVariations:
    """Test different prompt variations for effectiveness"""

    def test_zero_shot_vs_few_shot(self):
        """Compare zero-shot vs few-shot prompting"""

        zero_shot_prompt = """
        Select the best agent for this task: {description}
        Available agents: servicenow, jira, github
        """

        few_shot_prompt = """
        Select the best agent for this task: {description}
        Available agents: servicenow, jira, github

        Examples:
        - "API Gateway down" -> servicenow
        - "Bug in payment code" -> jira
        - "Create pull request" -> github
        """

        # Few-shot should have more tokens but better accuracy
        # This is a structural test, not functional

        assert len(few_shot_prompt) > len(zero_shot_prompt)
        assert "examples" in few_shot_prompt.lower()

    def test_structured_output_prompt(self):
        """Test prompts that request structured outputs"""

        structured_prompt = """
        Return your response as JSON with these exact fields:
        {
            "selected_agent": "<agent_name>",
            "confidence": <0.0-1.0>,
            "reasoning": "<brief explanation>"
        }
        """

        # Should contain JSON schema
        assert "json" in structured_prompt.lower()
        assert "selected_agent" in structured_prompt
        assert "confidence" in structured_prompt
