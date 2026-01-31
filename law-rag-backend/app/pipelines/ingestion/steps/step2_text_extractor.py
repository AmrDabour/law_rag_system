"""
Step 2: Text Extractor
Extract Arabic text from PDF pages with proper RTL handling
"""

from typing import Any, Dict, List
import fitz  # PyMuPDF
import logging
import re

# RTL text handling
try:
    from bidi.algorithm import get_display
    BIDI_AVAILABLE = True
except ImportError:
    BIDI_AVAILABLE = False

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import PageContent

logger = logging.getLogger(__name__)


class TextExtractorStep(PipelineStep):
    """
    Step 2: Extract text from PDF pages.
    
    Input: fitz.Document
    Output: List[PageContent] with page number and text
    
    Includes RTL text fixing for Arabic content using python-bidi.
    """
    
    def __init__(self):
        super().__init__("Text Extractor")
        if not BIDI_AVAILABLE:
            self.logger.warning("python-bidi not installed. RTL text may be reversed.")
    
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
            
            # Clean up and fix RTL text
            text = self._clean_text(text)
            text = self._fix_rtl_text(text)
            
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
    
    def _fix_rtl_text(self, text: str) -> str:
        """
        Fix RTL text ordering issues from PDF extraction.
        
        PyMuPDF extracts text in the order stored in the PDF, which for RTL
        languages often means numbers are reversed (e.g., 2008 becomes 8002).
        
        This method applies the Unicode Bidirectional Algorithm to fix the
        logical ordering of characters while preserving the visual appearance.
        
        Args:
            text: Extracted text with potential RTL issues
            
        Returns:
            Text with corrected RTL ordering
        """
        if not BIDI_AVAILABLE or not text:
            return text
        
        try:
            # Process line by line to preserve structure
            lines = text.split('\n')
            fixed_lines = []
            
            for line in lines:
                if line.strip():
                    # Apply bidi algorithm to fix RTL ordering
                    # get_display converts logical order to visual order
                    fixed_line = get_display(line)
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            
            return '\n'.join(fixed_lines)
        except Exception as e:
            self.logger.warning(f"RTL fixing failed: {e}")
            return text
    
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

