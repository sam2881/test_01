"""Simple API server without database dependencies"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()
load_dotenv(".env.local")

app = FastAPI(title="AI Agent Platform - Simple API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    issue_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    context: Dict[str, Any]
    rag_results: Optional[Dict[str, Any]] = None


@app.get("/")
async def root():
    return {"status": "ok", "service": "AI Agent Platform API"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/chat/")
async def chat(request: ChatRequest):
    """Simple chat endpoint for testing"""
    # For now, return a mock response
    response_text = f"I received your message: '{request.message}'"

    if request.issue_id:
        response_text += f"\nAnalyzing issue: {request.issue_id}"

    return ChatResponse(
        response=response_text,
        context={
            "vector_db_count": 0,
            "graph_db_count": 0
        },
        rag_results={
            "vector_results": [],
            "graph_results": []
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
