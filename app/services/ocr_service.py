"""OCR (Optical Character Recognition) service using Google Cloud Vision API."""
import io
import os
import json
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path

from google.cloud import vision
from google.cloud import storage
from PIL import Image
from loguru import logger

from app.config import settings


class OCRService:
    """Service for extracting text from documents using Google Cloud Vision API."""
    
    def __init__(self):
        """Initialize OCR service with Google Cloud Vision and Storage clients."""
        self.vision_client = None
        self.storage_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize the Google Cloud Vision and Storage clients."""
        try:
            # Set credentials from config if provided
            if settings.google_application_credentials:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.google_application_credentials
            
            self.vision_client = vision.ImageAnnotatorClient()
            self.storage_client = storage.Client()
            logger.info("Google Cloud Vision and Storage clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud clients: {e}")
            self.vision_client = None
            self.storage_client = None
    
    def _upload_to_gcs(self, document: bytes, filename: str) -> str:
        """
        Upload document to Google Cloud Storage.
        
        Args:
            document: Document bytes
            filename: Original filename
            
        Returns:
            GCS URI (gs://bucket-name/path)
        """
        if not self.storage_client or not settings.gcs_bucket_name:
            raise RuntimeError("Google Cloud Storage not configured. Please check GCS_BUCKET_NAME setting.")
        
        try:
            bucket = self.storage_client.bucket(settings.gcs_bucket_name)
            unique_id = str(uuid.uuid4())
            blob_name = f"ocr_input/{unique_id}/{filename}"
            blob = bucket.blob(blob_name)
            
            blob.upload_from_string(document)
            gcs_uri = f"gs://{settings.gcs_bucket_name}/{blob_name}"
            logger.info(f"Uploaded document to {gcs_uri}")
            
            return gcs_uri
        except Exception as e:
            logger.error(f"Error uploading to GCS: {e}")
            raise RuntimeError(f"Failed to upload to GCS: {str(e)}")
    
    def _download_from_gcs(self, gcs_uri: str) -> str:
        """
        Download JSON result from Google Cloud Storage.
        
        Args:
            gcs_uri: GCS URI to download from
            
        Returns:
            JSON content as string
        """
        if not self.storage_client:
            raise RuntimeError("Google Cloud Storage client not initialized.")
        
        try:
            # Parse GCS URI: gs://bucket-name/path
            uri_parts = gcs_uri.replace("gs://", "").split("/", 1)
            bucket_name = uri_parts[0]
            blob_name = uri_parts[1]
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            content = blob.download_as_text()
            logger.info(f"Downloaded result from {gcs_uri}")
            
            return content
        except Exception as e:
            logger.error(f"Error downloading from GCS: {e}")
            raise RuntimeError(f"Failed to download from GCS: {str(e)}")
    
    def _list_gcs_blobs(self, gcs_prefix: str) -> list:
        """
        List all blobs with the given prefix in Google Cloud Storage.
        
        Args:
            gcs_prefix: GCS URI prefix (gs://bucket-name/path/)
            
        Returns:
            List of blob names
        """
        if not self.storage_client:
            raise RuntimeError("Google Cloud Storage client not initialized.")
        
        try:
            # Parse GCS URI: gs://bucket-name/path/
            uri_parts = gcs_prefix.replace("gs://", "").split("/", 1)
            bucket_name = uri_parts[0]
            prefix = uri_parts[1] if len(uri_parts) > 1 else ""
            
            bucket = self.storage_client.bucket(bucket_name)
            blobs = list(bucket.list_blobs(prefix=prefix))
            
            blob_names = [blob.name for blob in blobs]
            logger.info(f"Found {len(blob_names)} blob(s) with prefix {prefix}")
            
            return blob_names
        except Exception as e:
            logger.error(f"Error listing blobs from GCS: {e}")
            raise RuntimeError(f"Failed to list blobs from GCS: {str(e)}")
    
    def _cleanup_gcs_files(self, *gcs_uris: str):
        """
        Clean up temporary files from Google Cloud Storage.
        
        Args:
            gcs_uris: GCS URIs to delete
        """
        if not self.storage_client:
            return
        
        for gcs_uri in gcs_uris:
            try:
                # Parse GCS URI
                uri_parts = gcs_uri.replace("gs://", "").split("/", 1)
                bucket_name = uri_parts[0]
                blob_name = uri_parts[1]
                
                bucket = self.storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                blob.delete()
                
                logger.debug(f"Deleted temporary file: {gcs_uri}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {gcs_uri}: {e}")
    
    def _extract_text_from_pdf_async(self, pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract text from PDF using Google Cloud Vision API's async batch annotation.
        
        Args:
            pdf_bytes: PDF file as bytes
            filename: Original filename
            
        Returns:
            Dictionary with extracted text and confidence
        """
        if not self.vision_client:
            raise RuntimeError("Google Cloud Vision client not initialized. Please check credentials.")
        
        input_gcs_uri = None
        output_gcs_prefix = None
        
        try:
            # Upload PDF to GCS
            input_gcs_uri = self._upload_to_gcs(pdf_bytes, filename)
            
            # Generate unique output prefix
            unique_id = str(uuid.uuid4())
            output_gcs_prefix = f"gs://{settings.gcs_bucket_name}/ocr_output/{unique_id}/"
            
            # Configure input and output
            input_config = vision.InputConfig(
                gcs_source=vision.GcsSource(uri=input_gcs_uri),
                mime_type='application/pdf'
            )
            
            output_config = vision.OutputConfig(
                gcs_destination=vision.GcsDestination(uri=output_gcs_prefix),
                batch_size=100  # Max pages per output file
            )
            
            # Configure the request
            feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
            request = vision.AsyncAnnotateFileRequest(
                features=[feature],
                input_config=input_config,
                output_config=output_config
            )
            
            # Execute async batch annotation
            logger.info("Starting async batch annotation for PDF")
            operation = self.vision_client.async_batch_annotate_files(requests=[request])
            
            # Wait for operation to complete
            logger.info("Waiting for operation to complete...")
            result = operation.result(timeout=420)
            
            # Get output file location from the first response
            if not result.responses:
                raise RuntimeError("No responses found in operation result")
            
            first_response = result.responses[0]
            output_uri = first_response.output_config.gcs_destination.uri
            logger.info(f"Operation completed, results at: {output_uri}")
            
            # List all output files from the prefix
            # The output is stored in output-1-to-X.json files where X depends on the number of pages
            blob_names = self._list_gcs_blobs(output_uri)
            
            # Filter to only JSON files
            output_files = [name for name in blob_names if name.endswith('.json')]
            output_files.sort()  # Ensure they're processed in order
            logger.info(f"Found {len(output_files)} output file(s): {output_files}")
            
            if not output_files:
                raise RuntimeError("No output files found in GCS")
            
            # Extract text and confidence from all output files
            all_text_parts = []
            all_confidences = []
            num_pages = 0
            
            # Process each output file
            for output_file in output_files:
                output_file_uri = f"gs://{settings.gcs_bucket_name}/{output_file}"
                logger.info(f"Processing output file: {output_file_uri}")
                
                json_content = self._download_from_gcs(output_file_uri)
                json_data = json.loads(json_content)
                
                # Parse responses from this file
                for response in json_data.get('responses', []):
                    num_pages += 1
                    full_text_annotation = response.get('fullTextAnnotation', {})
                    
                    # Extract text
                    text = full_text_annotation.get('text', '')
                    if text:
                        all_text_parts.append(text)
                    
                    # Calculate confidence from pages
                    pages = full_text_annotation.get('pages', [])
                    for page in pages:
                        blocks = page.get('blocks', [])
                        for block in blocks:
                            if 'confidence' in block:
                                all_confidences.append(block['confidence'])
            
            # Combine results
            combined_text = "\n\n".join(text for text in all_text_parts if text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
            
            logger.info(f"Extracted text from {num_pages} page(s) with confidence {avg_confidence:.4f}")
            
            return combined_text
        
        except Exception as e:
            logger.error(f"Error in async PDF processing: {e}")
            raise RuntimeError(f"Failed to process PDF: {str(e)}")
        
        finally:
            # Clean up temporary files
            if input_gcs_uri:
                self._cleanup_gcs_files(input_gcs_uri)
            if output_gcs_prefix:
                # Try to clean up all output files (best effort)
                try:
                    blob_names = self._list_gcs_blobs(output_gcs_prefix)
                    output_file_uris = [f"gs://{settings.gcs_bucket_name}/{name}" for name in blob_names]
                    if output_file_uris:
                        self._cleanup_gcs_files(*output_file_uris)
                except Exception as e:
                    logger.warning(f"Failed to cleanup output files: {e}")
    
    def _extract_text_from_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from a single image using Google Cloud Vision API.
        
        Args:
            image_bytes: Image file as bytes
            
        Returns:
            Dictionary with extracted text and confidence
        """
        if not self.vision_client:
            raise RuntimeError("Google Cloud Vision client not initialized. Please check credentials.")
        
        try:
            image = vision.Image(content=image_bytes)
            response = self.vision_client.document_text_detection(image=image)
            
            if response.error.message:
                raise Exception(f"Google Cloud Vision API error: {response.error.message}")
            
            # Extract full text
            text = response.full_text_annotation.text if response.full_text_annotation else ""
            
            # Calculate average confidence from pages
            confidence = 0.0
            if response.full_text_annotation and response.full_text_annotation.pages:
                total_confidence = 0.0
                block_count = 0
                
                for page in response.full_text_annotation.pages:
                    for block in page.blocks:
                        if hasattr(block, 'confidence'):
                            total_confidence += block.confidence
                            block_count += 1
                
                if block_count > 0:
                    confidence = total_confidence / block_count
            
            return text
        
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            raise RuntimeError(f"Failed to extract text: {str(e)}")
    
    async def extract_text(
        self,
        document: bytes,
        filename: str = ""
    ) -> Dict[str, Any]:
        """
        Extract text from a document (PDF or image) using Google Cloud Vision API.
        
        Args:
            document: Raw document bytes (PDF or image)
            filename: Original filename to determine file type
            
        Returns:
            Extracted text as string
        """
        if not self.vision_client:
            raise RuntimeError("Google Cloud Vision client not initialized. Please check credentials.")
        
        try:
            # Determine file type from filename or content
            file_ext = Path(filename).suffix.lower() if filename else ""
            is_pdf = file_ext == ".pdf" or document[:4] == b'%PDF'
            
            if is_pdf:
                logger.info("Processing PDF document with async batch annotation")
                return self._extract_text_from_pdf_async(document, filename)
            else:
                logger.info("Processing image document")
                return self._extract_text_from_image(document)
        
        except Exception as e:
            logger.error(f"Error in extract_text: {e}")
            raise
