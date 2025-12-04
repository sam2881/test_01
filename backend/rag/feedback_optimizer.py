"""
Feedback Optimizer - ML-based weight optimization for search

Learns optimal search weights from execution outcomes:
- Tracks which scripts were recommended and executed
- Records success/failure of executions
- Adjusts weights based on incident type, severity, service

Uses reinforcement learning concepts to continuously improve.
"""

import os
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import structlog

logger = structlog.get_logger()


@dataclass
class FeedbackRecord:
    """Record of a search and execution outcome"""
    feedback_id: str
    incident_id: str
    incident_type: str
    severity: str
    service: str
    environment: str

    # Search info
    query: str
    weights_used: Dict[str, float]
    recommended_script_id: str
    recommendation_rank: int  # Where the successful script was in results

    # Execution outcome
    executed: bool = False
    success: bool = False
    execution_time_seconds: float = 0.0
    error_message: str = ""

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    executed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizedWeights:
    """Weights optimized for specific context"""
    incident_type: str
    semantic: float
    keyword: float
    metadata: float
    confidence: float  # How confident we are in these weights
    sample_count: int  # How many samples were used to derive

    def to_dict(self) -> Dict[str, float]:
        return {
            "semantic": self.semantic,
            "keyword": self.keyword,
            "metadata": self.metadata
        }


class FeedbackOptimizer:
    """
    Feedback-based optimizer for search weights.

    Learns optimal weights for different incident contexts by:
    1. Recording search and execution outcomes
    2. Analyzing patterns in successful executions
    3. Adjusting weights using gradient-free optimization

    Storage: JSON files for persistence (can be upgraded to PostgreSQL)
    """

    def __init__(
        self,
        data_dir: str = "./data/feedback",
        min_samples_for_optimization: int = 10
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.min_samples = min_samples_for_optimization
        self._feedback_records: List[FeedbackRecord] = []
        self._optimized_weights: Dict[str, OptimizedWeights] = {}

        # Default weights
        self.default_weights = {
            "semantic": 0.6,
            "keyword": 0.3,
            "metadata": 0.1
        }

        # Load existing data
        self._load_feedback()
        self._load_optimized_weights()

        logger.info(
            "feedback_optimizer_initialized",
            records=len(self._feedback_records),
            optimized_contexts=len(self._optimized_weights)
        )

    def record_feedback(
        self,
        incident_id: str,
        incident_type: str,
        severity: str,
        service: str,
        environment: str,
        query: str,
        weights_used: Dict[str, float],
        recommended_script_id: str,
        recommendation_rank: int
    ) -> str:
        """
        Record a new search feedback entry.

        Returns:
            feedback_id for later update
        """
        feedback_id = f"fb_{int(time.time())}_{incident_id}"

        record = FeedbackRecord(
            feedback_id=feedback_id,
            incident_id=incident_id,
            incident_type=incident_type,
            severity=severity,
            service=service,
            environment=environment,
            query=query,
            weights_used=weights_used,
            recommended_script_id=recommended_script_id,
            recommendation_rank=recommendation_rank
        )

        self._feedback_records.append(record)
        self._save_feedback()

        logger.info(
            "feedback_recorded",
            feedback_id=feedback_id,
            incident_type=incident_type
        )

        return feedback_id

    def update_execution_result(
        self,
        feedback_id: str,
        success: bool,
        execution_time_seconds: float = 0.0,
        error_message: str = ""
    ):
        """
        Update feedback record with execution results.

        Triggers weight optimization if enough samples.
        """
        for record in self._feedback_records:
            if record.feedback_id == feedback_id:
                record.executed = True
                record.success = success
                record.execution_time_seconds = execution_time_seconds
                record.error_message = error_message
                record.executed_at = datetime.now().isoformat()
                break

        self._save_feedback()

        # Check if we should optimize
        self._maybe_optimize()

        logger.info(
            "execution_result_recorded",
            feedback_id=feedback_id,
            success=success
        )

    def get_optimal_weights(
        self,
        incident_type: str,
        severity: str = "medium",
        service: str = ""
    ) -> Dict[str, float]:
        """
        Get optimal weights for the given context.

        Falls back to defaults if not enough data.
        """
        # Try exact match first
        context_key = self._get_context_key(incident_type, severity, service)
        if context_key in self._optimized_weights:
            weights = self._optimized_weights[context_key]
            logger.info(
                "using_optimized_weights",
                context=context_key,
                confidence=weights.confidence
            )
            return weights.to_dict()

        # Try incident_type only
        type_key = self._get_context_key(incident_type, "", "")
        if type_key in self._optimized_weights:
            weights = self._optimized_weights[type_key]
            return weights.to_dict()

        # Return defaults with severity-based adjustment
        weights = self.default_weights.copy()
        if severity.lower() in ["high", "critical"]:
            # For critical incidents, boost metadata matching (more precise)
            weights["metadata"] += 0.1
            weights["semantic"] -= 0.1

        return weights

    def _maybe_optimize(self):
        """Check if we have enough data to optimize and do so"""
        # Group feedback by incident type
        by_type: Dict[str, List[FeedbackRecord]] = {}
        for record in self._feedback_records:
            if record.executed and record.success:
                key = record.incident_type
                if key not in by_type:
                    by_type[key] = []
                by_type[key].append(record)

        # Optimize for each type with enough samples
        for incident_type, records in by_type.items():
            if len(records) >= self.min_samples:
                self._optimize_for_type(incident_type, records)

    def _optimize_for_type(
        self,
        incident_type: str,
        successful_records: List[FeedbackRecord]
    ):
        """
        Optimize weights for a specific incident type.

        Uses weighted averaging of weights that led to successful executions,
        with ranking position as the weight (lower rank = higher weight).
        """
        # Collect weight samples weighted by recommendation rank
        semantic_samples = []
        keyword_samples = []
        metadata_samples = []
        sample_weights = []

        for record in successful_records:
            # Higher weight for better ranks (rank 1 = best)
            rank_weight = 1.0 / (record.recommendation_rank + 1)

            semantic_samples.append(record.weights_used.get("semantic", 0.6))
            keyword_samples.append(record.weights_used.get("keyword", 0.3))
            metadata_samples.append(record.weights_used.get("metadata", 0.1))
            sample_weights.append(rank_weight)

        # Weighted average
        total_weight = sum(sample_weights)
        optimal_semantic = sum(s * w for s, w in zip(semantic_samples, sample_weights)) / total_weight
        optimal_keyword = sum(k * w for k, w in zip(keyword_samples, sample_weights)) / total_weight
        optimal_metadata = sum(m * w for m, w in zip(metadata_samples, sample_weights)) / total_weight

        # Normalize to sum to 1
        total = optimal_semantic + optimal_keyword + optimal_metadata
        optimal_semantic /= total
        optimal_keyword /= total
        optimal_metadata /= total

        # Calculate confidence based on sample count and variance
        variance = np.var(semantic_samples) + np.var(keyword_samples) + np.var(metadata_samples)
        confidence = min(1.0, len(successful_records) / 50) * (1 - min(variance, 1.0))

        # Store optimized weights
        context_key = self._get_context_key(incident_type, "", "")
        self._optimized_weights[context_key] = OptimizedWeights(
            incident_type=incident_type,
            semantic=round(optimal_semantic, 3),
            keyword=round(optimal_keyword, 3),
            metadata=round(optimal_metadata, 3),
            confidence=round(confidence, 3),
            sample_count=len(successful_records)
        )

        self._save_optimized_weights()

        logger.info(
            "weights_optimized",
            incident_type=incident_type,
            semantic=optimal_semantic,
            keyword=optimal_keyword,
            metadata=optimal_metadata,
            confidence=confidence,
            samples=len(successful_records)
        )

    def _get_context_key(
        self,
        incident_type: str,
        severity: str,
        service: str
    ) -> str:
        """Generate context key for weight lookup"""
        parts = [incident_type.lower()]
        if severity:
            parts.append(severity.lower())
        if service:
            parts.append(service.lower())
        return "_".join(parts)

    def _save_feedback(self):
        """Save feedback records to disk"""
        file_path = self.data_dir / "feedback_records.json"
        records = [r.to_dict() for r in self._feedback_records]
        with open(file_path, 'w') as f:
            json.dump(records, f, indent=2)

    def _load_feedback(self):
        """Load feedback records from disk"""
        file_path = self.data_dir / "feedback_records.json"
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    records = json.load(f)
                self._feedback_records = [
                    FeedbackRecord(**r) for r in records
                ]
            except Exception as e:
                logger.error("feedback_load_failed", error=str(e))

    def _save_optimized_weights(self):
        """Save optimized weights to disk"""
        file_path = self.data_dir / "optimized_weights.json"
        weights = {k: asdict(v) for k, v in self._optimized_weights.items()}
        with open(file_path, 'w') as f:
            json.dump(weights, f, indent=2)

    def _load_optimized_weights(self):
        """Load optimized weights from disk"""
        file_path = self.data_dir / "optimized_weights.json"
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    weights = json.load(f)
                self._optimized_weights = {
                    k: OptimizedWeights(**v) for k, v in weights.items()
                }
            except Exception as e:
                logger.error("weights_load_failed", error=str(e))

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        total = len(self._feedback_records)
        executed = sum(1 for r in self._feedback_records if r.executed)
        successful = sum(1 for r in self._feedback_records if r.success)

        return {
            "total_records": total,
            "executed": executed,
            "successful": successful,
            "success_rate": successful / executed if executed > 0 else 0,
            "optimized_contexts": len(self._optimized_weights),
            "weights_by_type": {
                k: v.to_dict() for k, v in self._optimized_weights.items()
            }
        }

    def get_script_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics per script"""
        stats: Dict[str, Dict[str, Any]] = {}

        for record in self._feedback_records:
            script_id = record.recommended_script_id
            if script_id not in stats:
                stats[script_id] = {
                    "recommended": 0,
                    "executed": 0,
                    "successful": 0,
                    "avg_execution_time": 0,
                    "times": []
                }

            stats[script_id]["recommended"] += 1
            if record.executed:
                stats[script_id]["executed"] += 1
                stats[script_id]["times"].append(record.execution_time_seconds)
                if record.success:
                    stats[script_id]["successful"] += 1

        # Calculate averages
        for script_id, s in stats.items():
            if s["times"]:
                s["avg_execution_time"] = np.mean(s["times"])
            del s["times"]
            s["success_rate"] = s["successful"] / s["executed"] if s["executed"] > 0 else 0

        return stats


# Global instance
feedback_optimizer = FeedbackOptimizer()
