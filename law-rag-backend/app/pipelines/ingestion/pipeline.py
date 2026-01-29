"""
Ingestion Pipeline
7-step pipeline for processing and indexing legal documents
"""

from typing import Dict, Any, Optional
import time
import logging

from app.pipelines.base import Pipeline
from app.pipelines.ingestion.models import (
    IngestionInput, 
    IngestionOutput, 
    ArticleMetadata
)
from app.pipelines.ingestion.steps import (
    PDFLoaderStep,
    TextExtractorStep,
    ArticleSplitterStep,
    MetadataEnricherStep,
    DenseEmbedderStep,
    SparseEncoderStep,
    QdrantStorerStep,
)

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    7-Step Ingestion Pipeline for Legal Documents.
    
    Steps:
    1. PDF Loader - Load PDF from bytes
    2. Text Extractor - Extract Arabic text from pages
    3. Article Splitter - Split by مادة (article) boundaries
    4. Metadata Enricher - Add metadata and create chunks
    5. Dense Embedder - Generate Qwen3 embeddings
    6. Sparse Encoder - Generate BM25 sparse vectors
    7. Qdrant Storer - Store with dual vectors
    """
    
    def __init__(self):
        """Initialize the ingestion pipeline"""
        self.pipeline = self._build_pipeline()
    
    def _build_pipeline(self) -> Pipeline:
        """Build the 7-step pipeline"""
        pipeline = Pipeline("Legal Document Ingestion")
        
        # Add all steps
        pipeline.add_step(PDFLoaderStep())       # Step 1
        pipeline.add_step(TextExtractorStep())   # Step 2
        pipeline.add_step(ArticleSplitterStep()) # Step 3
        pipeline.add_step(MetadataEnricherStep())# Step 4
        pipeline.add_step(DenseEmbedderStep())   # Step 5
        pipeline.add_step(SparseEncoderStep())   # Step 6
        pipeline.add_step(QdrantStorerStep())    # Step 7
        
        return pipeline
    
    async def run(
        self,
        pdf_content: bytes,
        filename: str,
        collection_name: str,
        metadata: Dict[str, Any],
    ) -> IngestionOutput:
        """
        Run the ingestion pipeline.
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Original filename
            collection_name: Target Qdrant collection
            metadata: Document metadata dict
            
        Returns:
            IngestionOutput with results
        """
        start_time = time.time()
        
        # Build ArticleMetadata from dict
        article_metadata = ArticleMetadata(
            country=metadata.get("country", "unknown"),
            law_type=metadata.get("law_type", "unknown"),
            law_name=metadata.get("law_name", ""),
            law_name_en=metadata.get("law_name_en"),
            law_number=metadata.get("law_number"),
            law_year=metadata.get("law_year"),
            source_file=filename,
        )
        
        # Build context
        context = {
            "collection_name": collection_name,
            "metadata": article_metadata,
            "filename": filename,
        }
        
        logger.info(f"Starting ingestion: {filename} -> {collection_name}")
        
        # Run pipeline (synchronous but wrapped for async context)
        result = self.pipeline.run(pdf_content, context)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Build output
        return IngestionOutput(
            success=result.success,
            collection_name=collection_name,
            articles_count=context.get("articles_found", 0),
            chunks_count=context.get("chunks_created", 0),
            duration_ms=duration_ms,
            errors=result.errors,
            pages_processed=context.get("pages_with_text", 0),
        )


def create_ingestion_pipeline() -> IngestionPipeline:
    """Factory function to create ingestion pipeline"""
    return IngestionPipeline()
