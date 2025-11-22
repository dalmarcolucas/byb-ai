"""Extraction result models."""
from pydantic import BaseModel


class ExtractionResult(BaseModel):
    """Result of entity extraction."""
    responsible_engineer: str
    date: str
    construction_progress_percentage: float
