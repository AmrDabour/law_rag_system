"""
Step 4: Reranker
Cross-encoder reranking of candidates
"""

from typing import Any, Dict, List
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.query.models import RetrievedChunk
from app.services.reranker_service import get_reranker_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class RerankerStep(PipelineStep):
    """
    Step 4: Rerank candidates using cross-encoder.
    
    Input: List[RetrievedChunk] - Top 25 candidates
    Output: List[RetrievedChunk] - Top 5 reranked
    
    Uses Qwen3-Reranker-0.6B for accurate relevance scoring.
    """
    
    def __init__(self):
        super().__init__("Reranker")
        self._reranker = None
    
    @property
    def reranker(self):
        """Lazy load reranker service"""
        if self._reranker is None:
            self._reranker = get_reranker_service()
        return self._reranker
    
    def process(self, data: List[RetrievedChunk], context: Dict[str, Any]) -> List[RetrievedChunk]:
        """
        Rerank candidates by relevance to query.
        
        Args:
            data: List of candidate chunks
            context: Pipeline context (must contain original query)
            
        Returns:
            Top K reranked chunks
        """
        if not data:
            return []
        
        query = context.get("normalized_query") or context.get("original_query", "")
        top_k = settings.RERANK_TOP_K  # 5
        
        self.logger.info(f"Reranking {len(data)} candidates to top {top_k}...")
        
        # Convert to dicts for reranker
        docs = [{"content": chunk.content, "chunk": chunk} for chunk in data]
        
        # Rerank
        reranked = self.reranker.rerank(
            query=query,
            documents=docs,
            top_k=top_k,
            content_key="content",
        )
        
        # Extract chunks with rerank scores
        result = []
        for doc in reranked:
            chunk = doc["chunk"]
            chunk.rerank_score = doc.get("rerank_score")
            result.append(chunk)
        
        context["chunks_after_rerank"] = len(result)
        
        self.logger.info(f"Reranked to {len(result)} chunks")
        
        # Log top results
        for i, chunk in enumerate(result[:3], 1):
            article_num = chunk.article_number if chunk.article_number is not None else "N/A"
            # Safely handle rerank_score - ensure it's a number
            if chunk.rerank_score is None:
                rerank_score = 0.0
            elif isinstance(chunk.rerank_score, (int, float)):
                rerank_score = float(chunk.rerank_score)
            else:
                # If it's something unexpected (like a list), convert to string
                rerank_score = 0.0
                self.logger.warning(f"Unexpected rerank_score type: {type(chunk.rerank_score)}")
            
            self.logger.debug(
                f"  #{i}: مادة {article_num} "
                f"(rerank={rerank_score:.4f})"
            )
        
        return result
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, list):
            return False
        return all(isinstance(c, RetrievedChunk) for c in data)
