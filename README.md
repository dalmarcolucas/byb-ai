# byb-ai

A Python REST API built with FastAPI for the BYB AI application.

## Features

- FastAPI web framework
- Health check endpoints
- Auto-generated OpenAPI/Swagger documentation
- Pydantic models for request/response validation

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
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