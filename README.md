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

## Architecture

### Overall System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT APPLICATION                                  │
│                                                                              │
│  Uploads construction report document (PDF/Image)                           │
└──────────────────────────────────────────────────────────────┬──────────────┘
                                   │
                                   │ POST /validate
                                   │ (with document file)
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BYB AI API (FastAPI)                                │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 1. OCR SERVICE                                                        │  │
│  │    - Extracts text from document                                      │  │
│  │    - Uses Google Cloud Vision API                                     │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  │ Raw text                                 │
│                                  ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 2. NER SERVICE                                                        │  │
│  │    - Extracts structured entities                                     │  │
│  │    - Responsible engineer, date, progress %                           │  │
│  │    - Uses LangExtract + Gemini                                        │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  │ Structured data                          │
│                                  ▼                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 3. VALIDATION SERVICE                                                 │  │
│  │    - Validates extracted entities                                     │  │
│  │    - Checks all required fields present                               │  │
│  │    - Validates progress % in valid range                              │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  │                                           │
│                                  ▼                                           │
│                          Is validation successful?                           │
│                                  │                                           │
│                   ┌──────────────┴──────────────┐                           │
│                   │                              │                           │
│                   ▼ NO                           ▼ YES                       │
│         Return validation result      ┌─────────────────────┐               │
│                                       │  4a. UPLOAD SERVICE  │               │
│                                       │  - Upload to Filecoin│               │
│                                       └──────────┬──────────┘               │
│                                                  │                           │
│                                                  ▼                           │
│                                       ┌─────────────────────┐               │
│                                       │ 4b. BLOCKCHAIN      │               │
│                                       │     SERVICE         │               │
│                                       │ - Confirm milestone │               │
│                                       │ - Act as oracle     │               │
│                                       └──────────┬──────────┘               │
└───────────────────────────────────────────────────┼──────────────────────────┘
                                                    │
                                                    │ confirmMilestone(
                                                    │   buildingId,
                                                    │   milestoneNumber
                                                    │ )
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ETHEREUM BLOCKCHAIN                                       │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ EscrowManager Smart Contract                                          │  │
│  │ (https://github.com/Peixer/byb-sc/blob/main/contracts/                │  │
│  │  EscrowManager.sol)                                                   │  │
│  │                                                                        │  │
│  │  Function: confirmMilestone(uint256 buildingId, uint8 milestone)     │  │
│  │  - Records milestone confirmation on-chain                            │  │
│  │  - Enables fund release for this milestone                            │  │
│  │                                                                        │  │
│  │  Function: releaseMilestoneFunds(uint256 buildingId)                 │  │
│  │  - Releases USDC to developer for confirmed milestones                │  │
│  │  - Can be called by anyone after confirmation                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  State stored on blockchain:                                                 │
│  - Which milestones are confirmed                                            │
│  - How much USDC is escrowed                                                 │
│  - How much has been released                                                │
│  - Developer address                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Details

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Document   │────▶│  OCR Service │────▶│  NER Service │
└──────────────┘     └──────────────┘     └──────────────┘
                                                   │
                                                   │ Extraction Result
                                                   ▼
                                          ┌──────────────┐
                                          │  Validation  │
                                          │   Service    │
                                          └──────┬───────┘
                                                 │
                                                 │ is_valid = true
                                                 │
                          ┌──────────────────────┴──────────────────────┐
                          │                                             │
                          ▼                                             ▼
                 ┌──────────────┐                            ┌──────────────┐
                 │    Upload    │                            │  Blockchain  │
                 │   Service    │                            │   Service    │
                 │  (Filecoin)  │                            └──────┬───────┘
                 └──────────────┘                                   │
                                                                    │ Web3.py
                                                                    │
                                                                    ▼
                                                          ┌──────────────────┐
                                                          │  Ethereum Node   │
                                                          │  (via RPC)       │
                                                          └────────┬─────────┘
                                                                   │
                                                                   │ Transaction
                                                                   │
                                                                   ▼
                                                          ┌──────────────────┐
                                                          │ EscrowManager.sol│
                                                          │  confirmMilestone│
                                                          └──────────────────┘
```

### Trust Model

```
       TRADITIONAL ESCROW                    BLOCKCHAIN ORACLE ESCROW
            (Manual)                              (Automated)

    ┌───────────────────┐                 ┌───────────────────┐
    │   Construction    │                 │   Construction    │
    │    Manager        │                 │    Manager        │
    └─────────┬─────────┘                 └─────────┬─────────┘
              │                                     │
              │ Submits report                      │ Uploads document
              ▼                                     ▼
    ┌───────────────────┐                 ┌───────────────────┐
    │   Manual Review   │                 │   AI Validation   │
    │   (Days/Weeks)    │                 │   (Seconds)       │
    └─────────┬─────────┘                 └─────────┬─────────┘
              │                                     │
              │ Approves                            │ Auto-confirms
              ▼                                     ▼
    ┌───────────────────┐                 ┌───────────────────┐
    │   Bank/Escrow     │                 │  Smart Contract   │
    │   Agent           │                 │  (Immutable)      │
    └─────────┬─────────┘                 └─────────┬─────────┘
              │                                     │
              │ Releases funds                      │ Auto-releases
              ▼                                     ▼
    ┌───────────────────┐                 ┌───────────────────┐
    │    Developer      │                 │    Developer      │
    └───────────────────┘                 └───────────────────┘

    ⏱️  SLOW                               ⏱️  FAST
    💰 HIGH FEES                           💰 LOW FEES
    🤝 TRUST REQUIRED                      🔒 TRUSTLESS
    📝 OPAQUE                              🔍 TRANSPARENT
```

For more detailed architecture documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).