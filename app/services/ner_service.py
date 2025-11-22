"""NER (Named Entity Recognition) service using LangExtract and Google Gemini."""
import os
import time
from typing import Dict, Any, List, Optional
from loguru import logger

from app.config import settings
from app.models import ExtractionResult

try:
    import langextract as lx
except ImportError:
    lx = None


class NERService:
    """Service for extracting entities from text using LangExtract and Google Gemini."""
    
    ENTITY_DEFINITIONS = [
        {
            "field_name": "responsible_engineer",
            "field_type": "string",
            "description": "Name of the responsible engineer",
            "required": True
        },
        {
            "field_name": "date",
            "field_type": "string",
            "description": "Date in DD/MM/YYYY format",
            "required": True
        },
        {
            "field_name": "construction_progress_percentage",
            "field_type": "float",
            "description": "Construction progress as a percentage (0-100)",
            "required": True
        }
    ]
    
    def __init__(self):
        """Initialize NER service."""
        if lx is None:
            raise RuntimeError("langextract package not installed. Please install it with: pip install langextract")
        
        if settings.langextract_api_key and not os.environ.get('LANGEXTRACT_API_KEY'):
            os.environ['LANGEXTRACT_API_KEY'] = settings.langextract_api_key
    
    def _build_extraction_prompt(
        self,
        entity_definitions: List[Dict[str, Any]],
        extraction_context: str
    ) -> str:
        """
        Build the extraction prompt for LangExtract.
        
        Args:
            entity_definitions: List of entity definitions
            extraction_context: Context for extraction
            
        Returns:
            Formatted prompt string
        """
        field_descriptions = []
        for entity_def in entity_definitions:
            field_name = entity_def["field_name"]
            description = entity_def["description"]
            required_status = "required" if entity_def.get("required", True) else "optional"
            field_type = entity_def["field_type"]
            field_descriptions.append(f"- {field_name} ({field_type}, {required_status}): {description}")
        
        fields_text = "\n".join(field_descriptions)
        
        prompt = f"""Extract structured information from a {extraction_context}.

Fields to extract:
{fields_text}

Important instructions:
- Extract ONLY the requested information
- Maintain Brazilian formats (dates DD/MM/YYYY or MM/YYYY, numeric values as decimal numbers)
- If an optional field is not present in the text, do not include it in the extraction
- If a required field is not present, do your best to find it
- Be precise and extract exactly what is in the document
- Use the exact text from the document, do not paraphrase"""
        
        return prompt
    
    def _create_extraction_examples(self) -> List[Any]:
        """
        Create example extractions for LangExtract.
        
        Returns:
            List of ExampleData objects
        """
        examples = [
            lx.data.ExampleData(
                text="Construction Report - Project Alpha\nEngineer: João Silva\nDate: 15/03/2024\nProgress: 75% complete",
                extractions=[
                    lx.data.Extraction(
                        extraction_class="responsible_engineer",
                        extraction_text="João Silva",
                        attributes={"description": "Name of the responsible engineer", "type": "string"}
                    ),
                    lx.data.Extraction(
                        extraction_class="date",
                        extraction_text="15/03/2024",
                        attributes={"description": "Date in DD/MM/YYYY format", "type": "string"}
                    ),
                    lx.data.Extraction(
                        extraction_class="construction_progress_percentage",
                        extraction_text="75",
                        attributes={"description": "Construction progress as a percentage (0-100)", "type": "float"}
                    ),
                ]
            )
        ]
        return examples
    
    async def extract_entities(
        self,
        text: str
    ) -> ExtractionResult:
        """
        Extract entities from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            ExtractionResult object with extracted entities
        """
        entity_definitions = self.ENTITY_DEFINITIONS
        extraction_context = "construction report"
        
        if not os.environ.get('LANGEXTRACT_API_KEY') and not settings.langextract_api_key:
            raise RuntimeError(
                "LangExtract API key not configured. Please set LANGEXTRACT_API_KEY environment variable. "
                "Get your API key from https://aistudio.google.com/app/apikey"
            )
        
        start_time = time.time()
        
        try:
            prompt = self._build_extraction_prompt(entity_definitions, extraction_context)
            logger.debug(f"Extraction prompt built for context: {extraction_context}")
            
            examples = self._create_extraction_examples()
            
            logger.info(f"Extracting entities using {settings.ner_model_name} via LangExtract...")
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt,
                examples=examples,
                model_id=settings.ner_model_name,
                use_schema_constraints=True,
            )
            
            entities = {}
            fields_extracted = 0
            
            if result and hasattr(result, 'extractions'):
                field_map = {ed["field_name"]: ed for ed in entity_definitions}
                
                for extraction in result.extractions:
                    field_name = extraction.extraction_class
                    if field_name in field_map:
                        value = extraction.extraction_text
                        
                        field_type = field_map[field_name]["field_type"]
                        try:
                            if field_type == "float":
                                value = float(value.replace(",", ".")) if value else None
                            elif field_type == "integer":
                                value = int(value) if value else None
                            elif field_type == "boolean":
                                value = value.lower() in ["true", "sim", "yes", "1"] if value else None
                        except (ValueError, AttributeError):
                            pass
                        
                        entities[field_name] = value
                        if value is not None:
                            fields_extracted += 1
            
            for entity_def in entity_definitions:
                field_name = entity_def["field_name"]
                if field_name not in entities:
                    if not entity_def.get("required", True):
                        entities[field_name] = None
            
            processing_time = time.time() - start_time
            
            logger.info(f"Extracted {fields_extracted}/{len(entity_definitions)} fields in {processing_time:.2f}s")
            
            return ExtractionResult(
                responsible_engineer=entities.get("responsible_engineer") or "",
                date=entities.get("date") or "",
                construction_progress_percentage=entities.get("construction_progress_percentage") or 0.0
            )
        
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error extracting entities: {e}", exc_info=True)
            
            return ExtractionResult(
                responsible_engineer="",
                date="",
                construction_progress_percentage=0.0
            )
