"""
Step 7: Qdrant Storer
Store chunks with dual vectors in Qdrant
"""

from typing import Any, Dict, List
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import DocumentChunk
from app.db.qdrant_client import get_qdrant_manager

logger = logging.getLogger(__name__)


class QdrantStorerStep(PipelineStep):
    """
    Step 7: Store chunks in Qdrant with dual vectors.
    
    Input: List[DocumentChunk] with both vectors
    Output: Number of points stored
    """
    
    def __init__(self):
        super().__init__("Qdrant Storer")
        self._qdrant = None
    
    @property
    def qdrant(self):
        """Lazy load Qdrant manager"""
        if self._qdrant is None:
            self._qdrant = get_qdrant_manager()
        return self._qdrant
    
    def process(self, data: List[DocumentChunk], context: Dict[str, Any]) -> int:
        """
        Store all chunks in Qdrant.
        
        Args:
            data: List of DocumentChunk with vectors
            context: Pipeline context (must contain 'collection_name')
            
        Returns:
            Number of points stored
        """
        if not data:
            return 0
        
        collection_name = context.get("collection_name")
        if not collection_name:
            raise ValueError("collection_name not found in context")
        
        total = len(data)
        self.logger.info(f"📦 Storing {total} chunks to {collection_name}...")
        print(f"\n📦 Qdrant Storage Progress ({total} chunks):")
        
        # Convert chunks to Qdrant points
        points = [chunk.to_qdrant_point() for chunk in data]
        
        # Upsert to Qdrant
        stored = self.qdrant.upsert_points(
            collection_name=collection_name,
            points=points,
            batch_size=100,
        )
        
        context["points_stored"] = stored
        self.logger.info(f"Stored {stored} points to {collection_name}")
        
        return stored
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, list):
            return False
        
        for chunk in data:
            if not isinstance(chunk, DocumentChunk):
                return False
            if chunk.dense_vector is None:
                self.logger.warning(f"Chunk {chunk.chunk_id} missing dense vector")
                return False
            if chunk.sparse_vector is None:
                self.logger.warning(f"Chunk {chunk.chunk_id} missing sparse vector")
                return False
        
        return True
