"""
Qdrant Vector Database Client
Connection management and operations for hybrid vector search
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams,
    PointStruct, Filter, FieldCondition, MatchValue, MatchAny,
    SparseIndexParams, Modifier
)
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantManager:
    """
    Qdrant database manager singleton.
    Handles connection, collection operations, and hybrid search.
    """
    
    _instance: Optional['QdrantManager'] = None
    _client: Optional[QdrantClient] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish connection to Qdrant"""
        logger.info(f"Connecting to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        
        self._client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            timeout=60,
        )
        
        # Test connection
        try:
            self._client.get_collections()
            logger.info("✅ Connected to Qdrant successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            raise
    
    @property
    def client(self) -> QdrantClient:
        """Get the Qdrant client instance"""
        if self._client is None:
            self._connect()
        return self._client
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists"""
        return self.client.collection_exists(collection_name)
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get collection information"""
        if not self.collection_exists(collection_name):
            return None
        
        info = self.client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "status": info.status.value,
        }
    
    def create_collection(
        self,
        collection_name: str,
        vectors_config: Dict[str, VectorParams],
        sparse_vectors_config: Optional[Dict[str, SparseVectorParams]] = None,
    ) -> bool:
        """
        Create a new collection with specified configuration.
        
        Args:
            collection_name: Name of the collection
            vectors_config: Dense vector configuration
            sparse_vectors_config: Sparse vector configuration (optional)
            
        Returns:
            True if created successfully
        """
        if self.collection_exists(collection_name):
            logger.warning(f"Collection '{collection_name}' already exists")
            return False
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_vectors_config,
        )
        
        logger.info(f"✅ Created collection: {collection_name}")
        return True
    
    def upsert_points(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Upsert points to collection with batching.
        
        Args:
            collection_name: Target collection
            points: List of point dicts with id, vector, sparse_vector, payload
            batch_size: Batch size for upserts
            
        Returns:
            Number of points upserted
        """
        from tqdm import tqdm
        
        total = 0
        num_batches = (len(points) + batch_size - 1) // batch_size
        
        logger.info(f"📊 Storing {len(points)} points to Qdrant ({num_batches} batches)...")
        
        with tqdm(total=len(points), desc="Storing in Qdrant", unit="point") as pbar:
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                
                point_structs = []
                for p in batch:
                    # Build vector dict
                    vectors = {}
                    if "dense_vector" in p:
                        vectors["dense"] = p["dense_vector"]
                    if "sparse_vector" in p:
                        vectors["sparse"] = models.SparseVector(
                            indices=p["sparse_vector"]["indices"],
                            values=p["sparse_vector"]["values"],
                        )
                    
                    point_structs.append(PointStruct(
                        id=p["id"],
                        vector=vectors,
                        payload=p.get("payload", {}),
                    ))
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=point_structs,
                    wait=True,
                )
                total += len(batch)
                pbar.update(len(batch))
            
        logger.info(f"✅ Upserted {total} points to {collection_name}")
        return total
    
    def hybrid_search(
        self,
        collection_name: str,
        dense_vector: List[float],
        sparse_vector: Dict[str, List],
        filter_conditions: Optional[Filter] = None,
        limit: int = 25,
    ) -> List[Dict]:
        """
        Perform hybrid search with RRF fusion.
        
        Args:
            collection_name: Collection to search
            dense_vector: Dense query vector
            sparse_vector: Sparse query vector (indices, values)
            filter_conditions: Optional filter
            limit: Number of results
            
        Returns:
            List of search results with payloads and scores
        """
        # Build sparse vector
        sparse_vec = models.SparseVector(
            indices=sparse_vector["indices"],
            values=sparse_vector["values"],
        )
        
        # Perform hybrid search with prefetch and RRF fusion
        results = self.client.query_points(
            collection_name=collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=limit,
                ),
                models.Prefetch(
                    query=sparse_vec,
                    using="sparse",
                    limit=limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=filter_conditions,
            limit=limit,
            with_payload=True,
        )
        
        return [
            {
                "id": point.id,
                "score": point.score,
                "payload": point.payload,
            }
            for point in results.points
        ]
    
    def dense_search(
        self,
        collection_name: str,
        dense_vector: List[float],
        filter_conditions: Optional[Filter] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Perform dense-only vector search.
        
        Args:
            collection_name: Collection to search
            dense_vector: Query vector
            filter_conditions: Optional filter
            limit: Number of results
            
        Returns:
            List of search results
        """
        results = self.client.search(
            collection_name=collection_name,
            query_vector=("dense", dense_vector),
            query_filter=filter_conditions,
            limit=limit,
            with_payload=True,
        )
        
        return [
            {
                "id": point.id,
                "score": point.score,
                "payload": point.payload,
            }
            for point in results
        ]
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        if not self.collection_exists(collection_name):
            return False
        
        self.client.delete_collection(collection_name)
        logger.warning(f"🗑️ Deleted collection: {collection_name}")
        return True
    
    def get_points_count(self, collection_name: str) -> int:
        """Get number of points in collection"""
        if not self.collection_exists(collection_name):
            return 0
        info = self.client.get_collection(collection_name)
        return info.points_count
    
    def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False


def get_qdrant_manager() -> QdrantManager:
    """Get Qdrant manager singleton"""
    return QdrantManager()
