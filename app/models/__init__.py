"""Data models for MongoDB collections."""
from app.models.annotation import (
    Annotation,
    AnnotationFilter,
    AnnotationStats,
    AnnotationType,
    BaseAnnotation,
    BBox,
    ClassificationAnnotation,
    DetectionAnnotation,
    OBBAnnotation,
    OBBPoints,
    PoseAnnotation,
    PoseKeypoints,
    SegmentationAnnotation,
    SegmentationPolygon,
)
from app.models.base import MongoBaseModel, PyObjectId
from app.models.dataset import Dataset, ImageMetadata, UploadSession

__all__ = [
    # Base
    "PyObjectId",
    "MongoBaseModel",
    # Dataset models
    "Dataset",
    "ImageMetadata",
    "UploadSession",
    # Annotation models
    "Annotation",
    "AnnotationType",
    "BaseAnnotation",
    "BBox",
    "OBBPoints",
    "SegmentationPolygon",
    "PoseKeypoints",
    "AnnotationStats",
    "AnnotationFilter",
    "DetectionAnnotation",
    "OBBAnnotation",
    "SegmentationAnnotation",
    "PoseAnnotation",
    "ClassificationAnnotation"
]

