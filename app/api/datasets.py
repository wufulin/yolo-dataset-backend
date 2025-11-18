"""Dataset management API endpoints."""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query, Depends
from app.auth import authenticate_user
from app.schemas.dataset import (
    DatasetResponse, ImageResponse, PaginatedResponse, DatasetCreate
)
from app.services.mongo_service import mongo_service
from app.services.minio_service import minio_service


router = APIRouter()


@router.get("/datasets", response_model=PaginatedResponse)
async def list_datasets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    username: str = Depends(authenticate_user)
):
    """
    List all datasets with pagination.
    
    Args:
        page: Page number (starting from 1)
        page_size: Number of items per page
        
    Returns:
        PaginatedResponse: Paginated list of datasets
    """
    skip = (page - 1) * page_size
    
    datasets = mongo_service.list_datasets(skip=skip, limit=page_size)
    
    total = mongo_service.datasets.count_documents({})

    return PaginatedResponse(
        items=datasets,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    username: str = Depends(authenticate_user)
):
    """
    Get dataset by ID.
    
    Args:
        dataset_id: Dataset ID
        
    Returns:
        DatasetResponse: Dataset information
    """
    dataset = mongo_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    return DatasetResponse(**dataset)


@router.get("/datasets/{dataset_id}/images", response_model=PaginatedResponse)
async def get_dataset_images(
    dataset_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    split: Optional[str] = Query(None, description="Filter by split"),
    username: str = Depends(authenticate_user)
):
    """
    Get images for a specific dataset.
    
    Args:
        dataset_id: Dataset ID
        page: Page number
        page_size: Page size
        split: Optional split filter
        
    Returns:
        PaginatedResponse: Paginated list of images
    """
    # Verify dataset exists
    dataset = mongo_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    skip = (page - 1) * page_size
    images = mongo_service.get_images_by_dataset(
        dataset_id, skip=skip, limit=page_size, split=split
    )
    
    # Generate presigned URLs for images
    for image in images:
        image["file_url"] = minio_service.get_file_url(image["file_path"])
    
    total = mongo_service.count_images(dataset_id, split=split)
    
    return PaginatedResponse(
        items=images,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/images/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: str,
    username: str = Depends(authenticate_user)
):
    """
    Get image by ID with annotations.
    
    Args:
        image_id: Image ID
        
    Returns:
        ImageResponse: Image information with annotations
    """
    image = mongo_service.get_image(image_id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Generate presigned URL
    image["file_url"] = minio_service.get_file_url(image["file_path"])
    
    return ImageResponse(**image)


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    username: str = Depends(authenticate_user)
):
    """
    Delete dataset and all associated images.
    
    Args:
        dataset_id: Dataset ID
        
    Returns:
        dict: Deletion status
    """
    # Verify dataset exists
    dataset = mongo_service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Delete from MongoDB and MinIO
    success = mongo_service.delete_dataset(dataset_id)
    
    if success:
        return {"status": "success", "message": "Dataset deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset"
        )