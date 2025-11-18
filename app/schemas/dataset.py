"""Pydantic schemas for API requests and responses."""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


class DatasetCreate(BaseModel):
    """Schema for dataset creation."""
    name: str = Field(..., min_length=1, max_length=100, description="Dataset name")
    description: Optional[str] = Field(None, max_length=500, description="Dataset description")
    dataset_type: str = Field(..., description="Dataset type: detect/obb/segment/pose/classify")
    class_names: Optional[List[str]] = Field(default=[], description="List of class names (optional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "My YOLO Dataset",
                "description": "A custom object detection dataset",
                "dataset_type": "detect",
                "class_names": ["person", "car", "dog", "cat"]
            }
        }


class DatasetResponse(BaseModel):
    """Schema for dataset response."""
    id: str = Field(..., description="Dataset ID")
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    dataset_type: str = Field(..., description="Dataset type")
    class_names: List[str] = Field(..., description="List of class names")
    num_images: int = Field(..., description="Number of images")
    num_annotations: int = Field(..., description="Total annotations")
    splits: Dict[str, int] = Field(..., description="Split counts")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    
    model_config = {"from_attributes": True}


class ImageResponse(BaseModel):
    """Schema for image response."""
    id: str = Field(..., description="Image ID")
    dataset_id: str = Field(..., description="Parent dataset ID")
    filename: str = Field(..., description="Image filename")
    file_url: str = Field(..., description="Image URL")
    width: int = Field(..., description="Image width")
    height: int = Field(..., description="Image height")
    split: str = Field(..., description="Dataset split")
    annotations: List[Dict[str, Any]] = Field(..., description="Image annotations")
    created_at: datetime = Field(..., description="Creation timestamp")


class UploadResponse(BaseModel):
    """Schema for upload response."""
    upload_id: str = Field(..., description="Upload session ID")
    chunk_size: int = Field(..., description="Chunk size in bytes")
    total_chunks: int = Field(..., description="Total number of chunks")


class UploadComplete(BaseModel):
    """Schema for upload completion."""
    upload_id: str = Field(..., description="Upload session ID")
    filename: str = Field(..., description="Original filename")
    dataset_info: Optional[DatasetCreate] = Field(None, description="Dataset information")


class PaginatedResponse(BaseModel):
    """Schema for paginated responses."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")