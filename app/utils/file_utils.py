"""Utility functions for file operations."""
import os
import hashlib
import shutil
from pathlib import Path


def ensure_directory(path: str) -> None:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash of a file.
    
    Args:
        file_path: Path to file
        chunk_size: Chunk size for reading
        
    Returns:
        str: MD5 hash
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def safe_remove(path: str) -> bool:
    """
    Safely remove file or directory.
    
    Args:
        path: Path to remove
        
    Returns:
        bool: True if successful
    """
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception:
        return False


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        int: File size in bytes
    """
    return os.path.getsize(file_path)


def get_extension(filename: str) -> str:
    """
    Get file extension in lowercase.
    
    Args:
        filename: Filename
        
    Returns:
        str: File extension
    """
    return Path(filename).suffix.lower()


def is_valid_filename(filename: str) -> bool:
    """
    Check if filename is valid.
    
    Args:
        filename: Filename to check
        
    Returns:
        bool: True if filename is valid
    """
    if not filename or filename.startswith('.'):
        return False
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        if char in filename:
            return False
    
    return True