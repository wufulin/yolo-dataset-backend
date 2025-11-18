"""Pydantic schemas for API requests and responses."""
from app.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    ImageResponse,
    UploadResponse,
    UploadComplete,
    PaginatedResponse
)
from app.schemas.annotation import (
    AnnotationBase,
    BBoxSchema,
    DetectionAnnotationCreate,
    OBBAnnotationCreate,
    SegmentationAnnotationCreate,
    PoseAnnotationCreate,
    ClassificationAnnotationCreate,
    AnnotationResponse,
    AnnotationUpdate,
    AnnotationStatsResponse,
    PaginatedAnnotationsResponse
)

__all__ = [
    # Dataset schemas
    "DatasetCreate",
    "DatasetResponse",
    "ImageResponse",
    "UploadResponse",
    "UploadComplete",
    "PaginatedResponse",
    # Annotation schemas
    "AnnotationBase",
    "BBoxSchema",
    "DetectionAnnotationCreate",
    "OBBAnnotationCreate",
    "SegmentationAnnotationCreate",
    "PoseAnnotationCreate",
    "ClassificationAnnotationCreate",
    "AnnotationResponse",
    "AnnotationUpdate",
    "AnnotationStatsResponse",
    "PaginatedAnnotationsResponse"
]

