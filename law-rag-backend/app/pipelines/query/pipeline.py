"""
Query Pipeline
6-step pipeline for answering legal questions
"""

from typing import Dict, Any, Optional, List
import time
import logging

from app.pipelines.base import Pipeline, PipelineStep
from app.pipelines.query.models import QueryInput, QueryOutput, RetrievedChunk
from app.pipelines.query.steps import (
    PreprocessorStep,
    DualEncoderStep,
    HybridRetrieverStep,
    RerankerStep,
    GeneratorStep,
    FormatterStep,
)
from app.core.config import SupportedCountry

logger = logging.getLogger(__name__)


class CombineForFormatterStep(PipelineStep):
    """Helper step to combine answer and chunks for formatter"""
    
    def __init__(self):
        super().__init__("Combine for Formatter")
    
    def process(self, data: str, context: Dict[str, Any]) -> tuple:
        """Combine answer with chunks from context"""
        chunks = context.get("reranked_chunks", [])
        return (data, chunks)


class QueryPipeline:
    """
    6-Step Query Pipeline for Legal Questions.
    
    Steps:
    1. Preprocessor - Normalize Arabic query
    2. Dual Encoder - Generate dense + sparse vectors
    3. Hybrid Retriever - RRF fusion search -> Top 25
    4. Reranker - Cross-encoder rerank -> Top 5
    5. Generator - Gemini answer with citations
    6. Formatter - Format response with sources
    """
    
    def __init__(self):
        """Initialize the query pipeline"""
        self.pipeline = self._build_pipeline()
    
    def _build_pipeline(self) -> Pipeline:
        """Build the 6-step pipeline"""
        pipeline = Pipeline("Legal Query")
        
        # Add all steps
        pipeline.add_step(PreprocessorStep())      # Step 1
        pipeline.add_step(DualEncoderStep())       # Step 2
        pipeline.add_step(HybridRetrieverStep())   # Step 3
        pipeline.add_step(RerankerStep())          # Step 4
        pipeline.add_step(GeneratorStep())         # Step 5
        
        return pipeline
    
    async def run(self, query_input: QueryInput) -> QueryOutput:
        """
        Run the query pipeline.
        
        Args:
            query_input: QueryInput with question and filters
            
        Returns:
            QueryOutput with answer and sources
        """
        start_time = time.time()
        
        # Build collection name from country
        collection_name = f"laws_{query_input.country}"
        
        # Build context
        context = {
            "collection_name": collection_name,
            "country": query_input.country,
            "law_types": query_input.law_types,
            "session_id": query_input.session_id,
            "top_k": query_input.top_k,
        }
        
        logger.info(f"Query pipeline: '{query_input.question[:50]}...' -> {collection_name}")
        
        # Run first 4 steps to get reranked chunks
        # Step 1: Preprocess
        preprocessor = PreprocessorStep()
        normalized_query = preprocessor.process(query_input.question, context)
        
        # Step 2: Dual Encode
        dual_encoder = DualEncoderStep()
        encoded = dual_encoder.process(normalized_query, context)
        
        # Step 3: Hybrid Retrieve
        retriever = HybridRetrieverStep()
        candidates = retriever.process(encoded, context)
        
        # Step 4: Rerank
        reranker = RerankerStep()
        reranked = reranker.process(candidates, context)
        
        # Store reranked for formatter
        context["reranked_chunks"] = reranked
        
        # Step 5: Generate
        generator = GeneratorStep()
        answer = generator.process(reranked, context)
        
        # Step 6: Format
        formatter = FormatterStep()
        query_time_ms = (time.time() - start_time) * 1000
        context["query_time_ms"] = query_time_ms
        
        output = formatter.process((answer, reranked), context)
        
        logger.info(f"Query completed in {query_time_ms:.0f}ms")
        
        return output
    
    def run_sync(self, query_input: QueryInput) -> QueryOutput:
        """Synchronous version of run"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.run(query_input))


def create_query_pipeline() -> QueryPipeline:
    """Factory function to create query pipeline"""
    return QueryPipeline()
