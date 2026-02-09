"""
Step 1: Query Preprocessor
Normalize and clean user query
"""

from typing import Any, Dict
import logging

from app.pipelines.base import PipelineStep
from app.utils.arabic import ArabicNormalizer

logger = logging.getLogger(__name__)


class PreprocessorStep(PipelineStep):
    """
    Step 1: Preprocess user query.
    
    Input: str (raw query)
    Output: str (normalized query)
    
    Operations:
    - Arabic text normalization
    - Remove excessive whitespace
    - Basic cleaning
    """
    
    def __init__(self):
        super().__init__("Query Preprocessor")
    
    def process(self, data: str, context: Dict[str, Any]) -> str:
        """
        Preprocess the query.
        
        Args:
            data: Raw user query
            context: Pipeline context
            
        Returns:
            Normalized query
        """
        original = data
        
        # Normalize Arabic text for better matching
        normalized = ArabicNormalizer.normalize(
            data,
            remove_diacritics=True,
            remove_tatweel=True,
            normalize_alef=True,
            normalize_teh=False,  # Keep ة for legal accuracy
            normalize_yeh=False,  # Keep ى for legal accuracy
            normalize_whitespace=True,
        )
        
        # Store original in context
        context["original_query"] = original
        context["normalized_query"] = normalized
        
        self.logger.info(f"Preprocessed query: '{original[:50]}...' -> '{normalized[:50]}...'")
        
        return normalized
    
    def validate_input(self, data: Any) -> bool:
        """Validate input is a non-empty string"""
        if not isinstance(data, str):
            self.logger.error("Query must be a string")
            return False
        if not data.strip():
            self.logger.error("Query cannot be empty")
            return False
        return True
