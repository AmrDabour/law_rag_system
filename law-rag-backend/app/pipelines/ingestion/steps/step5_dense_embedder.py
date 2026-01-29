"""
Step 5: Dense Embedder
Generate Qwen3 dense embeddings for chunks
"""

from typing import Any, Dict, List
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import DocumentChunk
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class DenseEmbedderStep(PipelineStep):
    """
    Step 5: Generate dense embeddings using Qwen3-Embedding-0.6B.
    
    Input: List[DocumentChunk] without embeddings
    Output: List[DocumentChunk] with dense_vector populated
    """
    
    def __init__(self):
        super().__init__("Dense Embedder")
        self._embedding_service = None
    
    @property
    def embedding_service(self):
        """Lazy load embedding service"""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    def process(self, data: List[DocumentChunk], context: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Generate dense embeddings for all chunks.
        
        Args:
            data: List of DocumentChunk
            context: Pipeline context
            
        Returns:
            List of DocumentChunk with dense_vector populated
        """
        if not data:
            return []
        
        # Extract content for batch embedding
        contents = [chunk.content for chunk in data]
        total = len(contents)
        
        self.logger.info(f"📊 Generating dense embeddings for {total} chunks...")
        print(f"\n🔄 Dense Embedding Progress ({total} chunks):")
        
        # Batch embed - always show progress
        embeddings = self.embedding_service.embed_batch(
            contents,
            show_progress=True,  # Always show progress
        )
        
        # Assign embeddings to chunks
        for chunk, embedding in zip(data, embeddings):
            chunk.dense_vector = embedding
        
        context["dense_embeddings_generated"] = len(embeddings)
        self.logger.info(f"Generated {len(embeddings)} dense embeddings ({self.embedding_service.dimension}D)")
        
        return data
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, list):
            return False
        return all(isinstance(c, DocumentChunk) for c in data)
