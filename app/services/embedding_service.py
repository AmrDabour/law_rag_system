"""
Embedding Service
Qwen3-Embedding-0.6B for dense vector generation
"""

from typing import List, Optional
import torch
from sentence_transformers import SentenceTransformer
import logging

from app.core.config import settings
from app.utils.device import get_device, get_torch_dtype

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Qwen3-Embedding-0.6B singleton service.
    Generates 1024-dimensional dense vectors for semantic search.
    
    Features:
    - Automatic GPU/CPU detection
    - Singleton pattern for memory efficiency
    - Batch encoding support
    """
    
    _instance: Optional['EmbeddingService'] = None
    _model: Optional[SentenceTransformer] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_model()
            EmbeddingService._initialized = True
    
    def _load_model(self):
        """Load the Qwen3 embedding model"""
        self.device = get_device()
        self.model_name = settings.EMBEDDING_MODEL
        
        logger.info(f"Loading embedding model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        
        try:
            self._model = SentenceTransformer(
                self.model_name,
                trust_remote_code=True,
                device=self.device,
            )
            
            # Set to evaluation mode
            self._model.eval()
            
            # Get actual dimension
            self.dimension = self._model.get_sentence_embedding_dimension()
            
            logger.info(f"✅ Embedding model loaded successfully")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Dimension: {self.dimension}")
            logger.info(f"   Device: {self.device}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise
    
    @property
    def model(self) -> SentenceTransformer:
        """Get the model instance"""
        if self._model is None:
            self._load_model()
        return self._model
    
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            List of floats (1024-dimensional vector)
        """
        with torch.no_grad():
            embedding = self.model.encode(
                text,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        return embedding.tolist()
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size (default from settings)
            show_progress: Show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        bs = batch_size or settings.EMBEDDING_BATCH_SIZE
        total = len(texts)
        
        logger.info(f"📊 Embedding {total} chunks (batch_size={bs})...")
        
        with torch.no_grad():
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=bs,
                show_progress_bar=True,  # Always show progress
                convert_to_numpy=True,
            )
        
        logger.info(f"✅ Embedded {total} chunks successfully")
        return embeddings.tolist()
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "device": self.device,
            "batch_size": settings.EMBEDDING_BATCH_SIZE,
        }


# Singleton getter
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get embedding service singleton"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
