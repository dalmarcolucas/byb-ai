import base64
import httpx
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class UploadService:
    
    def __init__(self):
        # Set timeout to 5 minutes for large file uploads
        self.timeout = settings.upload_service_timeout or 300.0
        logger.info(f"UploadService initialized with timeout: {self.timeout}s")
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: Optional[str] = None
    ) -> dict:
        logger.info(f"Starting file upload. Filename: {filename}, Size: {len(file_content)} bytes")
        
        if not settings.upload_service_url:
            logger.error("Upload service URL not configured")
            raise RuntimeError(
                "Upload service URL not configured. "
                "Please set UPLOAD_SERVICE_URL environment variable."
            )
        
        logger.debug("Encoding file content to base64")
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        logger.debug(f"Base64 encoded size: {len(file_base64)} characters")
        
        payload = {
            "file": file_base64
        }
        
        if filename:
            payload["filename"] = filename
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if settings.upload_service_api_key:
            headers["X-API-Key"] = settings.upload_service_api_key
            logger.debug("API key included in request headers")
        else:
            logger.warning("No API key configured for upload service")
        
        try:
            logger.info(f"Sending POST request to {settings.upload_service_url}")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    settings.upload_service_url,
                    json=payload,
                    headers=headers
                )
                
                logger.debug(f"Received response with status code: {response.status_code}")
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"File uploaded successfully. Response: {result}")
                return result
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Upload failed with HTTP status {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            logger.error(f"Request URL: {settings.upload_service_url}")
            logger.error(f"Filename: {filename}")
            raise RuntimeError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Upload request failed - {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Request URL: {settings.upload_service_url}")
            logger.error(f"Filename: {filename}")
            logger.error(f"Error type: {type(e).__module__}.{type(e).__name__}")
            logger.error(f"Full error details: {repr(e)}", exc_info=True)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during upload - {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Request URL: {settings.upload_service_url}")
            logger.error(f"Filename: {filename}")
            logger.error(f"Full traceback:", exc_info=True)
            raise RuntimeError(error_msg)
