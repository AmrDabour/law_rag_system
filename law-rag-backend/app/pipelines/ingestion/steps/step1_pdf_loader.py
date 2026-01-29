"""
Step 1: PDF Loader
Load PDF file from bytes content
"""

from typing import Any, Dict
import fitz  # PyMuPDF
import logging

from app.pipelines.base import PipelineStep

logger = logging.getLogger(__name__)


class PDFLoaderStep(PipelineStep):
    """
    Step 1: Load PDF from bytes content.
    
    Input: bytes (PDF content)
    Output: fitz.Document (PyMuPDF document object)
    """
    
    def __init__(self):
        super().__init__("PDF Loader")
    
    def process(self, data: bytes, context: Dict[str, Any]) -> fitz.Document:
        """
        Load PDF document from bytes.
        
        Args:
            data: PDF file content as bytes
            context: Pipeline context
            
        Returns:
            PyMuPDF Document object
        """
        self.logger.info(f"Loading PDF ({len(data)} bytes)")
        
        # Open PDF from memory
        doc = fitz.open(stream=data, filetype="pdf")
        
        # Store page count in context
        context["page_count"] = len(doc)
        context["pdf_metadata"] = {
            "page_count": len(doc),
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
        }
        
        self.logger.info(f"Loaded PDF with {len(doc)} pages")
        
        return doc
    
    def validate_input(self, data: Any) -> bool:
        """Validate that input is bytes"""
        if not isinstance(data, bytes):
            self.logger.error("Input must be bytes")
            return False
        if len(data) < 100:
            self.logger.error("PDF content too small")
            return False
        return True
