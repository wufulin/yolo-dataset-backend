"""Enhanced MongoDB data models for datasets."""
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class Dataset(BaseModel):
    """Enhanced dataset model."""
    name: str = Field(..., min_length=1, max_length=100, description="Dataset name")
    description: Optional[str] = Field(None, max_length=500, description="Dataset description")
    dataset_type: str = Field(..., description="Dataset type: detect/obb/segment/pose/classify")
    class_names: List[str] = Field(default_factory=list, description="List of class names")
    num_images: int = Field(0, ge=0, description="Number of images in dataset")
    num_annotations: int = Field(0, ge=0, description="Total number of annotations")
    splits: Dict[str, int] = Field(default_factory=dict, description="Split counts")
    status: str = Field("processing", description="Dataset status")
    error_message: Optional[str] = Field(None, description="Error message if status is error")
    file_size: int = Field(0, ge=0, description="Original file size in bytes")
    storage_path: Optional[str] = Field(None, description="Storage path for dataset files")
    created_by: str = Field("admin", description="User who created the dataset")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(1, ge=1, description="Dataset version")
    
    @staticmethod
    def get_current_time() -> datetime:
        """Get current UTC time."""
        return datetime.utcnow()
    
    @validator('dataset_type')
    def validate_dataset_type(cls, v):
        """Validate dataset type."""
        if v not in ['detect', 'obb', 'segment', 'pose', 'classify']:
            raise ValueError('dataset_type must be one of: detect, obb, segment, pose, classify')
        return v
    
    @validator('status') 
    def validate_status(cls, v):
        """Validate status."""
        if v not in ['processing', 'active', 'error', 'deleted']:
            raise ValueError('status must be one of: processing, active, error, deleted')
        return v
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "name": "COCO Dataset",
                "description": "COCO8 dataset",
                "dataset_type": "detect",
                "class_names": ["person", "car", "bicycle"],
                "num_images": 1000,
                "num_annotations": 5000,
                "splits": {"train": 800, "val": 200},
                "status": "active",
                "version": 1
            }
        }
    }