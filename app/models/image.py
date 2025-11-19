"""Image metadata model."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field, validator

from .annotation import AnnotationType
from .base import PyObjectId


class ImageMetadata(BaseModel):
    """Enhanced image metadata model."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    dataset_id: PyObjectId = Field(..., alias="dataset_id", description="Parent dataset ID")
    filename: str = Field(..., min_length=1, max_length=255, description="Image filename")
    file_path: str = Field(..., description="Path in storage")
    file_size: int = Field(0, ge=0, description="File size in bytes")
    file_hash: Optional[str] = Field(None, description="File MD5 hash")
    width: int = Field(..., ge=1, description="Image width")
    height: int = Field(..., ge=1, description="Image height")
    channels: Optional[int] = Field(None, ge=1, le=4, description="Number of channels")
    format: str = Field("jpg", description="Image format")
    split: str = Field(..., description="Dataset split (train/val/test)")
    annotations: List[AnnotationType] = Field(default_factory=list, description="Image annotations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extended metadata")
    is_annotated: bool = Field(False, description="Whether the image has annotations")
    annotation_count: int = Field(0, ge=0, description="Number of annotations")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('split')
    def validate_split(cls, v):
        """Validate split value."""
        if v not in ['train', 'val', 'test']:
            raise ValueError('split must be one of: train, val, test')
        return v
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
        "json_schema_extra": {
            "example": {
                "filename": "image1.jpg",
                "file_path": "dataset_123/image1.jpg", 
                "width": 640,
                "height": 480,
                "split": "train",
                "annotations": [],
                "is_annotated": False
            }
        }
    }

