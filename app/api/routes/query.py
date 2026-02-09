"""
Query Routes
Legal question answering endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.api.schemas.query import QueryRequest, QueryResponse, SourceSchema, QueryMetadata
from app.api.deps import (
    get_query_pipeline,
    get_sessions,
    get_collection_factory,
    validate_country,
)
from app.pipelines.query import QueryPipeline, QueryInput
from app.services.session_service import SessionService
from app.db.factory import CollectionFactory
from app.core.config import SupportedCountry

router = APIRouter(prefix="/api/v1", tags=["Query"])
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def query_laws(
    request: QueryRequest,
    pipeline: QueryPipeline = Depends(get_query_pipeline),
    session_service: SessionService = Depends(get_sessions),
    factory: CollectionFactory = Depends(get_collection_factory),
) -> QueryResponse:
    """
    Ask a legal question and get an answer with citations.
    
    - **question**: Your legal question in Arabic
    - **country**: Country code (egypt, jordan, uae, saudi, kuwait)
    - **law_types**: Optional filter by law types (criminal, civil, etc.)
    - **session_id**: Optional session ID for conversation history
    - **top_k**: Number of sources to retrieve (default 5)
    """
    # Validate country
    try:
        country = validate_country(request.country)
    except HTTPException:
        raise
    
    # Check collection exists
    collection_name = factory.get_collection_name(country)
    stats = factory.get_collection_stats(country)
    
    if stats is None or stats["points_count"] == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No laws found for country: {request.country}. Please ingest laws first."
        )
    
    logger.info(f"Query: '{request.question[:50]}...' -> {collection_name}")
    
    # Build query input
    query_input = QueryInput(
        question=request.question,
        country=request.country,
        law_types=request.law_types,
        session_id=request.session_id,
        top_k=request.top_k,
    )
    
    # Run query pipeline
    try:
        result = await pipeline.run(query_input)
    except Exception as e:
        logger.error(f"Query pipeline error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )
    
    # Save to session if provided
    if request.session_id:
        try:
            session_service.add_user_message(
                request.session_id,
                request.question,
                metadata={"country": request.country, "law_types": request.law_types}
            )
            session_service.add_assistant_message(
                request.session_id,
                result.answer,
                sources=[s.to_dict() for s in result.sources],
            )
        except Exception as e:
            logger.warning(f"Failed to save to session: {e}")
    
    # Convert to response schema
    sources = [
        SourceSchema(
            law_name=s.law_name,
            article_number=s.article_number,
            article_text=s.article_text,
            page_number=s.page_number,
            relevance_score=s.relevance_score,
            content_preview=s.content_preview,
        )
        for s in result.sources
    ]
    
    metadata = QueryMetadata(
        query_time_ms=result.query_time_ms,
        chunks_retrieved=result.chunks_retrieved,
        chunks_after_rerank=result.chunks_after_rerank,
        embedding_model=result.embedding_model,
        reranker_model=result.reranker_model,
        llm_model=result.llm_model,
    )
    
    return QueryResponse(
        success=result.success,
        answer=result.answer,
        sources=sources,
        metadata=metadata,
        errors=result.errors,
    )
