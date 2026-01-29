"""
Collection Factory
Automatic collection creation with Golden Schema for multi-country support
"""

from typing import Dict, List, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    VectorParams, SparseVectorParams, SparseIndexParams,
    Distance, Modifier, PayloadSchemaType
)
import logging

from app.core.config import SupportedCountry, settings

logger = logging.getLogger(__name__)


class CollectionFactory:
    """
    Factory for creating Qdrant collections with Golden Schema.
    Ensures every country gets identical Hybrid (Dense + Sparse) configuration.
    
    Benefits:
    - Schema Consistency: Identical hybrid schema for all countries
    - Operational Safety: Validates against SupportedCountry enum
    - Speed: Adding a new country is just a config update
    """
    
    # === GOLDEN SCHEMA DEFINITION ===
    # This schema is automatically applied to ALL country collections
    
    @staticmethod
    def get_golden_dense_config() -> Dict[str, VectorParams]:
        """Get the standard dense vector configuration"""
        return {
            "dense": VectorParams(
                size=settings.EMBEDDING_DIMENSION,  # 1024 for Qwen3-Embedding
                distance=Distance.COSINE,
            )
        }
    
    @staticmethod
    def get_golden_sparse_config() -> Dict[str, SparseVectorParams]:
        """Get the standard sparse vector configuration"""
        return {
            "sparse": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=True,  # Save RAM for sparse index
                ),
                modifier=Modifier.IDF,  # BM25-style IDF weighting
            )
        }
    
    # === END GOLDEN SCHEMA ===
    
    def __init__(self, client: QdrantClient):
        """
        Initialize factory with Qdrant client.
        
        Args:
            client: QdrantClient instance
        """
        self.client = client
    
    def get_collection_name(self, country: SupportedCountry) -> str:
        """
        Generate standardized collection name.
        
        Args:
            country: Validated SupportedCountry enum
            
        Returns:
            Collection name (e.g., "laws_egypt")
        """
        return f"laws_{country.value}"
    
    def ensure_country_collection(self, country: SupportedCountry) -> str:
        """
        Ensures the collection exists with the GOLDEN SCHEMA.
        Auto-creates it if missing. Returns collection name.
        
        This is the main method to use - it guarantees:
        1. Collection exists
        2. Has correct hybrid schema (dense + sparse)
        3. Has proper payload indexes
        
        Args:
            country: Validated SupportedCountry enum (prevents typos)
            
        Returns:
            Collection name (e.g., "laws_egypt")
        """
        collection_name = self.get_collection_name(country)
        
        # 1. Check if already exists
        if self.client.collection_exists(collection_name):
            logger.info(f"✓ Collection '{collection_name}' exists")
            return collection_name
        
        # 2. Create with Golden Schema
        logger.info(f"🚀 Initializing new legal system for: {country.name}")
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=self.get_golden_dense_config(),
            sparse_vectors_config=self.get_golden_sparse_config(),
        )
        
        # 3. Create payload indexes for efficient filtering
        self._create_payload_indexes(collection_name)
        
        logger.info(f"✅ Collection '{collection_name}' created with Golden Schema")
        logger.info(f"   - Dense vectors: {settings.EMBEDDING_DIMENSION}D (Cosine)")
        logger.info(f"   - Sparse vectors: BM25 with IDF modifier")
        
        return collection_name
    
    def _create_payload_indexes(self, collection_name: str) -> None:
        """
        Create indexes for common filter fields.
        
        Args:
            collection_name: Collection to index
        """
        index_fields = [
            ("law_type", PayloadSchemaType.KEYWORD),
            ("article_number", PayloadSchemaType.INTEGER),
            ("law_name", PayloadSchemaType.KEYWORD),
            ("country", PayloadSchemaType.KEYWORD),
        ]
        
        for field_name, field_type in index_fields:
            try:
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field_name,
                    field_schema=field_type,
                )
                logger.debug(f"   Created index: {field_name}")
            except Exception as e:
                # Index may already exist
                logger.debug(f"   Index {field_name}: {e}")
    
    def list_country_collections(self) -> Dict[str, Dict]:
        """
        List all country collections and their status.
        
        Returns:
            Dict mapping country to collection info
        """
        result = {}
        
        for country in SupportedCountry:
            collection_name = self.get_collection_name(country)
            exists = self.client.collection_exists(collection_name)
            
            if exists:
                info = self.client.get_collection(collection_name)
                result[country.value] = {
                    "collection": collection_name,
                    "points_count": info.points_count,
                    "status": "active",
                    "vectors_count": info.vectors_count,
                }
            else:
                result[country.value] = {
                    "collection": collection_name,
                    "points_count": 0,
                    "status": "not_initialized",
                    "vectors_count": 0,
                }
        
        return result
    
    def delete_country_collection(self, country: SupportedCountry) -> bool:
        """
        Delete a country's collection (use with caution).
        
        Args:
            country: Country to delete
            
        Returns:
            True if deleted
        """
        collection_name = self.get_collection_name(country)
        
        if self.client.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
            logger.warning(f"🗑️ Deleted collection: {collection_name}")
            return True
        
        return False
    
    def reset_country_collection(self, country: SupportedCountry) -> str:
        """
        Reset a country's collection (delete and recreate).
        
        Args:
            country: Country to reset
            
        Returns:
            Collection name
        """
        self.delete_country_collection(country)
        return self.ensure_country_collection(country)
    
    def get_collection_stats(self, country: SupportedCountry) -> Optional[Dict]:
        """
        Get detailed statistics for a country's collection.
        
        Args:
            country: Country to query
            
        Returns:
            Collection statistics or None if not exists
        """
        collection_name = self.get_collection_name(country)
        
        if not self.client.collection_exists(collection_name):
            return None
        
        info = self.client.get_collection(collection_name)
        
        return {
            "collection_name": collection_name,
            "country": country.value,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "status": info.status.value,
            "config": {
                "dense_size": settings.EMBEDDING_DIMENSION,
                "dense_distance": "cosine",
                "sparse_enabled": True,
                "sparse_modifier": "idf",
            }
        }
