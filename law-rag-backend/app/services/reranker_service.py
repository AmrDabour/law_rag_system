"""
Reranker Service
Qwen3-Reranker-0.6B for cross-encoder reranking
"""

from typing import List, Dict, Optional
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import logging

from app.core.config import settings
from app.utils.device import get_device, get_torch_dtype

logger = logging.getLogger(__name__)


class RerankerService:
    """
    Qwen3-Reranker-0.6B cross-encoder singleton.
    Reranks candidate documents by relevance to query.
    
    Features:
    - Cross-encoder architecture for accurate relevance scoring
    - Automatic GPU/CPU detection
    - Batch scoring for efficiency
    """
    
    _instance: Optional['RerankerService'] = None
    _model = None
    _tokenizer = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_model()
            RerankerService._initialized = True
    
    def _load_model(self):
        """Load the Qwen3 reranker model"""
        self.device = get_device()
        self.model_name = settings.RERANKER_MODEL
        self.max_length = settings.RERANKER_MAX_LENGTH
        
        logger.info(f"Loading reranker model: {self.model_name}")
        logger.info(f"Device: {self.device}")
        
        try:
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )

            # CRITICAL: Always ensure pad_token is properly set for batch processing
            # Some Qwen models have pad_token set but it doesn't work properly
            # Force set pad_token to eos_token which is known to work
            if self._tokenizer.eos_token:
                self._tokenizer.pad_token = self._tokenizer.eos_token
                self._tokenizer.pad_token_id = self._tokenizer.eos_token_id
            elif self._tokenizer.pad_token is None:
                self._tokenizer.add_special_tokens({'pad_token': '[PAD]'})

            # Set padding side (required for decoder-only models like Qwen)
            self._tokenizer.padding_side = 'left'

            logger.info(f"   pad_token: {self._tokenizer.pad_token}")
            logger.info(f"   pad_token_id: {self._tokenizer.pad_token_id}")
            logger.info(f"   padding_side: {self._tokenizer.padding_side}")

            # Load model
            dtype = get_torch_dtype(self.device)
            self._model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype=dtype,
            )

            # CRITICAL: Set pad_token_id in model config (required for batch processing)
            # The model checks its own config, not the tokenizer's pad_token_id
            if self._model.config.pad_token_id is None:
                self._model.config.pad_token_id = self._tokenizer.pad_token_id
                logger.info(f"   Set model.config.pad_token_id to: {self._model.config.pad_token_id}")

            # Move to device and set to eval
            self._model = self._model.to(self.device)
            self._model.eval()
            
            logger.info(f"✅ Reranker model loaded successfully")
            logger.info(f"   Model: {self.model_name}")
            logger.info(f"   Device: {self.device}")
            logger.info(f"   Max length: {self.max_length}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load reranker model: {e}")
            raise
    
    @property
    def model(self):
        """Get the model instance"""
        if self._model is None:
            self._load_model()
        return self._model
    
    @property
    def tokenizer(self):
        """Get the tokenizer instance"""
        if self._tokenizer is None:
            self._load_model()
        return self._tokenizer
    
    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: Optional[int] = None,
        content_key: str = "content",
    ) -> List[Dict]:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: User query
            documents: List of document dicts (must have content_key)
            top_k: Number of top documents to return (default from settings)
            content_key: Key for document content in dict
            
        Returns:
            Reranked documents with rerank_score added
        """
        if not documents:
            return []
        
        k = top_k or settings.RERANK_TOP_K
        
        # Extract content
        contents = [doc.get(content_key, "") for doc in documents]
        
        # Create query-document pairs
        pairs = [[query, content] for content in contents]
        
        # Tokenize
        inputs = self.tokenizer(
            pairs,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=self.max_length,
        ).to(self.device)
        
        # Score
        with torch.no_grad():
            logits = self.model(**inputs).logits
            # Handle different model output shapes:
            # - Single output (num_labels=1): logits shape [batch, 1] -> squeeze to [batch]
            # - Binary classification (num_labels=2): use positive class logit at index 1
            # - Multi-class: use max logit as relevance score
            if logits.shape[-1] == 1:
                scores = logits.squeeze(-1)
            elif logits.shape[-1] == 2:
                # Binary classification: use positive class logit
                scores = logits[:, 1]
            else:
                # Multi-class: use max logit as relevance score
                scores = logits.max(dim=-1).values

        # Handle single document case (0-dim tensor after squeeze)
        if len(scores.shape) == 0:
            scores = scores.unsqueeze(0)

        # Convert to list of floats
        scores_list = scores.cpu().tolist()
        
        # Add scores to documents
        scored_docs = []
        for i, doc in enumerate(documents):
            doc_copy = doc.copy()
            doc_copy["rerank_score"] = scores_list[i]
            scored_docs.append(doc_copy)
        
        # Sort by score (descending) and take top-k
        scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        return scored_docs[:k]
    
    def score_pair(self, query: str, document: str) -> float:
        """
        Score a single query-document pair.
        
        Args:
            query: User query
            document: Document text
            
        Returns:
            Relevance score
        """
        inputs = self.tokenizer(
            [[query, document]],
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=self.max_length,
        ).to(self.device)
        
        with torch.no_grad():
            logits = self.model(**inputs).logits
            # Handle different model output shapes
            if logits.shape[-1] == 1:
                score = logits.squeeze(-1)
            elif logits.shape[-1] == 2:
                # Binary classification: use positive class logit
                score = logits[:, 1]
            else:
                score = logits.max(dim=-1).values
            # Squeeze batch dimension for single pair
            score = score.squeeze()

        return float(score.cpu())
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "max_length": self.max_length,
            "top_k": settings.RERANK_TOP_K,
        }


# Singleton getter
_reranker_service: Optional[RerankerService] = None


def get_reranker_service() -> RerankerService:
    """Get reranker service singleton"""
    global _reranker_service
    if _reranker_service is None:
        _reranker_service = RerankerService()
    return _reranker_service
