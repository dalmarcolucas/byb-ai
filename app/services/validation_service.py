from app.models.extraction import ExtractionResult


class ValidationService:

    def validate_extraction(self, 
                            extraction_result: ExtractionResult
    ) -> bool:
        """
        Validate the extracted entities.

        Args:
            extraction_result: The result of entity extraction.

        Returns:
            True if all required fields are valid, False otherwise.
        """
        if not extraction_result.responsible_engineer:
            return False
        
        if not extraction_result.date:
            return False
        
        if not (30.0 <= extraction_result.construction_progress_percentage <= 100.0):
            return False
        
        return True
