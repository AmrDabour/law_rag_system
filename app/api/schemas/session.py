"""
Session API Schemas
Request and response models for session management
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SessionCreate(BaseModel):
    """Create session request"""
    country: Optional[str] = Field(
        default="egypt",
        description="Default country for queries"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional session metadata"
    )


class SessionResponse(BaseModel):
    """Session creation response"""
    session_id: str = Field(..., description="Unique session ID")
    created_at: str = Field(..., description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2026-01-29T10:30:00Z"
            }
        }


class MessageSchema(BaseModel):
    """A message in conversation history"""
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class SessionHistory(BaseModel):
    """Session history response"""
    session_id: str
    created_at: str
    updated_at: str
    messages: List[MessageSchema]
    metadata: Dict[str, Any] = Field(default_factory=dict)
