"""
Sparse Encoder Service
FastEmbed BM25 for sparse vector generation (keyword matching)
"""

from typing import List, Dict, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SparseEncoderService:
    """
    FastEmbed BM25 sparse encoder singleton.
    Generates sparse vectors for keyword-based retrieval.
    
    Features:
    - BM25 sparse encoding for keyword matching
    - Complements dense embeddings in hybrid search
    - CPU-based (fast enough, no GPU needed)
    """
    
    _instance: Optional['SparseEncoderService'] = None
    _model = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_model()
            SparseEncoderService._initialized = True
    
    def _load_model(self):
        """Load the BM25 sparse encoder"""
        self.model_name = settings.SPARSE_MODEL
        
        logger.info(f"Loading sparse encoder: {self.model_name}")
        
        try:
            from fastembed import SparseTextEmbedding
            
            self._model = SparseTextEmbedding(model_name=self.model_name)
            
            logger.info(f"✅ Sparse encoder loaded successfully")
            logger.info(f"   Model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load sparse encoder: {e}")
            raise
    
    @property
    def model(self):
        """Get the model instance"""
        if self._model is None:
            self._load_model()
        return self._model
    
    def encode(self, text: str) -> Dict[str, List]:
        """
        Encode single text to sparse vector.
        
        Args:
            text: Input text
            
        Returns:
            Dict with 'indices' and 'values' lists
        """
        embeddings = list(self.model.embed([text]))
        
        if embeddings:
            return {
                "indices": embeddings[0].indices.tolist(),
                "values": embeddings[0].values.tolist(),
            }
        
        return {"indices": [], "values": []}
    
    def encode_batch(self, texts: List[str]) -> List[Dict[str, List]]:
        """
        Encode multiple texts to sparse vectors.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of sparse vector dicts
        """
        if not texts:
            return []
        
        embeddings = list(self.model.embed(texts))
        
        return [
            {
                "indices": emb.indices.tolist(),
                "values": emb.values.tolist(),
            }
            for emb in embeddings
        ]
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "type": "sparse",
            "method": "BM25",
        }


# Singleton getter
_sparse_encoder_service: Optional[SparseEncoderService] = None


def get_sparse_encoder_service() -> SparseEncoderService:
    """Get sparse encoder service singleton"""
    global _sparse_encoder_service
    if _sparse_encoder_service is None:
        _sparse_encoder_service = SparseEncoderService()
    return _sparse_encoder_service
