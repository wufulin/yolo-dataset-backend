"""File upload API endpoints."""
import os
import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from app.auth import authenticate_user
from app.config import settings
from app.utils.file_utils import ensure_directory, safe_remove
from app.schemas.dataset import UploadResponse, UploadComplete
from app.services.yolo_validator import yolo_validator
from app.services.mongo_service import mongo_service
from app.services.minio_service import minio_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter()

# Store upload sessions in memory (in production, use Redis)
upload_sessions = {}


@router.post("/upload/start", response_model=UploadResponse)
async def start_upload(
    filename: str = Form(...),
    total_size: int = Form(...),
    total_chunks: int = Form(...),
    chunk_size: int = Form(...),
    username: str = Depends(authenticate_user)
):
    """
    Start a new file upload session.
    
    Args:
        filename: Original filename
        total_size: Total file size in bytes
        total_chunks: Total number of chunks
        chunk_size: Size of each chunk in bytes
        
    Returns:
        UploadResponse: Upload session information
    """
    # Validate file size
    if total_size > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_upload_size} bytes"
        )
    
    # Create upload session
    upload_id = str(uuid.uuid4())
    temp_dir = os.path.join(settings.temp_dir, upload_id)
    ensure_directory(temp_dir)
    
    upload_sessions[upload_id] = {
        "filename": filename,
        "total_size": total_size,
        "total_chunks": total_chunks,
        "chunk_size": chunk_size,
        "received_chunks": set(),
        "temp_dir": temp_dir,
        "temp_file": os.path.join(temp_dir, filename)
    }
    
    return UploadResponse(
        upload_id=upload_id,
        chunk_size=chunk_size,
        total_chunks=total_chunks
    )


@router.post("/upload/chunk/{upload_id}/{chunk_index}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    file: UploadFile = File(...),
    username: str = Depends(authenticate_user)
):
    """
    Upload a file chunk.
    
    Args:
        upload_id: Upload session ID
        chunk_index: Index of the chunk
        file: Uploaded file chunk
        
    Returns:
        dict: Upload status
    """
    if upload_id not in upload_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    session = upload_sessions[upload_id]
    
    # Validate chunk index
    if chunk_index < 0 or chunk_index >= session["total_chunks"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid chunk index"
        )
    
    # Save chunk
    chunk_path = f"{session['temp_file']}.part{chunk_index}"
    try:
        with open(chunk_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        session["received_chunks"].add(chunk_index)
        
        return {"status": "success", "chunk": chunk_index}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save chunk: {str(e)}"
        )


@router.post("/upload/complete/{upload_id}")
async def complete_upload(
    upload_id: str,
    upload_complete: UploadComplete,
    username: str = Depends(authenticate_user)
):
    """
    Complete file upload and process dataset.
    
    Args:
        upload_id: Upload session ID
        upload_complete: Upload completion data
        
    Returns:
        dict: Processing status
    """
    if upload_id not in upload_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    session = upload_sessions[upload_id]
    
    # Check if all chunks are received
    if len(session["received_chunks"]) != session["total_chunks"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not all chunks received"
        )
    
    # Reassemble file
    try:
        with open(session["temp_file"], "wb") as output:
            for i in range(session["total_chunks"]):
                chunk_path = f"{session['temp_file']}.part{i}"
                with open(chunk_path, "rb") as chunk:
                    output.write(chunk.read())
                safe_remove(chunk_path)
        
        # Process the dataset
        return await process_dataset(
            session["temp_file"],
            upload_complete.dataset_info
        )
        
    except Exception as e:
        # Cleanup on error
        safe_remove(session["temp_dir"])
        upload_sessions.pop(upload_id, None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process dataset: {str(e)}"
        )


async def process_dataset(zip_path: str, dataset_info: Optional[any]) -> dict:
    """
    Process uploaded dataset ZIP file.
    
    Args:
        zip_path: Path to ZIP file
        dataset_info: Dataset information
        
    Returns:
        dict: Processing results
    """
    # Extract and validate dataset
    extract_dir = os.path.join(settings.temp_dir, f"extract_{uuid.uuid4()}")
    try:
        dataset_root = yolo_validator.extract_zip(zip_path, extract_dir)
        
        # Validate YOLO format
        is_valid, message = yolo_validator.validate_dataset(dataset_root)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YOLO dataset: {message}"
            )
        
        # Parse dataset information
        dataset_yaml = yolo_validator._find_dataset_yaml(dataset_root)
        yaml_data = {}
        if dataset_yaml:
            yaml_data = yolo_validator.parse_dataset_yaml(dataset_yaml)
        
        # Determine dataset type
        dataset_type = yolo_validator.get_dataset_type(dataset_root)
        class_names = yaml_data.get('names', [])
        
        # Create dataset in MongoDB
        dataset_data = {
            "name": dataset_info.name if dataset_info else "Unnamed Dataset",
            "description": dataset_info.description if dataset_info else None,
            "dataset_type": dataset_type,
            "class_names": class_names,
            "num_images": 0,
            "num_annotations": 0,
            "splits": {}
        }
        
        dataset_id = mongo_service.create_dataset(dataset_data)
        
        # Process images and annotations
        processed_count = await process_images(
            dataset_root, dataset_id, dataset_type, class_names, yaml_data
        )
        
        return {
            "status": "success",
            "dataset_id": dataset_id,
            "processed_images": processed_count,
            "dataset_type": dataset_type
        }
        
    finally:
        # Cleanup temporary files
        safe_remove(extract_dir)
        safe_remove(zip_path)


async def process_images(dataset_root: str, dataset_id: str, dataset_type: str,
                        class_names: List[str], yaml_data: dict) -> int:
    """
    Process all images and annotations in dataset.
    
    Args:
        dataset_root: Root directory of dataset
        dataset_id: Dataset ID in MongoDB
        dataset_type: Type of dataset
        class_names: List of class names
        yaml_data: YAML configuration data
        
    Returns:
        int: Number of processed images
    """
    processed_count = 0
    
    # Process each split (train, val, test)
    for split in ['train', 'val', 'test']:
        split_key = f"{split}_split" if split == 'train' else f"{split}"
        split_path = yaml_data.get(split_key)
        
        if not split_path or not os.path.exists(os.path.join(dataset_root, split_path)):
            continue
        
        # Process images in this split
        split_processed = 0
        for image_file in find_image_files(os.path.join(dataset_root, split_path)):
            try:
                await process_single_image(
                    image_file, dataset_id, split, dataset_type,
                    class_names, dataset_root
                )
                split_processed += 1
                processed_count += 1                
            except Exception as e:
                logger.error(f"Error processing image {image_file}: {str(e)}", exc_info=True)
                continue
    
    return processed_count


async def process_single_image(image_path: str, dataset_id: str, split: str,
                              dataset_type: str, class_names: List[str],
                              dataset_root: str) -> None:
    """
    Process a single image and its annotations.
    
    Args:
        image_path: Path to image file
        dataset_id: Dataset ID
        split: Dataset split
        dataset_type: Type of dataset
        class_names: List of class names
        dataset_root: Root directory of dataset
    """
    # Upload image to MinIO
    object_name = f"{dataset_id}/{os.path.basename(image_path)}"
    image_url = minio_service.upload_file(image_path, object_name)
    
    # Find and parse annotations
    annotation_path = find_annotation_path(image_path, dataset_root)
    annotations = []
    if annotation_path and os.path.exists(annotation_path):
        annotations = yolo_validator.parse_annotations(
            annotation_path, dataset_type, class_names
        )
    
    # Create image metadata
    image_data = {
        "dataset_id": dataset_id,
        "filename": os.path.basename(image_path),
        "file_path": object_name,
        "width": 0,  # Would need to read image dimensions
        "height": 0,
        "split": split,
        "annotations": annotations
    }
    
    mongo_service.create_image(image_data)


def find_image_files(directory: str) -> List[str]:
    """Find all image files in directory."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    image_files = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_files.append(os.path.join(root, file))
    
    return image_files


def find_annotation_path(image_path: str, dataset_root: str) -> Optional[str]:
    """Find corresponding annotation file for an image."""
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    
    # Look for annotation in labels directory
    labels_dir = os.path.join(dataset_root, "labels")
    if os.path.exists(labels_dir):
        annotation_path = os.path.join(labels_dir, f"{base_name}.txt")
        if os.path.exists(annotation_path):
            return annotation_path
    
    return None