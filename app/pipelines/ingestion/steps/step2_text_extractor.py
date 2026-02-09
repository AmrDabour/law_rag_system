"""
Step 2: Text Extractor
Extract Arabic text from PDF pages
"""

from typing import Any, Dict, List
import fitz  # PyMuPDF
import logging
import re
import unicodedata

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import PageContent

logger = logging.getLogger(__name__)

# Pattern to match sequences of Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩)
# Only matches 2+ digits since single digits don't need reversal
ARABIC_NUMERALS_PATTERN = re.compile(r'[٠-٩]{2,}')


class TextExtractorStep(PipelineStep):
    """
    Step 2: Extract text from PDF pages.
    
    Input: fitz.Document
    Output: List[PageContent] with page number and text
    
    Includes fixes for:
    - Arabic Presentation Forms (ﻛ -> ك)
    - Reversed Arabic numerals from RTL PDF extraction
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
            
            # Normalize Arabic presentation forms to standard characters
            text = self._normalize_arabic(text)
            
            # Clean up text
            text = self._clean_text(text)
            
            # Fix reversed Arabic numerals
            text = self._fix_reversed_numbers(text)
            
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
    
    def _normalize_arabic(self, text: str) -> str:
        """
        Normalize Arabic Presentation Forms to standard Arabic characters.
        
        PDFs often contain Arabic Presentation Forms (Unicode FB50-FDFF, FE70-FEFF)
        which are visual representations of Arabic characters. This method converts
        them to standard Arabic characters using Unicode NFKC normalization.
        
        Examples: ﻛ ﻜ ﻚ ﻙ -> ك
        
        Args:
            text: Text with potential Arabic Presentation Forms
            
        Returns:
            Text with normalized Arabic characters
        """
        if not text:
            return ""
        
        # NFKC normalization converts compatibility characters to their canonical forms
        # This handles Arabic Presentation Forms -> Standard Arabic
        return unicodedata.normalize('NFKC', text)
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and merge fragmented Arabic text from PDF extraction.
        
        PDF extraction often fragments text with arbitrary line breaks,
        splitting words and sentences. This method intelligently merges
        lines while preserving actual paragraph breaks.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned and merged text
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        merged_lines = []
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # Empty line indicates paragraph break
                if current_paragraph:
                    merged_lines.append(' '.join(current_paragraph))
                    current_paragraph = []
                continue
            
            # Check if line ends with sentence-ending punctuation
            ends_sentence = line.endswith(('.', '。', '؟', '!', ':', '،'))
            
            current_paragraph.append(line)
            
            # If line ends a sentence, close the paragraph
            if ends_sentence:
                merged_lines.append(' '.join(current_paragraph))
                current_paragraph = []
        
        # Don't forget remaining content
        if current_paragraph:
            merged_lines.append(' '.join(current_paragraph))
        
        # Join paragraphs with double newline for clear separation
        return '\n\n'.join(merged_lines)
    
    def _fix_reversed_numbers(self, text: str) -> str:
        """
        Fix reversed Arabic numerals from PDF extraction.
        
        PyMuPDF sometimes extracts multi-digit Arabic numbers in reversed order
        (e.g., ٢٠٠٨ becomes ٨٠٠٢). This method finds all Arabic numeral 
        sequences and reverses them to correct the order.
        
        Args:
            text: Text with potentially reversed Arabic numerals
            
        Returns:
            Text with corrected Arabic numerals
        """
        if not text:
            return text
        
        def reverse_match(match):
            """Reverse the matched Arabic numeral sequence"""
            return match.group(0)[::-1]
        
        # Replace all Arabic numeral sequences with their reversed version
        return ARABIC_NUMERALS_PATTERN.sub(reverse_match, text)
    
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

