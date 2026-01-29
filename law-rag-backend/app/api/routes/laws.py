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
