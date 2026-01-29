"""
Ingestion Pipeline Models
Data models for the ingestion pipeline
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PageContent:
    """Content extracted from a PDF page"""
    page_number: int
    text: str
    

@dataclass
class ArticleMetadata:
    """Metadata for a legal article"""
    country: str
    law_type: str
    law_name: str
    law_name_en: Optional[str] = None
    law_number: Optional[str] = None
    law_year: Optional[str] = None
    source_file: Optional[str] = None


@dataclass
class RawArticle:
    """Raw article extracted from text"""
    article_number: Optional[int]
    article_text: Optional[str]  # e.g., "مادة ٣١٨"
    content: str
    page_number: int
    chapter: Optional[str] = None


@dataclass 
class DocumentChunk:
    """
    A chunk of legal document ready for embedding.
    Represents a single article or part of an article.
    """
    chunk_id: str
    content: str
    article_number: Optional[int]
    article_text: Optional[str]
    page_number: int
    
    # Metadata
    country: str
    law_type: str
    law_name: str
    law_name_en: Optional[str] = None
    law_number: Optional[str] = None
    law_year: Optional[str] = None
    source_file: Optional[str] = None
    chapter: Optional[str] = None
    
    # For long articles split into parts
    chunk_part: int = 1
    total_parts: int = 1
    
    # Vectors (populated by embedding steps)
    dense_vector: Optional[List[float]] = None
    sparse_vector: Optional[Dict[str, List]] = None
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to Qdrant payload dict"""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "article_number": self.article_number,
            "article_text": self.article_text,
            "page_number": self.page_number,
            "country": self.country,
            "law_type": self.law_type,
            "law_name": self.law_name,
            "law_name_en": self.law_name_en,
            "law_number": self.law_number,
            "law_year": self.law_year,
            "source_file": self.source_file,
            "chapter": self.chapter,
            "chunk_part": self.chunk_part,
            "total_parts": self.total_parts,
        }
    
    def to_qdrant_point(self) -> Dict[str, Any]:
        """Convert to Qdrant point format"""
        return {
            "id": self.chunk_id,
            "dense_vector": self.dense_vector,
            "sparse_vector": self.sparse_vector,
            "payload": self.to_payload(),
        }


@dataclass
class IngestionInput:
    """Input to ingestion pipeline"""
    pdf_content: bytes
    filename: str
    metadata: ArticleMetadata
    collection_name: str


@dataclass
class IngestionOutput:
    """Output from ingestion pipeline"""
    success: bool
    collection_name: str
    articles_count: int
    chunks_count: int
    duration_ms: float
    errors: List[str] = field(default_factory=list)
    
    # Detailed stats
    pages_processed: int = 0
    skipped_chunks: int = 0
