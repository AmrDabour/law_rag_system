"""
Laws Routes
List and manage law collections
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.api.schemas.ingest import LawsListResponse, CollectionInfo
from app.api.deps import get_collection_factory, validate_country
from app.db.factory import CollectionFactory
from app.core.config import SupportedCountry

router = APIRouter(prefix="/api/v1", tags=["Laws"])
logger = logging.getLogger(__name__)


@router.get("/laws", response_model=LawsListResponse)
async def list_all_laws(
    factory: CollectionFactory = Depends(get_collection_factory),
) -> LawsListResponse:
    """
    List all country collections and their status.
    
    Returns information about each supported country including:
    - Collection name
    - Number of indexed documents
    - Status (active/not_initialized)
    """
    countries = factory.list_country_collections()
    
    return LawsListResponse(
        success=True,
        countries=countries,
    )


@router.get("/laws/{country}")
async def get_country_laws(
    country: str,
    factory: CollectionFactory = Depends(get_collection_factory),
):
    """
    Get detailed information about a specific country's laws.
    
    - **country**: Country code (egypt, jordan, uae, saudi, kuwait)
    """
    # Validate country
    try:
        country_enum = validate_country(country)
    except HTTPException:
        raise
    
    stats = factory.get_collection_stats(country_enum)
    
    if stats is None:
        return {
            "success": True,
            "country": country,
            "status": "not_initialized",
            "message": "No laws have been ingested for this country yet.",
            "stats": None,
        }
    
    return {
        "success": True,
        "country": country,
        "status": "active" if stats["points_count"] > 0 else "empty",
        "stats": stats,
    }


@router.delete("/laws/{country}")
async def delete_country_laws(
    country: str,
    factory: CollectionFactory = Depends(get_collection_factory),
):
    """
    Delete all laws for a country.
    
    ⚠️ WARNING: This will permanently delete all indexed laws for this country.
    
    - **country**: Country code to delete
    """
    # Validate country
    try:
        country_enum = validate_country(country)
    except HTTPException:
        raise
    
    # Check if collection exists
    stats = factory.get_collection_stats(country_enum)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No collection found for country: {country}"
        )
    
    # Delete collection
    deleted = factory.delete_country_collection(country_enum)
    
    if deleted:
        return {
            "success": True,
            "message": f"Deleted all laws for {country}",
            "collection": f"laws_{country}",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete collection"
        )


@router.post("/laws/{country}/reset")
async def reset_country_laws(
    country: str,
    factory: CollectionFactory = Depends(get_collection_factory),
):
    """
    Reset a country's collection (delete and recreate with Golden Schema).
    
    ⚠️ WARNING: This will delete all existing data and recreate the collection.
    
    - **country**: Country code to reset
    """
    # Validate country
    try:
        country_enum = validate_country(country)
    except HTTPException:
        raise
    
    # Reset collection
    collection_name = factory.reset_country_collection(country_enum)
    
    return {
        "success": True,
        "message": f"Reset collection for {country}",
        "collection": collection_name,
    }


@router.get("/laws/{country}/chunks")
async def browse_country_chunks(
    country: str,
    offset: int = 0,
    limit: int = 20,
    factory: CollectionFactory = Depends(get_collection_factory),
):
    """
    Browse chunks (documents) in a country's collection.
    
    Useful for inspecting the quality of ingested data.
    
    - **country**: Country code
    - **offset**: Starting offset for pagination
    - **limit**: Number of chunks to return (max 100)
    """
    # Validate country
    try:
        country_enum = validate_country(country)
    except HTTPException:
        raise
    
    # Limit to max 100
    limit = min(limit, 100)
    
    collection_name = factory.get_collection_name(country_enum)
    
    # Check if collection exists
    if not factory.client.collection_exists(collection_name):
        return {
            "success": True,
            "country": country,
            "chunks": [],
            "total": 0,
            "offset": offset,
            "limit": limit,
        }
    
    # Get collection info for total count
    info = factory.client.get_collection(collection_name)
    total = info.points_count
    
    # Scroll through points
    try:
        points, _ = factory.client.scroll(
            collection_name=collection_name,
            offset=offset if offset > 0 else None,
            limit=limit,
            with_payload=True,
            with_vectors=False,  # Don't return the actual vectors
        )
        
        chunks = []
        for point in points:
            payload = point.payload or {}
            chunks.append({
                "id": str(point.id),
                "law_name": payload.get("law_name", "Unknown"),
                "law_type": payload.get("law_type", "Unknown"),
                "article_number": payload.get("article_number"),
                "article_text": payload.get("article_text", ""),
                "page_number": payload.get("page_number"),
                "content": payload.get("content", "")[:500],  # First 500 chars
                "full_content": payload.get("content", ""),
                "country": payload.get("country", country),
            })
        
        return {
            "success": True,
            "country": country,
            "collection": collection_name,
            "chunks": chunks,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(chunks) < total,
        }
        
    except Exception as e:
        logger.error(f"Error browsing chunks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to browse chunks: {str(e)}"
        )
