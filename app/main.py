"""
Main FastAPI application for BYB AI.
"""

from typing import Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel

from app.services.ocr_service import OCRService

app = FastAPI(
    title="BYB AI API",
    description="REST API for BYB AI application",
    version="1.0.0"
)

# Initialize OCR service
ocr_service = OCRService()


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
    metadata: Dict[str, Any]


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
        # Read file content
        content = await file.read()
        
        # Validate file is not empty
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Extract text using OCR service
        result = await ocr_service.extract_text(
            document=content,
            filename=file.filename or "unknown"
        )
        
        return OCRResponse(**result)
        
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
