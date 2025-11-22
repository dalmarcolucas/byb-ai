"""
Main FastAPI application for BYB AI.
"""

from typing import Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Security, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import base64
import secrets

from app.services.ocr_service import OCRService
from app.services.ner_service import NERService
from app.services.validation_service import ValidationService
from app.models import ExtractionResult
from app.config import settings

app = FastAPI(
    title="BYB AI API",
    description="REST API for BYB AI application",
    version="1.0.0"
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(x_api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from request header.
    
    Args:
        x_api_key: API key from X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not settings.api_key:
        raise HTTPException(
            status_code=500,
            detail="API key not configured on server. Please contact administrator."
        )
    
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required. Please provide X-API-Key header."
        )
    
    if not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return x_api_key


ocr_service = OCRService()
ner_service = NERService()
validation_service = ValidationService()
validation_service = ValidationService()
validation_service = ValidationService()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    message: str


class RootResponse(BaseModel):
    """Root endpoint response model."""
    message: str
    health_check: str


class OCRResponse(BaseModel):
    """OCR extraction response model."""
    text: str


class ValidationResponse(BaseModel):
    """Validation response model."""
    is_valid: bool
    extraction: ExtractionResult


class BytesRequest(BaseModel):
    """Request model for bytes-based document processing."""
    document_bytes: str  # base64 encoded bytes
    filename: Optional[str] = "document"


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


@app.post("/ocr/extract", response_model=OCRResponse, tags=["OCR"])
async def extract_text_from_document(
    file: UploadFile = File(..., description="PDF or image file to extract text from"),
    api_key: str = Security(verify_api_key)
) -> OCRResponse:
    """
    Extract text from an uploaded document (PDF or image).
    
    Supported formats:
    - PDF documents
    - Images (JPEG, PNG, TIFF, etc.)
    
    Args:
        file: Uploaded file containing the document
        
    Returns:
        OCRResponse with extracted text and metadata (num_pages, confidence)
        
    Raises:
        HTTPException: If file processing fails
    """
    try:
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        result = await ocr_service.extract_text(
            document=content,
            filename=file.filename or "unknown"
        )
        
        return OCRResponse(text=result)
        
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@app.post("/ner/extract", response_model=ExtractionResult, tags=["NER"])
async def extract_entities_from_document(
    file: UploadFile = File(..., description="PDF or image file to extract entities from"),
    api_key: str = Security(verify_api_key)
) -> ExtractionResult:
    """
    Extract entities from an uploaded document (PDF or image).
    
    This endpoint processes the document in two steps:
    1. OCR: Extracts text from the document using Google Cloud Vision API
    2. NER: Extracts structured entities (responsible engineer, date, construction progress) from the text
    
    Supported formats:
    - PDF documents
    - Images (JPEG, PNG, TIFF, etc.)
    
    Args:
        file: Uploaded file containing the document
        
    Returns:
        NERResponse with extracted entities and metadata
        
    Raises:
        HTTPException: If file processing fails
    """
    try:
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        ocr_result = await ocr_service.extract_text(
            document=content,
            filename=file.filename or "unknown"
        )
        
        entities = await ner_service.extract_entities(text=ocr_result)
        
        return entities
        
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
async def validate_document(
    file: UploadFile = File(..., description="PDF or image file to validate"),
    api_key: str = Security(verify_api_key)
) -> ValidationResponse:
    """
    Validate an uploaded document (PDF or image).
    
    This endpoint processes the document in three steps:
    1. OCR: Extracts text from the document using Google Cloud Vision API
    2. NER: Extracts structured entities (responsible engineer, date, construction progress) from the text
    3. Validation: Validates the extracted entities
    
    Supported formats:
    - PDF documents
    - Images (JPEG, PNG, TIFF, etc.)
    
    Args:
        file: Uploaded file containing the document
        
    Returns:
        ValidationResponse with validation result and extracted entities
        
    Raises:
        HTTPException: If file processing fails
    """
    try:
        content = await file.read()
        
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        ocr_result = await ocr_service.extract_text(
            document=content,
            filename=file.filename or "unknown"
        )
        
        entities = await ner_service.extract_entities(text=ocr_result)
        
        is_valid = validation_service.validate_extraction(entities)
        
        return ValidationResponse(
            is_valid=is_valid,
            extraction=entities
        )
        
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@app.post("/validate-bytes", response_model=ValidationResponse, tags=["Validation"])
async def validate_document_bytes(
    request: BytesRequest = Body(..., description="Base64-encoded document bytes and optional filename"),
    api_key: str = Security(verify_api_key)
) -> ValidationResponse:
    """
    Validate document bytes (PDF or image).
    
    This endpoint accepts raw document bytes encoded as base64 instead of file uploads.
    Useful when you already have the document bytes in memory.
    
    This endpoint processes the document in three steps:
    1. OCR: Extracts text from the document using Google Cloud Vision API
    2. NER: Extracts structured entities (responsible engineer, date, construction progress) from the text
    3. Validation: Validates the extracted entities
    
    Supported formats:
    - PDF documents
    - Images (JPEG, PNG, TIFF, etc.)
    
    Args:
        request: BytesRequest containing base64-encoded document bytes and optional filename
        
    Returns:
        ValidationResponse with validation result and extracted entities
        
    Raises:
        HTTPException: If document processing fails
    """
    try:
        content = base64.b64decode(request.document_bytes)
        
        if not content:
            raise HTTPException(status_code=400, detail="Document bytes are empty")
        
        ocr_result = await ocr_service.extract_text(
            document=content,
            filename=request.filename or "document"
        )
        
        entities = await ner_service.extract_entities(text=ocr_result)
        
        is_valid = validation_service.validate_extraction(entities)
        
        return ValidationResponse(
            is_valid=is_valid,
            extraction=entities
        )
        
    except base64.binascii.Error:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
