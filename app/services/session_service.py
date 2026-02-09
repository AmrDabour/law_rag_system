"""
Session Service
Redis-based session management for conversation history
"""

from typing import Dict, List, Optional
from datetime import datetime
from uuid import uuid4
import logging

from app.db.redis_client import get_redis_manager, RedisManager
from app.core.config import settings

logger = logging.getLogger(__name__)


class SessionService:
    """
    Session management service.
    Handles conversation history and session state using Redis.
    
    Features:
    - Session creation and management
    - Conversation history storage
    - Automatic TTL-based expiration
    """
    
    _instance: Optional['SessionService'] = None
    _redis: Optional[RedisManager] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            SessionService._initialized = True
    
    def _initialize(self):
        """Initialize the session service"""
        logger.info("Initializing session service")
        self._redis = get_redis_manager()
        logger.info("✅ Session service initialized")
    
    @property
    def redis(self) -> RedisManager:
        """Get Redis manager"""
        if self._redis is None:
            self._redis = get_redis_manager()
        return self._redis
    
    def create_session(
        self,
        country: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Create a new session.
        
        Args:
            country: Default country for queries
            metadata: Additional session metadata
            
        Returns:
            Session ID
        """
        session_metadata = metadata or {}
        if country:
            session_metadata["country"] = country
        
        session_id = self.redis.create_session(session_metadata)
        logger.info(f"Created session: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None
        """
        return self.redis.get_session(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return self.redis.session_exists(session_id)
    
    def add_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Add user message to session.
        
        Args:
            session_id: Session ID
            content: Message content
            metadata: Optional metadata (e.g., query filters)
            
        Returns:
            True if successful
        """
        return self.redis.add_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata=metadata,
        )
    
    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        sources: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Add assistant message to session.
        
        Args:
            session_id: Session ID
            content: Answer content
            sources: List of source citations
            metadata: Optional metadata
            
        Returns:
            True if successful
        """
        msg_metadata = metadata or {}
        if sources:
            msg_metadata["sources"] = sources
        
        return self.redis.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            metadata=msg_metadata,
        )
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get recent conversation history.
        
        Args:
            session_id: Session ID
            limit: Maximum messages to return
            
        Returns:
            List of messages
        """
        return self.redis.get_messages(session_id, limit)
    
    def get_context_for_llm(
        self,
        session_id: str,
        max_messages: int = 6,
    ) -> str:
        """
        Get conversation context formatted for LLM.
        
        Args:
            session_id: Session ID
            max_messages: Maximum previous messages to include
            
        Returns:
            Formatted conversation context
        """
        messages = self.get_conversation_history(session_id, max_messages)
        
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages:
            role = "المستخدم" if msg["role"] == "user" else "المساعد"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n\n".join(context_parts)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        return self.redis.delete_session(session_id)
    
    def list_sessions(self) -> List[str]:
        """List all session IDs"""
        return self.redis.list_sessions()


# Singleton getter
_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """Get session service singleton"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
