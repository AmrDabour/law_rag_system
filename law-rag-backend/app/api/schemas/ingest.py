"""
Ingest API Schemas
Request and response models for ingestion endpoint
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Ingestion response body"""
    success: bool = Field(..., description="Whether ingestion was successful")
    message: str = Field(..., description="Status message")
    collection: str = Field(..., description="Target collection name")
    articles_found: int = Field(..., description="Number of articles detected")
    chunks_created: int = Field(..., description="Number of chunks created")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    pages_processed: int = Field(default=0, description="Number of pages processed")
    errors: List[str] = Field(default_factory=list, description="Any errors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Law ingested successfully",
                "collection": "laws_egypt",
                "articles_found": 395,
                "chunks_created": 412,
                "processing_time_ms": 25000.5,
                "pages_processed": 150,
                "errors": []
            }
        }


class LawInfo(BaseModel):
    """Information about an ingested law"""
    law_type: str
    law_name: str
    law_name_en: Optional[str] = None
    law_number: Optional[str] = None
    law_year: Optional[str] = None
    articles_count: int
    source_file: str


class CollectionInfo(BaseModel):
    """Information about a country collection"""
    collection_name: str
    country: str
    status: str
    points_count: int
    vectors_count: int
    laws: List[LawInfo] = Field(default_factory=list)


class LawsListResponse(BaseModel):
    """Response for listing laws"""
    success: bool = True
    countries: dict = Field(..., description="Country collections info")
