"""Pydantic schemas for annotation API requests and responses."""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class AnnotationBase(BaseModel):
    """Base annotation schema."""
    image_id: str = Field(..., description="Image ID")
    dataset_id: str = Field(..., description="Dataset ID")
    class_id: int = Field(..., description="Class ID")
    class_name: str = Field(..., description="Class name")
    annotation_type: str = Field(..., description="Annotation type")
    confidence: Optional[float] = Field(None, description="Confidence score")
    is_crowd: bool = Field(False, description="Is crowd annotation")
    area: Optional[float] = Field(None, description="Annotation area")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class BBoxSchema(BaseModel):
    """Bounding box schema."""
    x_center: float = Field(..., description="Normalized x center")
    y_center: float = Field(..., description="Normalized y center")
    width: float = Field(..., description="Normalized width")
    height: float = Field(..., description="Normalized height")


class DetectionAnnotationCreate(AnnotationBase):
    """Schema for creating detection annotation."""
    annotation_type: str = "detect"
    bbox: BBoxSchema = Field(..., description="Bounding box")


class OBBAnnotationCreate(AnnotationBase):
    """Schema for creating OBB annotation."""
    annotation_type: str = "obb"
    points: List[float] = Field(..., description="OBB points")


class SegmentationAnnotationCreate(AnnotationBase):
    """Schema for creating segmentation annotation."""
    annotation_type: str = "segment"
    points: List[float] = Field(..., description="Polygon points")


class PoseAnnotationCreate(AnnotationBase):
    """Schema for creating pose annotation."""
    annotation_type: str = "pose"
    keypoints: List[float] = Field(..., description="Keypoints")
    num_keypoints: int = Field(..., description="Number of keypoints")
    skeleton: Optional[List[int]] = Field(None, description="Skeleton connections")


class ClassificationAnnotationCreate(AnnotationBase):
    """Schema for creating classification annotation."""
    annotation_type: str = "classify"


# Union type for annotation creation
AnnotationCreate = Union[
    DetectionAnnotationCreate,
    OBBAnnotationCreate,
    SegmentationAnnotationCreate, 
    PoseAnnotationCreate,
    ClassificationAnnotationCreate
]


class AnnotationResponse(BaseModel):
    """Schema for annotation response."""
    id: str = Field(..., description="Annotation ID")
    image_id: str = Field(..., description="Image ID")
    dataset_id: str = Field(..., description="Dataset ID")
    class_id: int = Field(..., description="Class ID")
    class_name: str = Field(..., description="Class name")
    annotation_type: str = Field(..., description="Annotation type")
    confidence: Optional[float] = Field(None, description="Confidence score")
    is_crowd: bool = Field(..., description="Is crowd annotation")
    area: Optional[float] = Field(None, description="Annotation area")
    
    # Type-specific fields
    bbox: Optional[BBoxSchema] = Field(None, description="Bounding box (for detection)")
    points: Optional[List[float]] = Field(None, description="Points (for OBB/segmentation)")
    keypoints: Optional[List[float]] = Field(None, description="Keypoints (for pose)")
    num_keypoints: Optional[int] = Field(None, description="Number of keypoints (for pose)")
    skeleton: Optional[List[int]] = Field(None, description="Skeleton (for pose)")
    
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    
    model_config = {"from_attributes": True}


class AnnotationUpdate(BaseModel):
    """Schema for annotation update."""
    class_id: Optional[int] = Field(None, description="Class ID")
    class_name: Optional[str] = Field(None, description="Class name")
    confidence: Optional[float] = Field(None, description="Confidence score")
    is_crowd: Optional[bool] = Field(None, description="Is crowd annotation")
    area: Optional[float] = Field(None, description="Annotation area")
    
    # Type-specific fields
    bbox: Optional[BBoxSchema] = Field(None, description="Bounding box")
    points: Optional[List[float]] = Field(None, description="Points")
    keypoints: Optional[List[float]] = Field(None, description="Keypoints")
    skeleton: Optional[List[int]] = Field(None, description="Skeleton")
    
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AnnotationStatsResponse(BaseModel):
    """Schema for annotation statistics response."""
    dataset_id: str = Field(..., description="Dataset ID")
    date: datetime = Field(..., description="Statistics date")
    total_annotations: int = Field(..., description="Total annotations")
    annotations_by_class: Dict[str, int] = Field(..., description="Annotations by class")
    annotations_by_type: Dict[str, int] = Field(..., description="Annotations by type")
    avg_confidence: Optional[float] = Field(None, description="Average confidence")
    created_at: datetime = Field(..., description="Creation timestamp")


class PaginatedAnnotationsResponse(BaseModel):
    """Schema for paginated annotations response."""
    items: List[AnnotationResponse] = Field(..., description="List of annotations")
    total: int = Field(..., description="Total number of annotations")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")


class ClassDistributionResponse(BaseModel):
    """Schema for class distribution response."""
    dataset_id: str = Field(..., description="Dataset ID")
    split: Optional[str] = Field(None, description="Dataset split")
    total_images: int = Field(..., description="Total images")
    total_annotations: int = Field(..., description="Total annotations")
    classes: Dict[str, int] = Field(..., description="Class counts")
    created_at: datetime = Field(..., description="Generation timestamp")