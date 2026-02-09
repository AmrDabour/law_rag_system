"""
Health Check Routes
Liveness and readiness endpoints
"""

from fastapi import APIRouter, Depends
import logging

from app.api.schemas.common import HealthResponse, ReadyResponse
from app.api.deps import get_qdrant, get_redis
from app.db.qdrant_client import QdrantManager
from app.db.redis_client import RedisManager
from app.core.config import settings

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check(
    qdrant: QdrantManager = Depends(get_qdrant),
    redis: RedisManager = Depends(get_redis),
) -> HealthResponse:
    """
    Health check endpoint.
    Returns status of all services.
    """
    qdrant_status = "ok" if qdrant.health_check() else "error"
    redis_status = "ok" if redis.health_check() else "error"
    
    overall = "healthy" if qdrant_status == "ok" and redis_status == "ok" else "unhealthy"
    
    return HealthResponse(
        status=overall,
        qdrant=qdrant_status,
        redis=redis_status,
        version=settings.APP_VERSION,
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check(
    qdrant: QdrantManager = Depends(get_qdrant),
    redis: RedisManager = Depends(get_redis),
) -> ReadyResponse:
    """
    Readiness check endpoint.
    Returns detailed service and model status.
    """
    services = {
        "qdrant": qdrant.health_check(),
        "redis": redis.health_check(),
    }
    
    # Check if models can be loaded
    models_loaded = {
        "embedding": False,
        "sparse_encoder": False,
        "reranker": False,
        "llm": False,
    }
    
    try:
        from app.services.embedding_service import get_embedding_service
        get_embedding_service()
        models_loaded["embedding"] = True
    except Exception as e:
        logger.warning(f"Embedding model not ready: {e}")
    
    try:
        from app.services.sparse_encoder_service import get_sparse_encoder_service
        get_sparse_encoder_service()
        models_loaded["sparse_encoder"] = True
    except Exception as e:
        logger.warning(f"Sparse encoder not ready: {e}")
    
    try:
        from app.services.reranker_service import get_reranker_service
        get_reranker_service()
        models_loaded["reranker"] = True
    except Exception as e:
        logger.warning(f"Reranker not ready: {e}")
    
    try:
        from app.services.llm_service import get_llm_service
        get_llm_service()
        models_loaded["llm"] = True
    except Exception as e:
        logger.warning(f"LLM not ready: {e}")
    
    ready = all(services.values()) and all(models_loaded.values())
    
    return ReadyResponse(
        ready=ready,
        services=services,
        models_loaded=models_loaded,
    )
