"""Enhanced MongoDB data models with complete database design."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from .base import PyObjectId
from .annotation import AnnotationType


class ImageMetadata(BaseModel):
    """Enhanced image metadata model."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    dataset_id: PyObjectId = Field(..., description="Parent dataset ID")
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


class Dataset(BaseModel):
    """Enhanced dataset model."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
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
        "json_encoders": {ObjectId: str},
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


class UploadSession(BaseModel):
    """Upload session model."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    upload_id: str = Field(..., description="Upload session ID")
    user_id: str = Field(..., description="User ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., ge=0, description="File total size")
    total_chunks: int = Field(..., ge=1, description="Total number of chunks")
    chunk_size: int = Field(..., ge=1024, description="Chunk size in bytes")
    received_chunks: List[int] = Field(default_factory=list, description="Received chunk indices")
    temp_path: str = Field(..., description="Temporary file path")
    status: str = Field("uploading", description="Upload status")
    dataset_id: Optional[PyObjectId] = Field(None, description="Associated dataset ID")
    error_message: Optional[str] = Field(None, description="Error message")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(description="Session expiration time")
    
    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }