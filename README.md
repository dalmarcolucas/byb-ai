# byb-ai

A Python REST API built with FastAPI for the BYB AI application.

## Features

- FastAPI web framework
- OCR service using Google Cloud Vision API
- NER (Named Entity Recognition) service using LangExtract and Google Gemini
- Validation service for extracted entities
- Health check endpoints
- Auto-generated OpenAPI/Swagger documentation
- Pydantic models for request/response validation

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Google Cloud credentials for Vision API

## Installation

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
uv pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Google Cloud credentials and bucket name
```

## Running the API

Start the API server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For development with auto-reload:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### Health Checks

- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check endpoint

### Documentation

- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - ReDoc documentation
- `GET /openapi.json` - OpenAPI schema

## Example Usage

Check API health:
```bash
curl http://localhost:8000/health
```

Response:
```json
{
    "status": "ok",
    "message": "BYB AI API is running"
}
```