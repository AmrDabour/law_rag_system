"""
Configuration management for Egyptian Law RAG System
Includes SupportedCountry enum and Pydantic Settings
"""

from enum import Enum
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class SupportedCountry(str, Enum):
    """
    Validated country codes - prevents typos and duplicate collections.
    Add new countries here to enable automatic Golden Schema creation.
    """
    EGYPT = "egypt"
    JORDAN = "jordan"
    UAE = "uae"
    SAUDI = "saudi"
    KUWAIT = "kuwait"


class LawType(str, Enum):
    """Supported law types for filtering"""
    CRIMINAL = "criminal"
    CIVIL = "civil"
    COMMERCIAL = "commercial"
    ECONOMIC = "economic"
    ADMINISTRATIVE = "administrative"
    ARBITRATION = "arbitration"
    LABOR = "labor"
    PERSONAL_STATUS = "personal_status"


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # === API Configuration ===
    APP_NAME: str = "Law RAG API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # === Google Gemini API ===
    GOOGLE_API_KEY: str
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048
    
    # === Qdrant Vector Database ===
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: Optional[str] = None
    
    # === Redis Session Storage ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    SESSION_TTL: int = 86400  # 24 hours
    
    # === Embedding Model (Dense) ===
    EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-0.6B"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 32
    
    # === Sparse Encoder (BM25) ===
    SPARSE_MODEL: str = "Qdrant/bm25"
    
    # === Reranker Model ===
    RERANKER_MODEL: str = "Qwen/Qwen3-Reranker-0.6B"
    RERANKER_MAX_LENGTH: int = 512
    
    # === Search Configuration ===
    HYBRID_PREFETCH: int = 25  # Top-K for each search type before reranking
    RERANK_TOP_K: int = 5  # Final top-K after reranking
    DEFAULT_TOP_K: int = 5  # Default number of results to return
    
    # === Chunking Configuration ===
    MAX_CHUNK_TOKENS: int = 1000
    MIN_CHUNK_TOKENS: int = 50
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
