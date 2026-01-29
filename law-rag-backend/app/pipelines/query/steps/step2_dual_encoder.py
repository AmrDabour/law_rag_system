"""
Step 2: Dual Encoder
Generate both dense and sparse vectors for query
"""

from typing import Any, Dict
import logging

from app.pipelines.base import PipelineStep
from app.services.embedding_service import get_embedding_service
from app.services.sparse_encoder_service import get_sparse_encoder_service

logger = logging.getLogger(__name__)


class DualEncoderStep(PipelineStep):
    """
    Step 2: Encode query to both dense and sparse vectors.
    
    Input: str (normalized query)
    Output: Dict with 'dense_vector' and 'sparse_vector'
    """
    
    def __init__(self):
        super().__init__("Dual Encoder")
        self._embedding_service = None
        self._sparse_service = None
    
    @property
    def embedding_service(self):
        """Lazy load embedding service"""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    @property
    def sparse_service(self):
        """Lazy load sparse encoder service"""
        if self._sparse_service is None:
            self._sparse_service = get_sparse_encoder_service()
        return self._sparse_service
    
    def process(self, data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encode query to dual vectors.
        
        Args:
            data: Normalized query string
            context: Pipeline context
            
        Returns:
            Dict with dense_vector and sparse_vector
        """
        self.logger.info("Generating dual vectors for query...")
        
        # Generate dense vector (semantic)
        dense_vector = self.embedding_service.embed(data)
        
        # Generate sparse vector (keywords)
        sparse_vector = self.sparse_service.encode(data)
        
        # Store in context for later steps
        context["dense_vector"] = dense_vector
        context["sparse_vector"] = sparse_vector
        
        self.logger.info(
            f"Encoded query: dense={len(dense_vector)}D, "
            f"sparse={len(sparse_vector['indices'])} non-zero"
        )
        
        return {
            "query": data,
            "dense_vector": dense_vector,
            "sparse_vector": sparse_vector,
        }
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        return isinstance(data, str) and len(data) > 0
