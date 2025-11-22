"""
Main FastAPI application for BYB AI.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

app = FastAPI(
    title="BYB AI API",
    description="REST API for BYB AI application",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    message: str


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Dict containing status and message indicating the API is healthy.
    """
    return {
        "status": "ok",
        "message": "BYB AI API is running"
    }


@app.get("/", tags=["Health"])
async def root() -> Dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        Dict with welcome message.
    """
    return {
        "message": "Welcome to BYB AI API",
        "health_check": "/health"
    }
