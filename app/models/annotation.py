"""Annotation models for YOLO dataset types."""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from .base import PyObjectId


class BBox(BaseModel):
    """Bounding box coordinates."""
    x_center: float = Field(..., ge=0, le=1, description="Normalized x center coordinate")
    y_center: float = Field(..., ge=0, le=1, description="Normalized y center coordinate")
    width: float = Field(..., ge=0, le=1, description="Normalized width")
    height: float = Field(..., ge=0, le=1, description="Normalized height")
    
    @validator('width', 'height')
    def validate_dimensions(cls, v):
        """Validate that dimensions are within bounds."""
        if v <= 0:
            raise ValueError('Width and height must be positive')
        return v


class OBBPoints(BaseModel):
    """Oriented bounding box points."""
    points: List[float] = Field(..., min_items=8, max_items=8, description="8 coordinate values for 4 points")


class SegmentationPolygon(BaseModel):
    """Segmentation polygon points."""
    points: List[float] = Field(..., min_items=6, description="Polygon points (minimum 3 points)")


class PoseKeypoints(BaseModel):
    """Pose keypoints data."""
    keypoints: List[float] = Field(..., description="Keypoint coordinates and visibility")
    skeleton: Optional[List[int]] = Field(None, description="Skeleton connection indices")
    
    @validator('keypoints')
    def validate_keypoints(cls, v):
        """Validate keypoints format."""
        if len(v) % 3 != 0:
            raise ValueError('Keypoints must be in format [x1,y1,v1,x2,y2,v2,...]')
        return v


class BaseAnnotation(BaseModel):
    """Base annotation model with common fields."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    image_id: PyObjectId = Field(..., description="Reference to image")
    dataset_id: PyObjectId = Field(..., description="Reference to dataset")
    class_id: int = Field(..., ge=0, description="Class ID")
    class_name: str = Field(..., min_length=1, description="Class name")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")
    is_crowd: bool = Field(False, description="Whether annotation is for a crowd")
    area: Optional[float] = Field(None, ge=0, description="Annotation area")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @staticmethod
    def get_current_time() -> datetime:
        """Get current UTC time."""
        return datetime.utcnow()


class DetectionAnnotation(BaseAnnotation):
    """Detection annotation (bounding box)."""
    annotation_type: Literal["detect"] = "detect"
    bbox: BBox = Field(..., description="Bounding box coordinates")
    
    @property
    def normalized_coordinates(self) -> List[float]:
        """Get normalized coordinates in YOLO format."""
        return [
            self.bbox.x_center,
            self.bbox.y_center,
            self.bbox.width,
            self.bbox.height
        ]
    
    @property
    def pixel_coordinates(self, image_width: int, image_height: int) -> List[float]:
        """Convert to pixel coordinates."""
        return [
            self.bbox.x_center * image_width,
            self.bbox.y_center * image_height,
            self.bbox.width * image_width,
            self.bbox.height * image_height
        ]


class OBBAnnotation(BaseAnnotation):
    """Oriented bounding box annotation."""
    annotation_type: Literal["obb"] = "obb"
    obb: OBBPoints = Field(..., description="OBB points")
    
    @property
    def normalized_coordinates(self) -> List[float]:
        """Get normalized coordinates."""
        return self.obb.points
    
    @validator('obb')
    def validate_obb_points(cls, v):
        """Validate OBB points."""
        points = v.points
        if len(points) != 8:
            raise ValueError('OBB must have exactly 8 coordinate values')
        return v


class SegmentationAnnotation(BaseAnnotation):
    """Segmentation annotation."""
    annotation_type: Literal["segment"] = "segment"
    segment: SegmentationPolygon = Field(..., description="Segmentation polygon")
    
    @property
    def normalized_coordinates(self) -> List[float]:
        """Get normalized coordinates."""
        return self.segment.points
    
    @validator('segment')
    def validate_polygon(cls, v):
        """Validate polygon has at least 3 points."""
        if len(v.points) < 6:  # 3 points = 6 coordinates
            raise ValueError('Segmentation polygon must have at least 3 points')
        return v


class PoseAnnotation(BaseAnnotation):
    """Pose estimation annotation."""
    annotation_type: Literal["pose"] = "pose"
    pose: PoseKeypoints = Field(..., description="Pose keypoints")
    num_keypoints: int = Field(..., ge=1, description="Number of keypoints")
    
    @property
    def normalized_coordinates(self) -> List[float]:
        """Get normalized coordinates."""
        return self.pose.keypoints
    
    @validator('num_keypoints')
    def validate_num_keypoints(cls, v, values):
        """Validate number of keypoints matches the data."""
        if 'pose' in values and len(values['pose'].keypoints) != v * 3:
            raise ValueError('Number of keypoints does not match keypoints data length')
        return v


class ClassificationAnnotation(BaseAnnotation):
    """Classification annotation."""
    annotation_type: Literal["classify"] = "classify"
    
    @property
    def normalized_coordinates(self) -> List[float]:
        """Get normalized coordinates (just class ID)."""
        return [float(self.class_id)]


# Union type for all annotation types
Annotation = Union[
    DetectionAnnotation,
    OBBAnnotation, 
    SegmentationAnnotation,
    PoseAnnotation,
    ClassificationAnnotation
]


class AnnotationStats(BaseModel):
    """Annotation statistics model."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    dataset_id: PyObjectId = Field(..., description="Dataset reference")
    date: datetime = Field(..., description="Statistics date")
    total_annotations: int = Field(0, ge=0, description="Total annotations")
    annotations_by_class: Dict[str, int] = Field(default_factory=dict, description="Annotations per class")
    annotations_by_type: Dict[str, int] = Field(default_factory=dict, description="Annotations per type")
    avg_confidence: Optional[float] = Field(None, ge=0, le=1, description="Average confidence")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }


class AnnotationFilter(BaseModel):
    """Annotation filter criteria."""
    dataset_id: Optional[str] = Field(None, description="Filter by dataset")
    image_id: Optional[str] = Field(None, description="Filter by image")
    class_ids: Optional[List[int]] = Field(None, description="Filter by class IDs")
    class_names: Optional[List[str]] = Field(None, description="Filter by class names")
    annotation_types: Optional[List[str]] = Field(None, description="Filter by annotation types")
    min_confidence: Optional[float] = Field(None, ge=0, le=1, description="Minimum confidence")
    max_confidence: Optional[float] = Field(None, ge=0, le=1, description="Maximum confidence")
    split: Optional[str] = Field(None, description="Filter by dataset split")
    
    @validator('annotation_types')
    def validate_annotation_types(cls, v):
        """Validate annotation types."""
        if v is not None:
            valid_types = ['detect', 'obb', 'segment', 'pose', 'classify']
            for ann_type in v:
                if ann_type not in valid_types:
                    raise ValueError(f'Invalid annotation type: {ann_type}')
        return v
    
    @validator('split')
    def validate_split(cls, v):
        """Validate split value."""
        if v is not None and v not in ['train', 'val', 'test']:
            raise ValueError('split must be one of: train, val, test')
        return v