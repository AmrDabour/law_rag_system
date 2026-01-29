"""
Common API Schemas
Shared response models
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Overall health status")
    qdrant: str = Field(..., description="Qdrant connection status")
    redis: str = Field(..., description="Redis connection status")
    version: str = Field(..., description="API version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "qdrant": "ok",
                "redis": "ok",
                "version": "1.0.0"
            }
        }


class ReadyResponse(BaseModel):
    """Readiness check response"""
    ready: bool
    services: Dict[str, bool]
    models_loaded: Dict[str, bool]
