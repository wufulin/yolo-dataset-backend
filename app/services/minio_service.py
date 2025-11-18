"""MinIO service for handling file storage operations."""
import os
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
from app.config import settings


class MinioService:
    """Service class for MinIO operations."""
    
    def __init__(self):
        """Initialize MinIO client."""
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise Exception(f"Failed to create bucket: {e}")
    
    def upload_file(self, file_path: str, object_name: str) -> str:
        """
        Upload a file to MinIO.
        
        Args:
            file_path: Local path to the file
            object_name: Object name in MinIO
            
        Returns:
            str: URL of the uploaded file
        """
        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path
            )
            return f"http://{settings.minio_endpoint}/{self.bucket_name}/{object_name}"
        except S3Error as e:
            raise Exception(f"Failed to upload file: {e}")
    
    def get_file_url(self, object_name: str) -> str:
        """
        Get presigned URL for a file.
        
        Args:
            object_name: Object name in MinIO
            
        Returns:
            str: Presigned URL
        """
        try:
            return self.client.presigned_get_object(
                self.bucket_name,
                object_name
            )
        except S3Error as e:
            raise Exception(f"Failed to generate URL: {e}")
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO.
        
        Args:
            object_name: Object name in MinIO
            
        Returns:
            bool: True if successful
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.
        
        Args:
            object_name: Object name in MinIO
            
        Returns:
            bool: True if file exists
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False


# Global MinIO service instance
minio_service = MinioService()