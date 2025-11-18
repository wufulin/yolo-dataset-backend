"""Pydantic schemas for API requests and responses."""
from app.schemas.annotation import (
    AnnotationBase,
    AnnotationResponse,
    AnnotationStatsResponse,
    AnnotationUpdate,
    BBoxSchema,
    ClassificationAnnotationCreate,
    DetectionAnnotationCreate,
    OBBAnnotationCreate,
    PaginatedAnnotationsResponse,
    PoseAnnotationCreate,
    SegmentationAnnotationCreate,
)
from app.schemas.dataset import (
    DatasetCreate,
    DatasetResponse,
    ImageResponse,
    PaginatedResponse,
    UploadComplete,
    UploadResponse,
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

