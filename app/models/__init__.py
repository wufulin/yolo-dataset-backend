"""Data models for MongoDB collections."""
from app.models.base import PyObjectId, MongoBaseModel
from app.models.dataset import (
    Dataset,
    ImageMetadata,
    UploadSession
)
from app.models.annotation import (
    Annotation,
    AnnotationType,
    BaseAnnotation,
    BBox,
    OBBPoints,
    SegmentationPolygon,
    PoseKeypoints,
    AnnotationStats,
    AnnotationFilter,
    DetectionAnnotation,
    OBBAnnotation,
    SegmentationAnnotation,
    PoseAnnotation,
    ClassificationAnnotation
)

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

