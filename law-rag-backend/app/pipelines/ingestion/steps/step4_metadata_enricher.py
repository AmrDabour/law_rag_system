"""
Step 4: Metadata Enricher
Add metadata to articles and create DocumentChunks
"""

from typing import Any, Dict, List
import hashlib
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import RawArticle, DocumentChunk, ArticleMetadata
from app.utils.arabic import ArabicNumerals
from app.core.config import settings

logger = logging.getLogger(__name__)


class MetadataEnricherStep(PipelineStep):
    """
    Step 4: Enrich articles with metadata and create DocumentChunks.
    
    Input: List[RawArticle]
    Output: List[DocumentChunk]
    
    This step:
    - Generates unique chunk IDs
    - Handles long articles (splits into parts)
    - Adds all metadata fields
    """
    
    def __init__(self):
        super().__init__("Metadata Enricher")
    
    def process(self, data: List[RawArticle], context: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Create DocumentChunks from RawArticles.
        
        Args:
            data: List of RawArticle
            context: Pipeline context (must contain 'metadata')
            
        Returns:
            List of DocumentChunk
        """
        metadata: ArticleMetadata = context.get("metadata")
        if not metadata:
            raise ValueError("Metadata not found in context")
        
        chunks = []
        
        for article in data:
            # Check if article needs splitting
            article_chunks = self._process_article(article, metadata)
            chunks.extend(article_chunks)
        
        context["chunks_created"] = len(chunks)
        self.logger.info(f"Created {len(chunks)} chunks from {len(data)} articles")
        
        return chunks
    
    def _process_article(
        self,
        article: RawArticle,
        metadata: ArticleMetadata,
    ) -> List[DocumentChunk]:
        """
        Process a single article, splitting if needed.
        
        Args:
            article: RawArticle to process
            metadata: Article metadata
            
        Returns:
            List of DocumentChunk (usually 1, more if split)
        """
        content = article.content
        
        # Estimate token count (rough: ~1.5 chars per token for Arabic)
        estimated_tokens = len(content) / 1.5
        
        # Check if needs splitting
        if estimated_tokens > settings.MAX_CHUNK_TOKENS:
            return self._split_long_article(article, metadata)
        
        # Single chunk
        chunk_id = self._generate_chunk_id(
            metadata.country,
            metadata.law_type,
            article.article_number,
            1
        )
        
        return [DocumentChunk(
            chunk_id=chunk_id,
            content=content,
            article_number=article.article_number,
            article_text=article.article_text,
            page_number=article.page_number,
            country=metadata.country,
            law_type=metadata.law_type,
            law_name=metadata.law_name,
            law_name_en=metadata.law_name_en,
            law_number=metadata.law_number,
            law_year=metadata.law_year,
            source_file=metadata.source_file,
            chapter=article.chapter,
            chunk_part=1,
            total_parts=1,
        )]
    
    def _split_long_article(
        self,
        article: RawArticle,
        metadata: ArticleMetadata,
    ) -> List[DocumentChunk]:
        """
        Split a long article into multiple chunks.
        
        Args:
            article: Long article to split
            metadata: Article metadata
            
        Returns:
            List of DocumentChunk parts
        """
        content = article.content
        
        # Split by paragraphs
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = ""
        current_part = 1
        
        for para in paragraphs:
            # Check if adding this paragraph exceeds limit
            test_chunk = current_chunk + "\n\n" + para if current_chunk else para
            estimated_tokens = len(test_chunk) / 1.5
            
            if estimated_tokens > settings.MAX_CHUNK_TOKENS and current_chunk:
                # Save current chunk
                chunks.append(current_chunk)
                current_chunk = para
            else:
                current_chunk = test_chunk
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        # Create DocumentChunks
        total_parts = len(chunks)
        result = []
        
        for i, chunk_content in enumerate(chunks, 1):
            chunk_id = self._generate_chunk_id(
                metadata.country,
                metadata.law_type,
                article.article_number,
                i
            )
            
            # Add part indicator to content
            part_indicator = f"[مادة {article.article_number} - جزء {ArabicNumerals.to_arabic(str(i))} من {ArabicNumerals.to_arabic(str(total_parts))}]\n\n"
            
            result.append(DocumentChunk(
                chunk_id=chunk_id,
                content=part_indicator + chunk_content if i > 1 else chunk_content,
                article_number=article.article_number,
                article_text=article.article_text,
                page_number=article.page_number,
                country=metadata.country,
                law_type=metadata.law_type,
                law_name=metadata.law_name,
                law_name_en=metadata.law_name_en,
                law_number=metadata.law_number,
                law_year=metadata.law_year,
                source_file=metadata.source_file,
                chapter=article.chapter,
                chunk_part=i,
                total_parts=total_parts,
            ))
        
        self.logger.debug(f"Split article {article.article_number} into {total_parts} parts")
        
        return result
    
    def _generate_chunk_id(
        self,
        country: str,
        law_type: str,
        article_number: int,
        part: int,
    ) -> str:
        """
        Generate unique chunk ID as UUID (required by Qdrant).
        
        Uses UUID5 with namespace based on content for deterministic IDs.
        """
        import uuid
        
        # Create a deterministic UUID based on content
        base = f"{country}_{law_type}_art{article_number or 0}_p{part}_{id(self)}"
        
        # UUID5 creates deterministic UUID from namespace + name
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, base))
    
    def validate_input(self, data: Any) -> bool:
        """Validate input"""
        if not isinstance(data, list):
            return False
        return all(isinstance(a, RawArticle) for a in data)
