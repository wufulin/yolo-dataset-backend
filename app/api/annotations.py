"""Annotation management API endpoints."""
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import authenticate_user
from app.schemas.annotation import AnnotationResponse, AnnotationUpdate, PaginatedAnnotationsResponse
from app.services.annotation_service import annotation_service
from app.services.dataset_service import dataset_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/annotations", response_model=PaginatedAnnotationsResponse)
async def list_annotations(
    dataset_id: Optional[str] = Query(None, description="Filter by dataset ID"),
    image_id: Optional[str] = Query(None, description="Filter by image ID"),
    class_name: Optional[str] = Query(None, description="Filter by class name"),
    annotation_type: Optional[str] = Query(None, description="Filter by annotation type"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence"),
    max_confidence: Optional[float] = Query(None, ge=0, le=1, description="Maximum confidence"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    username: str = Depends(authenticate_user)
):
    """
    List annotations with filtering and pagination.
    
    Args:
        dataset_id: Filter by dataset ID
        image_id: Filter by image ID
        class_name: Filter by class name
        annotation_type: Filter by annotation type
        min_confidence: Minimum confidence threshold
        max_confidence: Maximum confidence threshold
        page: Page number
        page_size: Page size
        
    Returns:
        PaginatedAnnotationsResponse: Paginated list of annotations
    """
    logger.info(f"Listing annotations with filters: dataset_id={dataset_id}, image_id={image_id}, class_name={class_name}")
    
    # Build filter criteria
    filter_criteria = {}
    if dataset_id:
        filter_criteria["dataset_id"] = ObjectId(dataset_id)
    if image_id:
        filter_criteria["image_id"] = ObjectId(image_id)
    if class_name:
        filter_criteria["class_name"] = class_name
    if annotation_type:
        filter_criteria["annotation_type"] = annotation_type
    if min_confidence is not None or max_confidence is not None:
        filter_criteria["confidence"] = {}
        if min_confidence is not None:
            filter_criteria["confidence"]["$gte"] = min_confidence
        if max_confidence is not None:
            filter_criteria["confidence"]["$lte"] = max_confidence
    
    try:
        annotations, total = annotation_service.get_annotations_with_filter(
            filter_criteria=filter_criteria,
            skip=(page - 1) * page_size,
            limit=page_size
        )
        
        logger.info(f"Retrieved {len(annotations)} annotations (total: {total})")
        return PaginatedAnnotationsResponse(
            items=annotations,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch annotations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch annotations: {str(e)}"
        )


@router.get("/annotations/{annotation_id}", response_model=AnnotationResponse)
async def get_annotation(
    annotation_id: str,
    username: str = Depends(authenticate_user)
):
    """
    Get annotation by ID.
    
    Args:
        annotation_id: Annotation ID
        
    Returns:
        AnnotationResponse: Annotation details
    """
    logger.info(f"Retrieving annotation with ID: {annotation_id}")
    
    try:
        annotation = annotation_service.get_annotation(annotation_id)
        if not annotation:
            logger.error(f"Annotation not found with ID: {annotation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation not found"
            )
        
        logger.info(f"Retrieved annotation {annotation_id}")
        return AnnotationResponse(**annotation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve annotation: {str(e)}"
        )


@router.get("/datasets/{dataset_id}/annotations/stats")
async def get_dataset_annotation_stats(
    dataset_id: str,
    username: str = Depends(authenticate_user)
):
    """
    Get annotation statistics for a dataset.
    
    Args:
        dataset_id: Dataset ID
        
    Returns:
        dict: Annotation statistics
    """
    logger.info(f"Getting annotation stats for dataset {dataset_id}")
    
    try:
        # Verify dataset exists
        dataset = dataset_service.get_dataset(dataset_id)
        if not dataset:
            logger.error(f"Dataset not found with ID: {dataset_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )
        
        stats = annotation_service.get_dataset_annotation_stats(dataset_id)
        logger.info(f"Retrieved annotation stats for dataset {dataset_id}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get annotation stats for dataset {dataset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get annotation stats: {str(e)}"
        )


@router.get("/images/{image_id}/annotations")
async def get_image_annotations(
    image_id: str,
    username: str = Depends(authenticate_user)
):
    """
    Get all annotations for a specific image.
    
    Args:
        image_id: Image ID
        
    Returns:
        List[AnnotationResponse]: List of annotations for the image
    """
    logger.info(f"Getting annotations for image {image_id}")
    
    try:
        # Verify image exists
        image = dataset_service.get_image(image_id)
        if not image:
            logger.error(f"Image not found with ID: {image_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
        
        annotations = annotation_service.get_annotations_by_image(image_id)
        logger.info(f"Retrieved {len(annotations)} annotations for image {image_id}")
        return [AnnotationResponse(**ann) for ann in annotations]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get annotations for image {image_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get image annotations: {str(e)}"
        )


@router.put("/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: str,
    annotation_update: AnnotationUpdate,
    username: str = Depends(authenticate_user)
):
    """
    Update annotation.
    
    Args:
        annotation_id: Annotation ID
        annotation_update: Updated annotation data
        
    Returns:
        dict: Update status
    """
    logger.info(f"Updating annotation {annotation_id} by user '{username}'")
    
    try:
        # Verify annotation exists
        annotation = annotation_service.get_annotation(annotation_id)
        if not annotation:
            logger.error(f"Annotation not found with ID: {annotation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation not found"
            )
        
        success = annotation_service.update_annotation(
            annotation_id, 
            annotation_update.dict(exclude_unset=True)
        )
        
        if success:
            logger.info(f"Annotation {annotation_id} updated successfully")
            return {"status": "success", "message": "Annotation updated successfully"}
        else:
            logger.error(f"Failed to update annotation {annotation_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update annotation"
            )
            
    except ValueError as e:
        logger.error(f"Invalid annotation data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update annotation: {str(e)}"
        )


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    username: str = Depends(authenticate_user)
):
    """
    Delete annotation.
    
    Args:
        annotation_id: Annotation ID
        
    Returns:
        dict: Deletion status
    """
    logger.info(f"Deleting annotation {annotation_id} by user '{username}'")
    
    try:
        # Verify annotation exists
        annotation = annotation_service.get_annotation(annotation_id)
        if not annotation:
            logger.error(f"Annotation not found with ID: {annotation_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Annotation not found"
            )
        
        success = annotation_service.delete_annotation(annotation_id)
        
        if success:
            logger.info(f"Annotation {annotation_id} deleted successfully")
            return {"status": "success", "message": "Annotation deleted successfully"}
        else:
            logger.error(f"Failed to delete annotation {annotation_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete annotation"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete annotation {annotation_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete annotation: {str(e)}"
        )


@router.get("/datasets/{dataset_id}/class-distribution")
async def get_class_distribution(
    dataset_id: str,
    split: Optional[str] = Query(None, description="Filter by split"),
    username: str = Depends(authenticate_user)
):
    """
    Get class distribution for a dataset.
    
    Args:
        dataset_id: Dataset ID
        split: Optional split filter
        
    Returns:
        dict: Class distribution statistics
    """
    logger.info(f"Getting class distribution for dataset {dataset_id}, split={split}")
    
    try:
        # Verify dataset exists
        dataset = dataset_service.get_dataset(dataset_id)
        if not dataset:
            logger.error(f"Dataset not found with ID: {dataset_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )
        
        distribution = annotation_service.get_class_distribution(dataset_id, split)
        logger.info(f"Retrieved class distribution for dataset {dataset_id}")
        return distribution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get class distribution for dataset {dataset_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get class distribution: {str(e)}"
        )