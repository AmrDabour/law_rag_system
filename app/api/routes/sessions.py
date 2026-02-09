"""
Session Routes
Conversation session management
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.api.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionHistory,
    MessageSchema,
)
from app.api.deps import get_sessions
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/v1", tags=["Sessions"])
logger = logging.getLogger(__name__)


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreate = None,
    session_service: SessionService = Depends(get_sessions),
) -> SessionResponse:
    """
    Create a new conversation session.
    
    Sessions store conversation history for context-aware queries.
    Sessions expire after 24 hours of inactivity.
    
    - **country**: Optional default country for queries
    - **metadata**: Optional additional metadata
    """
    if request is None:
        request = SessionCreate()
    
    session_id = session_service.create_session(
        country=request.country,
        metadata=request.metadata,
    )
    
    session = session_service.get_session(session_id)
    
    return SessionResponse(
        session_id=session_id,
        created_at=session.get("created_at", ""),
    )


@router.get("/sessions/{session_id}", response_model=SessionHistory)
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_sessions),
) -> SessionHistory:
    """
    Get session details and conversation history.
    
    - **session_id**: Session ID to retrieve
    """
    session = session_service.get_session(session_id)
    
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )
    
    messages = [
        MessageSchema(
            role=msg["role"],
            content=msg["content"],
            timestamp=msg.get("timestamp", ""),
            metadata=msg.get("metadata"),
        )
        for msg in session.get("messages", [])
    ]
    
    return SessionHistory(
        session_id=session_id,
        created_at=session.get("created_at", ""),
        updated_at=session.get("updated_at", ""),
        messages=messages,
        metadata=session.get("metadata", {}),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_sessions),
):
    """
    Delete a session.
    
    - **session_id**: Session ID to delete
    """
    if not session_service.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )
    
    deleted = session_service.delete_session(session_id)
    
    if deleted:
        return {
            "success": True,
            "message": f"Session {session_id} deleted",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )


@router.get("/sessions")
async def list_sessions(
    session_service: SessionService = Depends(get_sessions),
):
    """
    List all active sessions.
    
    Note: This is mainly for debugging/admin purposes.
    """
    session_ids = session_service.list_sessions()
    
    return {
        "success": True,
        "count": len(session_ids),
        "sessions": session_ids[:100],  # Limit to 100
    }
