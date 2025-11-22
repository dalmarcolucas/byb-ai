"""
Main FastAPI application for BYB AI.
"""

from typing import Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel

from app.services.ocr_service import OCRService
from app.services.ner_service import NERService
from app.services.validation_service import ValidationService
from app.models import ExtractionResult

app = FastAPI(
    title="BYB AI API",
    description="REST API for BYB AI application",
    version="1.0.0"
)

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
    file: UploadFile = File(..., description="PDF or image file to extract text from")
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
    file: UploadFile = File(..., description="PDF or image file to extract entities from")
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
    file: UploadFile = File(..., description="PDF or image file to validate")
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
