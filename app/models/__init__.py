"""Data models for MongoDB collections."""
from app.models.base import PyObjectId, MongoBaseModel
from app.models.dataset import (
    Dataset,
    ImageMetadata,
    UploadSession,
    BBoxAnnotation,
    OBBAnnotation,
    SegmentationAnnotation,
    PoseAnnotation,
    ClassificationAnnotation
)
from app.models.annotation import (
    Annotation,
    BaseAnnotation,
    BBox,
    OBBPoints,
    SegmentationPolygon,
    PoseKeypoints,
    AnnotationStats,
    AnnotationFilter,
    DetectionAnnotation,
    OBBAnnotation as OBBAnnotationDetail,
    SegmentationAnnotation as SegmentationAnnotationDetail,
    PoseAnnotation as PoseAnnotationDetail,
    ClassificationAnnotation as ClassificationAnnotationDetail
)

__all__ = [
    # Base
    "PyObjectId",
    "MongoBaseModel",
    # Dataset models
    "Dataset",
    "ImageMetadata",
    "UploadSession",
    "BBoxAnnotation",
    "OBBAnnotation",
    "SegmentationAnnotation",
    "PoseAnnotation",
    "ClassificationAnnotation",
    # Annotation models
    "Annotation",
    "BaseAnnotation",
    "BBox",
    "OBBPoints",
    "SegmentationPolygon",
    "PoseKeypoints",
    "AnnotationStats",
    "AnnotationFilter",
    "DetectionAnnotation",
    "OBBAnnotationDetail",
    "SegmentationAnnotationDetail",
    "PoseAnnotationDetail",
    "ClassificationAnnotationDetail"
]

