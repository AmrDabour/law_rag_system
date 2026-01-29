"""
Query API Schemas
Request and response models for query endpoint
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Query request body"""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Legal question in Arabic",
        json_schema_extra={"example": "ما هي عقوبة السرقة في القانون المصري؟"}
    )
    country: str = Field(
        default="egypt",
        description="Country code (egypt, jordan, uae, saudi, kuwait)",
        json_schema_extra={"example": "egypt"}
    )
    law_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by law types",
        json_schema_extra={"example": ["criminal", "civil"]}
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation history"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of sources to retrieve"
    )


class SourceSchema(BaseModel):
    """Source citation in response"""
    law_name: str = Field(..., description="Name of the law")
    article_number: Optional[int] = Field(None, description="Article number")
    article_text: Optional[str] = Field(None, description="Article marker text")
    page_number: int = Field(..., description="Page number in source document")
    relevance_score: float = Field(..., description="Relevance score (0-1)")
    content_preview: str = Field(..., description="Preview of content")
    
    class Config:
        json_schema_extra = {
            "example": {
                "law_name": "قانون العقوبات",
                "article_number": 318,
                "article_text": "مادة ٣١٨",
                "page_number": 45,
                "relevance_score": 0.95,
                "content_preview": "يعاقب بالحبس مع الشغل..."
            }
        }


class QueryMetadata(BaseModel):
    """Query execution metadata"""
    query_time_ms: float
    chunks_retrieved: int
    chunks_after_rerank: int
    embedding_model: str
    reranker_model: str
    llm_model: str


class QueryResponse(BaseModel):
    """Query response body"""
    success: bool = Field(..., description="Whether query was successful")
    answer: str = Field(..., description="Generated answer in Arabic")
    sources: List[SourceSchema] = Field(..., description="Source citations")
    metadata: QueryMetadata = Field(..., description="Query execution metadata")
    errors: List[str] = Field(default_factory=list, description="Any errors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "وفقاً لقانون العقوبات المصري، عقوبة السرقة تختلف حسب ظروف الجريمة...",
                "sources": [
                    {
                        "law_name": "قانون العقوبات",
                        "article_number": 318,
                        "article_text": "مادة ٣١٨",
                        "page_number": 45,
                        "relevance_score": 0.95,
                        "content_preview": "يعاقب بالحبس مع الشغل..."
                    }
                ],
                "metadata": {
                    "query_time_ms": 850.5,
                    "chunks_retrieved": 25,
                    "chunks_after_rerank": 5,
                    "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
                    "reranker_model": "Qwen/Qwen3-Reranker-0.6B",
                    "llm_model": "gemini-2.5-flash"
                },
                "errors": []
            }
        }
