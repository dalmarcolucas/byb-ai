"""
Main FastAPI application for BYB AI.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="BYB AI API",
    description="REST API for BYB AI application",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    message: str


class RootResponse(BaseModel):
    """Root endpoint response model."""
    message: str
    health_check: str


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse containing status and message indicating the API is healthy.
    """
    return HealthResponse(
        status="ok",
        message="BYB AI API is running"
    )


@app.get("/", response_model=RootResponse, tags=["Info"])
async def root() -> RootResponse:
    """
    Root endpoint.

    Returns:
        RootResponse with welcome message and health check path.
    """
    return RootResponse(
        message="Welcome to BYB AI API",
        health_check="/health"
    )
