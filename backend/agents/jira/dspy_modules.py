"""DSPy modules for Jira agent - story processing and code generation"""
import dspy


class StoryBreakdown(dspy.Signature):
    """Break down Jira story into implementable tasks"""
    story_description = dspy.InputField(desc="Jira story description and requirements")
    codebase_context = dspy.InputField(desc="Relevant codebase context and patterns")

    tasks = dspy.OutputField(desc="List of specific implementation tasks")
    technical_approach = dspy.OutputField(desc="High-level technical approach")
    dependencies = dspy.OutputField(desc="External dependencies or prerequisites")
    estimated_effort = dspy.OutputField(desc="Estimated effort in story points")


class CodeGenerator(dspy.Signature):
    """Generate code for a specific task"""
    task_description = dspy.InputField()
    existing_code_context = dspy.InputField()
    coding_standards = dspy.InputField()

    code = dspy.OutputField(desc="Generated code implementation")
    file_path = dspy.OutputField(desc="Suggested file path")
    test_cases = dspy.OutputField(desc="Unit test cases")
    documentation = dspy.OutputField(desc="Code documentation and comments")


class JiraModule(dspy.Module):
    """Complete DSPy module for Jira story processing"""

    def __init__(self):
        super().__init__()
        self.breakdown = dspy.ChainOfThought(StoryBreakdown)
        self.code_gen = dspy.ChainOfThought(CodeGenerator)

    def forward(self, story_description: str, codebase_context: str, coding_standards: str):
        """Process Jira story"""
        # Break down story
        breakdown_result = self.breakdown(
            story_description=story_description,
            codebase_context=codebase_context
        )

        return dspy.Prediction(
            tasks=breakdown_result.tasks,
            technical_approach=breakdown_result.technical_approach,
            dependencies=breakdown_result.dependencies,
            estimated_effort=breakdown_result.estimated_effort
        )
