"""
Step 3: Hybrid Retriever
Perform hybrid search with RRF fusion
"""

from typing import Any, Dict, List, Optional
import logging

from qdrant_client import models

from app.pipelines.base import PipelineStep
from app.pipelines.query.models import RetrievedChunk
from app.db.qdrant_client import get_qdrant_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


class HybridRetrieverStep(PipelineStep):
    """
    Step 3: Hybrid search with RRF fusion.
    
    Input: Dict with query, dense_vector, sparse_vector
    Output: List[RetrievedChunk] - Top 25 candidates
    
    Strategy:
    1. Prefetch dense search (semantic) -> Top 25
    2. Prefetch sparse search (keywords) -> Top 25
    3. Fuse with Reciprocal Rank Fusion (RRF)
    4. Return unique Top 25
    """
    
    def __init__(self):
        super().__init__("Hybrid Retriever")
        self._qdrant = None
    
    @property
    def qdrant(self):
        """Lazy load Qdrant manager"""
        if self._qdrant is None:
            self._qdrant = get_qdrant_manager()
        return self._qdrant
    
    def process(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[RetrievedChunk]:
        """
        Perform hybrid search.
        
        Args:
            data: Dict with dense_vector and sparse_vector
            context: Pipeline context (must contain collection_name)
            
        Returns:
            List of RetrievedChunk candidates
        """
        collection_name = context.get("collection_name")
        if not collection_name:
            raise ValueError("collection_name not found in context")
        
        dense_vector = data["dense_vector"]
        sparse_vector = data["sparse_vector"]
        
        # Build filter from context
        filter_conditions = self._build_filter(context)
        
        limit = settings.HYBRID_PREFETCH_LIMIT  # 25
        
        self.logger.info(f"Hybrid search in {collection_name} (limit={limit})")
        
        # Perform hybrid search with RRF fusion
        results = self.qdrant.hybrid_search(
            collection_name=collection_name,
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            filter_conditions=filter_conditions,
            limit=limit,
        )
        
        # Convert to RetrievedChunk objects
        chunks = [
            RetrievedChunk.from_qdrant_result(r)
            for r in results
        ]
        
        context["chunks_retrieved"] = len(chunks)
        self.logger.info(f"Retrieved {len(chunks)} candidates")
        
        return chunks
    
    def _build_filter(self, context: Dict[str, Any]) -> Optional[models.Filter]:
        """Build Qdrant filter from context"""
        conditions = []
        
        # Filter by country
        country = context.get("country")
        if country:
            conditions.append(
                models.FieldCondition(
                    key="country",
                    match=models.MatchValue(value=country),
                )
            )
        
        # Filter by law types
        law_types = context.get("law_types")
        if law_types and isinstance(law_types, list):
            conditions.append(
                models.FieldCondition(
                    key="law_type",
                    match=models.MatchAny(any=law_types),
                )
            )
        
        if conditions:
            return models.Filter(must=conditions)
        
        return None
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, dict):
            return False
        if "dense_vector" not in data or "sparse_vector" not in data:
            self.logger.error("Missing dense_vector or sparse_vector")
            return False
        return True
