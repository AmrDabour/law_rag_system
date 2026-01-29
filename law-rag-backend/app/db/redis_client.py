"""
Redis Client
Session storage and caching
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4
import redis
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis connection manager singleton.
    Handles session storage and caching.
    """
    
    _instance: Optional['RedisManager'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish connection to Redis"""
        logger.info(f"Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        
        self._client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_timeout=5,
        )
        
        # Test connection
        try:
            self._client.ping()
            logger.info("✅ Connected to Redis successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance"""
        if self._client is None:
            self._connect()
        return self._client
    
    # === Session Management ===
    
    def create_session(self, metadata: Optional[Dict] = None) -> str:
        """
        Create a new session.
        
        Args:
            metadata: Optional session metadata
            
        Returns:
            Session ID
        """
        session_id = str(uuid4())
        session_data = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "metadata": metadata or {},
        }
        
        self.client.setex(
            f"session:{session_id}",
            settings.SESSION_TTL_SECONDS,
            json.dumps(session_data, ensure_ascii=False),
        )
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session data.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data or None if not found
        """
        data = self.client.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return self.client.exists(f"session:{session_id}") > 0
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Add a message to session history.
        
        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            True if successful
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        })
        session["updated_at"] = datetime.now().isoformat()
        
        # Update with TTL refresh
        self.client.setex(
            f"session:{session_id}",
            settings.SESSION_TTL_SECONDS,
            json.dumps(session, ensure_ascii=False),
        )
        
        return True
    
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get messages from session.
        
        Args:
            session_id: Session ID
            limit: Max number of recent messages
            
        Returns:
            List of messages
        """
        session = self.get_session(session_id)
        if not session:
            return []
        
        messages = session.get("messages", [])
        if limit:
            return messages[-limit:]
        return messages
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        result = self.client.delete(f"session:{session_id}")
        if result:
            logger.info(f"Deleted session: {session_id}")
        return result > 0
    
    def list_sessions(self, pattern: str = "session:*") -> List[str]:
        """List all session IDs"""
        keys = self.client.keys(pattern)
        return [k.replace("session:", "") for k in keys]
    
    # === Caching ===
    
    def cache_set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
    ) -> bool:
        """
        Set a cache value.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            self.client.setex(
                f"cache:{key}",
                ttl,
                json.dumps(value, ensure_ascii=False),
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def cache_get(self, key: str) -> Optional[Any]:
        """
        Get a cached value.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        data = self.client.get(f"cache:{key}")
        if data:
            return json.loads(data)
        return None
    
    def cache_delete(self, key: str) -> bool:
        """Delete a cache entry"""
        return self.client.delete(f"cache:{key}") > 0
    
    # === Health Check ===
    
    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            return self.client.ping()
        except Exception:
            return False


def get_redis_manager() -> RedisManager:
    """Get Redis manager singleton"""
    return RedisManager()
