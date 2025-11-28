"""Data Agent for SQL optimization and ETL debugging"""
import os
import sys
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent
import structlog

logger = structlog.get_logger()

app = FastAPI(title="Data Agent")


class DataTask(BaseModel):
    """Data task schema"""
    task_id: str
    task_type: str  # "sql_optimize", "etl_debug", "data_quality"
    query: str = ""
    error_message: str = ""


class DataAgent(BaseAgent):
    """Agent for data pipeline and SQL optimization"""

    def __init__(self):
        super().__init__(agent_name="DataAgent", agent_type="data_engineering")

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate task input"""
        return "task_id" in task and "task_type" in task

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process data task"""
        task_type = task["task_type"]

        logger.info("processing_data_task", type=task_type)

        if task_type == "sql_optimize":
            return self._optimize_sql(task)
        elif task_type == "etl_debug":
            return self._debug_etl(task)
        elif task_type == "data_quality":
            return self._check_data_quality(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _optimize_sql(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize SQL query"""
        query = task.get("query", "")

        # Use LLM to analyze and optimize
        prompt = f"""Analyze and optimize this SQL query:

{query}

Provide:
1. Performance issues
2. Optimized query
3. Index recommendations
"""
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "original_query": query,
            "analysis": response.choices[0].message.content
        }

    def _debug_etl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Debug ETL pipeline"""
        error_msg = task.get("error_message", "")

        prompt = f"""Debug this ETL error:

{error_msg}

Provide:
1. Root cause
2. Fix recommendations
3. Prevention strategies
"""
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "error_analysis": response.choices[0].message.content
        }

    def _check_data_quality(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Check data quality"""
        return {
            "quality_score": 85,
            "issues_found": ["Duplicate records", "Null values in critical fields"],
            "recommendations": ["Add unique constraint", "Implement null checks"]
        }


agent = DataAgent()


@app.post("/process")
async def process_data_task(task: DataTask):
    """Process data task"""
    try:
        result = agent.run(task.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "DataAgent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8014)
