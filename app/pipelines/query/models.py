"""
Query Pipeline Models
Data models for the query pipeline
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class QueryInput:
    """Input to query pipeline"""
    question: str
    country: str
    law_types: Optional[List[str]] = None
    session_id: Optional[str] = None
    top_k: int = 5


@dataclass
class RetrievedChunk:
    """A chunk retrieved from vector search"""
    chunk_id: str
    content: str
    article_number: Optional[int]
    article_text: Optional[str]
    law_name: str
    law_type: str
    page_number: int
    
    # Scores
    hybrid_score: float = 0.0
    rerank_score: Optional[float] = None
    
    # Additional metadata
    chapter: Optional[str] = None
    chunk_part: int = 1
    total_parts: int = 1
    
    @classmethod
    def from_qdrant_result(cls, result: Dict) -> 'RetrievedChunk':
        """Create from Qdrant search result"""
        payload = result.get("payload", {})
        return cls(
            chunk_id=payload.get("chunk_id", result.get("id", "")),
            content=payload.get("content", ""),
            article_number=payload.get("article_number"),
            article_text=payload.get("article_text"),
            law_name=payload.get("law_name", ""),
            law_type=payload.get("law_type", ""),
            page_number=payload.get("page_number", 0),
            hybrid_score=result.get("score", 0.0),
            chapter=payload.get("chapter"),
            chunk_part=payload.get("chunk_part", 1),
            total_parts=payload.get("total_parts", 1),
        )


@dataclass
class Source:
    """Citation source for answer"""
    law_name: str
    article_number: Optional[int]
    article_text: Optional[str]
    page_number: int
    relevance_score: float
    content_preview: str  # First 200 chars
    
    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization"""
        return {
            "law_name": self.law_name,
            "article_number": self.article_number,
            "article_text": self.article_text,
            "page_number": self.page_number,
            "relevance_score": round(self.relevance_score, 4),
            "content_preview": self.content_preview,
        }
    
    def format_citation(self) -> str:
        """Format as citation string"""
        if self.article_number:
            return f"{self.law_name} - مادة {self.article_number} (صفحة {self.page_number})"
        return f"{self.law_name} (صفحة {self.page_number})"


@dataclass
class QueryOutput:
    """Output from query pipeline"""
    success: bool
    answer: str
    sources: List[Source]
    
    # Timing
    query_time_ms: float
    
    # Metadata
    chunks_retrieved: int
    chunks_after_rerank: int
    
    # Model info
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    reranker_model: str = "Qwen/Qwen3-Reranker-0.6B"
    llm_model: str = "gemini-2.5-flash"
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dict for API response"""
        return {
            "success": self.success,
            "answer": self.answer,
            "sources": [s.to_dict() for s in self.sources],
            "metadata": {
                "query_time_ms": round(self.query_time_ms, 2),
                "chunks_retrieved": self.chunks_retrieved,
                "chunks_after_rerank": self.chunks_after_rerank,
                "embedding_model": self.embedding_model,
                "reranker_model": self.reranker_model,
                "llm_model": self.llm_model,
            },
            "errors": self.errors,
        }
