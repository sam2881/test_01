"""DSPy Optimizer Service for prompt optimization"""
import dspy
from dspy.teleprompt import BootstrapFewShot, MIPRO
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()


class DSPyOptimizer:
    """Service for optimizing DSPy modules"""

    def __init__(self):
        # Configure DSPy with OpenAI
        dspy.settings.configure(
            lm=dspy.OpenAI(model="gpt-4", max_tokens=2000)
        )
        logger.info("dspy_optimizer_initialized")

    def optimize_module(
        self,
        module: dspy.Module,
        training_examples: List[dspy.Example],
        metric_fn: callable,
        method: str = "bootstrap"
    ) -> dspy.Module:
        """
        Optimize a DSPy module using specified method

        Args:
            module: DSPy module to optimize
            training_examples: Training examples
            metric_fn: Metric function for evaluation
            method: Optimization method ('bootstrap' or 'mipro')

        Returns:
            Optimized DSPy module
        """
        logger.info("optimization_started", method=method, examples=len(training_examples))

        try:
            if method == "bootstrap":
                optimizer = BootstrapFewShot(
                    metric=metric_fn,
                    max_bootstrapped_demos=4,
                    max_labeled_demos=4
                )
            elif method == "mipro":
                optimizer = MIPRO(
                    metric=metric_fn,
                    num_candidates=10,
                    init_temperature=1.0
                )
            else:
                raise ValueError(f"Unknown optimization method: {method}")

            # Compile the module
            optimized = optimizer.compile(
                module,
                trainset=training_examples
            )

            logger.info("optimization_completed", method=method)
            return optimized

        except Exception as e:
            logger.error("optimization_error", error=str(e), method=method)
            raise

    def create_training_example(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> dspy.Example:
        """Create a training example from inputs and expected outputs"""
        return dspy.Example(**inputs, **outputs).with_inputs(*inputs.keys())

    def evaluate_module(
        self,
        module: dspy.Module,
        test_examples: List[dspy.Example],
        metric_fn: callable
    ) -> float:
        """Evaluate module performance"""
        from dspy.evaluate import Evaluate

        evaluator = Evaluate(
            devset=test_examples,
            metric=metric_fn,
            num_threads=4,
            display_progress=True
        )

        score = evaluator(module)
        logger.info("evaluation_completed", score=score)
        return score


# Example metric functions
def accuracy_metric(example, prediction, trace=None) -> bool:
    """Simple accuracy metric"""
    return example.output == prediction.output


def classification_metric(example, prediction, trace=None) -> bool:
    """Classification accuracy metric"""
    return example.label == prediction.label


# Global optimizer instance
optimizer = DSPyOptimizer()
