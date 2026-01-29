"""
API Dependencies
Dependency injection for FastAPI routes
"""

from typing import Generator, Optional
from functools import lru_cache
import logging

from fastapi import Depends, HTTPException, status

from app.db.qdrant_client import QdrantManager, get_qdrant_manager
from app.db.redis_client import RedisManager, get_redis_manager
from app.db.factory import CollectionFactory
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.sparse_encoder_service import SparseEncoderService, get_sparse_encoder_service
from app.services.reranker_service import RerankerService, get_reranker_service
from app.services.llm_service import LLMService, get_llm_service
from app.services.session_service import SessionService, get_session_service
from app.pipelines.ingestion import IngestionPipeline, create_ingestion_pipeline
from app.pipelines.query import QueryPipeline, create_query_pipeline
from app.core.config import SupportedCountry

logger = logging.getLogger(__name__)


# === Database Dependencies ===

def get_qdrant() -> QdrantManager:
    """Get Qdrant manager instance"""
    return get_qdrant_manager()


def get_redis() -> RedisManager:
    """Get Redis manager instance"""
    return get_redis_manager()


def get_collection_factory(
    qdrant: QdrantManager = Depends(get_qdrant)
) -> CollectionFactory:
    """Get collection factory instance"""
    return CollectionFactory(qdrant.client)


# === Service Dependencies ===

def get_embedder() -> EmbeddingService:
    """Get embedding service instance"""
    return get_embedding_service()


def get_sparse_encoder() -> SparseEncoderService:
    """Get sparse encoder service instance"""
    return get_sparse_encoder_service()


def get_reranker() -> RerankerService:
    """Get reranker service instance"""
    return get_reranker_service()


def get_llm() -> LLMService:
    """Get LLM service instance"""
    return get_llm_service()


def get_sessions() -> SessionService:
    """Get session service instance"""
    return get_session_service()


# === Pipeline Dependencies ===

@lru_cache()
def get_ingestion_pipeline() -> IngestionPipeline:
    """Get cached ingestion pipeline instance"""
    return create_ingestion_pipeline()


@lru_cache()
def get_query_pipeline() -> QueryPipeline:
    """Get cached query pipeline instance"""
    return create_query_pipeline()


# === Validation Dependencies ===

def validate_country(country: str) -> SupportedCountry:
    """
    Validate and convert country string to SupportedCountry enum.
    
    Args:
        country: Country string from request
        
    Returns:
        SupportedCountry enum value
        
    Raises:
        HTTPException if country is not supported
    """
    try:
        return SupportedCountry(country.lower())
    except ValueError:
        supported = [c.value for c in SupportedCountry]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported country: {country}. Supported: {supported}"
        )


def validate_session(
    session_id: Optional[str],
    session_service: SessionService = Depends(get_sessions),
) -> Optional[str]:
    """
    Validate session ID if provided.
    
    Args:
        session_id: Optional session ID
        session_service: Session service instance
        
    Returns:
        Validated session ID or None
        
    Raises:
        HTTPException if session not found
    """
    if session_id is None:
        return None
    
    if not session_service.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}"
        )
    
    return session_id
