"""File upload API endpoints."""
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.auth import authenticate_user
from app.config import settings
from app.schemas.upload import UploadComplete, UploadResponse
from app.utils.file_utils import ensure_directory, safe_remove
from app.utils.logger import get_logger
from app.services import upload_service

logger = get_logger(__name__)


router = APIRouter()

# Store upload sessions in memory 
# TODO: Use Redis for production
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
        return await upload_service.process_dataset(
            session["temp_file"],
            upload_complete.dataset_info,
        )
        
    except Exception as e:
        # Cleanup on error
        safe_remove(session["temp_dir"])
        upload_sessions.pop(upload_id, None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process dataset: {str(e)}"
        )
