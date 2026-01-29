"""
Step 2: Text Extractor
Extract Arabic text from PDF pages
"""

from typing import Any, Dict, List
import fitz  # PyMuPDF
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import PageContent

logger = logging.getLogger(__name__)


class TextExtractorStep(PipelineStep):
    """
    Step 2: Extract text from PDF pages.
    
    Input: fitz.Document
    Output: List[PageContent] with page number and text
    """
    
    def __init__(self):
        super().__init__("Text Extractor")
    
    def process(self, data: fitz.Document, context: Dict[str, Any]) -> List[PageContent]:
        """
        Extract text from all PDF pages.
        
        Args:
            data: PyMuPDF Document
            context: Pipeline context
            
        Returns:
            List of PageContent objects
        """
        pages = []
        total_chars = 0
        
        for page_num in range(len(data)):
            page = data[page_num]
            
            # Extract text
            text = page.get_text("text")
            
            # Clean up text
            text = self._clean_text(text)
            
            if text.strip():
                pages.append(PageContent(
                    page_number=page_num + 1,  # 1-indexed
                    text=text,
                ))
                total_chars += len(text)
        
        # Close the document
        data.close()
        
        context["total_chars"] = total_chars
        context["pages_with_text"] = len(pages)
        
        self.logger.info(f"Extracted text from {len(pages)} pages ({total_chars} chars)")
        
        return pages
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def validate_input(self, data: Any) -> bool:
        """Validate input is a fitz Document"""
        return isinstance(data, fitz.Document)
    
    def get_data_size(self, data: Any) -> int:
        """Get page count"""
        if isinstance(data, fitz.Document):
            return len(data)
        if isinstance(data, list):
            return len(data)
        return 0
