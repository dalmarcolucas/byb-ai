import base64
import httpx
from typing import Optional
from app.config import settings


class UploadService:
    
    def __init__(self):
        self.timeout = 30.0
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: Optional[str] = None
    ) -> dict:
        if not settings.upload_service_url:
            raise RuntimeError(
                "Upload service URL not configured. "
                "Please set UPLOAD_SERVICE_URL environment variable."
            )
        
        file_base64 = base64.b64encode(file_content).decode('utf-8')
        
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
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    settings.upload_service_url,
                    json=payload,
                    headers=headers
                )
                
                response.raise_for_status()
                
                return response.json()
                
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Upload failed with status {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise RuntimeError(f"Upload request failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during upload: {str(e)}")
