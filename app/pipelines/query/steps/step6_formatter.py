"""
Step 6: Response Formatter
Format final response with sources
"""

from typing import Any, Dict, List, Tuple
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.query.models import RetrievedChunk, Source, QueryOutput
from app.core.config import settings

logger = logging.getLogger(__name__)


class FormatterStep(PipelineStep):
    """
    Step 6: Format final response.
    
    Input: Tuple[str, List[RetrievedChunk]] - (answer, chunks)
    Output: QueryOutput
    """
    
    def __init__(self):
        super().__init__("Response Formatter")
    
    def process(self, data: Tuple[str, List[RetrievedChunk]], context: Dict[str, Any]) -> QueryOutput:
        """
        Format the final response.
        
        Args:
            data: Tuple of (answer string, reranked chunks)
            context: Pipeline context
            
        Returns:
            QueryOutput object
        """
        answer, chunks = data
        
        # Create sources from chunks
        sources = self._create_sources(chunks)
        
        # Get timing from context
        query_time_ms = context.get("query_time_ms", 0)
        # Ensure it's a number, not a list or other type
        if isinstance(query_time_ms, (int, float)):
            query_time_ms = float(query_time_ms)
        elif isinstance(query_time_ms, (list, tuple)) and len(query_time_ms) > 0:
            # If it's a list/tuple, try to get the first element
            query_time_ms = float(query_time_ms[0]) if isinstance(query_time_ms[0], (int, float)) else 0.0
        else:
            # For any other type, default to 0.0
            query_time_ms = 0.0
        
        # Build output
        output = QueryOutput(
            success=True,
            answer=answer,
            sources=sources,
            query_time_ms=query_time_ms,
            chunks_retrieved=context.get("chunks_retrieved", 0),
            chunks_after_rerank=context.get("chunks_after_rerank", len(chunks)),
            embedding_model=settings.EMBEDDING_MODEL,
            reranker_model=settings.RERANKER_MODEL,
            llm_model=settings.LLM_MODEL,
        )
        
        self.logger.info(f"Formatted response with {len(sources)} sources")
        
        return output
    
    def _create_sources(self, chunks: List[RetrievedChunk]) -> List[Source]:
        """Create Source objects from chunks"""
        sources = []
        
        for chunk in chunks:
            # Create content preview (first 200 chars)
            preview = chunk.content[:200]
            if len(chunk.content) > 200:
                preview += "..."
            
            # Use rerank score if available, else hybrid score
            score = chunk.rerank_score if chunk.rerank_score is not None else chunk.hybrid_score
            
            sources.append(Source(
                law_name=chunk.law_name,
                article_number=chunk.article_number,
                article_text=chunk.article_text,
                page_number=chunk.page_number,
                relevance_score=score,
                content_preview=preview,
            ))
        
        return sources
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, tuple) or len(data) != 2:
            return False
        answer, chunks = data
        return isinstance(answer, str) and isinstance(chunks, list)
