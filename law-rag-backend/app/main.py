"""
Egyptian Law RAG API
FastAPI application entry point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.utils.logger import setup_logging
from app.api.routes import health, query, ingest, laws, sessions

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # === STARTUP ===
    logger.info("🚀 Starting Egyptian Law RAG API...")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   Version: {settings.APP_VERSION}")
    
    # Pre-load services (optional - they load lazily anyway)
    try:
        logger.info("Pre-loading services...")
        
        # Test Qdrant connection
        from app.db.qdrant_client import get_qdrant_manager
        qdrant = get_qdrant_manager()
        if qdrant.health_check():
            logger.info("   ✅ Qdrant connected")
        else:
            logger.warning("   ⚠️ Qdrant not available")
        
        # Test Redis connection
        from app.db.redis_client import get_redis_manager
        redis = get_redis_manager()
        if redis.health_check():
            logger.info("   ✅ Redis connected")
        else:
            logger.warning("   ⚠️ Redis not available")
        
        logger.info("✅ API ready to serve requests")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        # Don't fail startup - services can be initialized on first request
    
    yield
    
    # === SHUTDOWN ===
    logger.info("👋 Shutting down Egyptian Law RAG API...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Egyptian Law RAG API - Intelligent Legal Assistant
    
    Features:
    - Hybrid search (Dense + Sparse vectors)
    - Cross-encoder reranking
    - Article-based chunking for accurate citations
    - Multi-country support
    - Session-based conversation history
    
    Supported Countries:
    - Egypt (egypt)
    - Jordan (jordan)
    - UAE (uae)
    - Saudi Arabia (saudi)
    - Kuwait (kuwait)
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(query.router)
app.include_router(ingest.router)
app.include_router(laws.router)
app.include_router(sessions.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
