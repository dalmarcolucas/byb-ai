"""Application configuration settings."""
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Cloud Configuration
    google_application_credentials: Optional[str] = None
    gcs_bucket_name: Optional[str] = None
    
    # API Configuration
    api_title: str = "BYB AI API"
    api_description: str = "REST API for BYB AI application"
    api_version: str = "1.0.0"
    
    langextract_api_key: Optional[str] = None
    ner_model_name: str = "gemini-flash-lite-latest"
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


# Global settings instance
settings = Settings()
