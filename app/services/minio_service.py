"""MinIO service for handling file storage operations."""
from minio import Minio
from minio.error import S3Error
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MinioService:
    """Service class for MinIO operations."""
    
    def __init__(self):
        """Initialize MinIO client."""
        logger.info(f"Initializing MinIO client (endpoint: {settings.minio_endpoint}, bucket: {settings.minio_bucket_name})")
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        self._ensure_bucket_exists()
        logger.info("MinIO client initialized successfully")
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(f"Creating MinIO bucket: {self.bucket_name}")
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created successfully")
            else:
                logger.info(f"Bucket '{self.bucket_name}' already exists")
        except S3Error as e:
            logger.error(f"Failed to create bucket '{self.bucket_name}': {e}", exc_info=True)
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
        logger.info(f"Uploading file '{file_path}' to MinIO as '{object_name}'")
        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path
            )
            url = f"http://{settings.minio_endpoint}/{self.bucket_name}/{object_name}"
            logger.info(f"File uploaded successfully: {object_name}")
            return url
        except S3Error as e:
            logger.error(f"Failed to upload file '{object_name}': {e}", exc_info=True)
            raise Exception(f"Failed to upload file: {e}")
    
    def get_file_url(self, object_name: str) -> str:
        """
        Get presigned URL for a file.
        
        Args:
            object_name: Object name in MinIO
            
        Returns:
            str: Presigned URL
        """
        logger.info(f"Generating presigned URL for: {object_name}")
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name
            )
            logger.info(f"Presigned URL generated for: {object_name}")
            return url
        except S3Error as e:
            logger.error(f"Failed to generate URL for '{object_name}': {e}", exc_info=True)
            raise Exception(f"Failed to generate URL: {e}")
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO.
        
        Args:
            object_name: Object name in MinIO
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Deleting file from MinIO: {object_name}")
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"File deleted successfully: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to delete file '{object_name}': {e}", exc_info=True)
            return False
    
    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.
        
        Args:
            object_name: Object name in MinIO
            
        Returns:
            bool: True if file exists
        """
        logger.info(f"Checking if file exists in MinIO: {object_name}")
        try:
            self.client.stat_object(self.bucket_name, object_name)
            logger.info(f"File exists: {object_name}")
            return True
        except S3Error:
            logger.error(f"File does not exist: {object_name}")
            return False


# Global MinIO service instance
minio_service = MinioService()