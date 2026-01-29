"""
Ingest Routes
Law document ingestion endpoint
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
import logging

from app.api.schemas.ingest import IngestResponse
from app.api.deps import (
    get_ingestion_pipeline,
    get_collection_factory,
    validate_country,
)
from app.pipelines.ingestion import IngestionPipeline
from app.db.factory import CollectionFactory
from app.core.config import SupportedCountry

router = APIRouter(prefix="/api/v1", tags=["Ingest"])
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_law(
    file: UploadFile = File(..., description="PDF file to ingest"),
    country: str = Form(..., description="Country code"),
    law_type: str = Form(..., description="Type of law"),
    law_name: str = Form(..., description="Arabic name of the law"),
    law_name_en: str = Form("", description="English name of the law"),
    law_number: str = Form("", description="Law number"),
    law_year: str = Form("", description="Law year"),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
    factory: CollectionFactory = Depends(get_collection_factory),
) -> IngestResponse:
    """
    Ingest a law PDF document.
    
    The PDF will be processed through the 7-step ingestion pipeline:
    1. Load PDF
    2. Extract text
    3. Split by articles (مادة)
    4. Enrich metadata
    5. Generate dense embeddings
    6. Generate sparse vectors
    7. Store in Qdrant
    
    - **file**: PDF file to upload
    - **country**: Country code (egypt, jordan, uae, saudi, kuwait)
    - **law_type**: Type of law (criminal, civil, commercial, economic, etc.)
    - **law_name**: Arabic name of the law (e.g., قانون العقوبات)
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported"
        )
    
    # Validate country
    try:
        country_enum = validate_country(country)
    except HTTPException:
        raise
    
    # Ensure collection exists with Golden Schema
    collection_name = factory.ensure_country_collection(country_enum)
    
    logger.info(f"Ingesting {file.filename} to {collection_name}")
    
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )
    
    if len(content) < 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too small to be a valid PDF"
        )
    
    # Build metadata
    metadata = {
        "country": country,
        "law_type": law_type,
        "law_name": law_name,
        "law_name_en": law_name_en or None,
        "law_number": law_number or None,
        "law_year": law_year or None,
    }
    
    # Run ingestion pipeline
    try:
        result = await pipeline.run(
            pdf_content=content,
            filename=file.filename,
            collection_name=collection_name,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {', '.join(result.errors)}"
        )
    
    return IngestResponse(
        success=True,
        message=f"Law '{law_name}' ingested successfully",
        collection=collection_name,
        articles_found=result.articles_count,
        chunks_created=result.chunks_count,
        processing_time_ms=result.duration_ms,
        pages_processed=result.pages_processed,
        errors=result.errors,
    )
