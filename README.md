# byb-ai

A Python REST API built with FastAPI for the BYB AI application with blockchain integration for construction milestone verification.

## Features

- FastAPI web framework
- OCR service using Google Cloud Vision API
- NER (Named Entity Recognition) service using LangExtract and Google Gemini
- Validation service for extracted entities
- **Blockchain Oracle**: Confirms construction milestones on-chain via EscrowManager smart contract
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

### Local Development

Start the API server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

For development with auto-reload:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

Build the Docker image:
```bash
docker build -t byb-ai .
```

Run with Docker Compose:
```bash
docker compose up
```


## API Endpoints

### Health Checks

- `GET /health` - Health check endpoint

### Document Processing

- `POST /validate` - Validate a document (PDF or image) by extracting and validating entities

### Documentation

- `GET /docs` - Interactive Swagger UI documentation
- `GET /redoc` - ReDoc documentation
- `GET /openapi.json` - OpenAPI schema

## Example Usage

### Health Check

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

### Validate Document

Validate a document and extract entities:
```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/document.pdf"
```

Response:
```json
{
    "is_valid": true,
    "extraction": {
        "responsible_engineer": "João Silva",
        "date": "15/03/2024",
        "construction_progress_percentage": 75.0
    }
}
```

The validation service checks:
- Responsible engineer field is not empty
- Date field is not empty
- Construction progress percentage is between 30.0 and 100.0

## Blockchain Integration

This API acts as an oracle for the [EscrowManager smart contract](https://github.com/Peixer/byb-sc/blob/main/contracts/EscrowManager.sol). When a document validation succeeds, the API automatically confirms construction milestones on-chain, enabling trustless escrow release.

### Quick Setup

1. Enable blockchain integration in `.env`:
```bash
BLOCKCHAIN_ENABLED=true
BLOCKCHAIN_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
ESCROW_CONTRACT_ADDRESS=0x1234...
ORACLE_PRIVATE_KEY=0xabcd...
BLOCKCHAIN_CHAIN_ID=11155111
```

2. Install blockchain dependencies:
```bash
uv pip install web3 eth-account
```

3. Validate a document - milestone confirmation happens automatically:
```bash
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: multipart/form-data" \
  -H "X-API-Key: your-api-key" \
  -F "file=@/path/to/document.pdf"
```

Response includes blockchain transaction:
```json
{
    "is_valid": true,
    "extraction": { ... },
    "blockchain_response": {
        "transaction_hash": "0xabcd...",
        "block_number": 12345678,
        "gas_used": 145890,
        "status": "success"
    }
}
```