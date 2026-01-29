"""
Step 6: Sparse Encoder
Generate BM25 sparse vectors for chunks
"""

from typing import Any, Dict, List
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import DocumentChunk
from app.services.sparse_encoder_service import get_sparse_encoder_service

logger = logging.getLogger(__name__)


class SparseEncoderStep(PipelineStep):
    """
    Step 6: Generate sparse vectors using FastEmbed BM25.
    
    Input: List[DocumentChunk] with dense_vector
    Output: List[DocumentChunk] with both dense_vector and sparse_vector
    """
    
    def __init__(self):
        super().__init__("Sparse Encoder")
        self._sparse_service = None
    
    @property
    def sparse_service(self):
        """Lazy load sparse encoder service"""
        if self._sparse_service is None:
            self._sparse_service = get_sparse_encoder_service()
        return self._sparse_service
    
    def process(self, data: List[DocumentChunk], context: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Generate sparse vectors for all chunks.
        
        Args:
            data: List of DocumentChunk with dense embeddings
            context: Pipeline context
            
        Returns:
            List of DocumentChunk with sparse_vector populated
        """
        if not data:
            return []
        
        # Extract content for batch encoding
        contents = [chunk.content for chunk in data]
        
        self.logger.info(f"Generating sparse vectors for {len(contents)} chunks...")
        
        # Batch encode
        sparse_vectors = self.sparse_service.encode_batch(contents)
        
        # Assign sparse vectors to chunks
        for chunk, sparse_vec in zip(data, sparse_vectors):
            chunk.sparse_vector = sparse_vec
        
        # Log stats
        avg_nonzero = sum(len(sv["indices"]) for sv in sparse_vectors) / len(sparse_vectors)
        
        context["sparse_vectors_generated"] = len(sparse_vectors)
        context["avg_sparse_nonzero"] = avg_nonzero
        
        self.logger.info(f"Generated {len(sparse_vectors)} sparse vectors (avg {avg_nonzero:.0f} non-zero)")
        
        return data
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, list):
            return False
        # Check that dense vectors exist
        for chunk in data:
            if not isinstance(chunk, DocumentChunk):
                return False
            if chunk.dense_vector is None:
                self.logger.warning(f"Chunk {chunk.chunk_id} missing dense vector")
        return True
