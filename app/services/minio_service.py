"""MinIO service for handling file storage operations."""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple

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
    
    def upload_file(self, file_path: str, object_name: str, content_type: str = "image/jpeg") -> str:
        """
        Upload a file to MinIO.
        
        Args:
            file_path: Local path to the file
            object_name: Object name in MinIO
            content_type: MIME type of the file (default: "image/jpeg")
            
        Returns:
            str: URL of the uploaded file
        """
        logger.info(f"Uploading file '{file_path}' to MinIO as '{object_name}' (content_type: {content_type})")
        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path,
                content_type=content_type
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
    
    def _get_single_file_url(self, object_name: str) -> Dict[str, any]:
        """
        Internal method to get URL for a single file (used by batch get URLs).
        
        Args:
            object_name: Object name in MinIO
            
        Returns:
            Dict containing URL generation result
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name
            )
            return {
                "success": True,
                "object_name": object_name,
                "url": url,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "object_name": object_name,
                "url": None,
                "error": str(e)
            }
    
    def _upload_single_file(self, file_info: Tuple[str, str, str]) -> Dict[str, any]:
        """
        Internal method to upload a single file (used by batch upload).
        
        Args:
            file_info: Tuple of (file_path, object_name, content_type)
            
        Returns:
            Dict containing upload result
        """
        file_path, object_name, content_type = file_info
        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path,
                content_type=content_type
            )
            url = f"http://{settings.minio_endpoint}/{self.bucket_name}/{object_name}"
            return {
                "success": True,
                "file_path": file_path,
                "object_name": object_name,
                "url": url,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "file_path": file_path,
                "object_name": object_name,
                "url": None,
                "error": str(e)
            }
    
    def _batch_upload_attempt(
        self,
        file_list: List[Tuple[str, str, str]],
        max_workers: int
    ) -> Tuple[List[Dict], List[str], List[Dict]]:
        """
        Internal method to attempt batch upload (used for initial upload and retries).
        
        Args:
            file_list: List of tuples (file_path, object_name, content_type)
            max_workers: Maximum number of concurrent upload threads
            
        Returns:
            Tuple of (all_results, success_list, failed_list)
        """
        results = []
        success_list = []
        failed_list = []
        
        # Use ThreadPoolExecutor for concurrent uploads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all upload tasks
            future_to_file = {
                executor.submit(self._upload_single_file, file_info): file_info 
                for file_info in file_list
            }
            
            # Process completed uploads
            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    success_list.append(result["object_name"])
                    logger.info(f"✓ Uploaded: {result['object_name']}")
                else:
                    # Find the content_type from the original file_info
                    file_info = future_to_file[future]
                    failed_list.append({
                        "file_path": result["file_path"],
                        "object_name": result["object_name"],
                        "content_type": file_info[2] if len(file_info) > 2 else "image/jpeg",
                        "error": result["error"]
                    })
                    logger.error(f"✗ Failed to upload {result['object_name']}: {result['error']}")
        
        return results, success_list, failed_list
    
    def upload_files(
        self, 
        file_list: List[Tuple[str, str]], 
        max_workers: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        content_type: str = "image/jpeg"
    ) -> Dict[str, any]:
        """
        Upload multiple files to MinIO in parallel with automatic retry for failed uploads.
        
        Args:
            file_list: List of tuples (file_path, object_name) or (file_path, object_name, content_type)
            max_workers: Maximum number of concurrent upload threads (default: 10)
            max_retries: Maximum number of retry attempts for failed uploads (default: 3)
            retry_delay: Delay in seconds between retry attempts (default: 1.0)
            content_type: Default MIME type for files if not specified in tuple (default: "image/jpeg")
            
        Returns:
            Dict containing:
                - total: Total number of files
                - successful: Number of successful uploads
                - failed: Number of failed uploads (after all retries)
                - results: List of individual upload results
                - success_list: List of successfully uploaded object names
                - failed_list: List of failed uploads with errors (after all retries)
                - retry_info: Information about retry attempts
        """
        if not file_list:
            logger.warning("Empty file list provided for batch upload")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "success_list": [],
                "failed_list": [],
                "retry_info": {
                    "total_retries": 0,
                    "retry_attempts": []
                }
            }
        
        logger.info(
            f"Starting batch upload of {len(file_list)} files with {max_workers} workers "
            f"(max_retries: {max_retries}, retry_delay: {retry_delay}s, default_content_type: {content_type})"
        )
        
        # Normalize file_list to ensure all tuples have content_type
        normalized_file_list = []
        for item in file_list:
            if len(item) == 2:
                # Add default content_type
                normalized_file_list.append((item[0], item[1], content_type))
            elif len(item) == 3:
                # Already has content_type
                normalized_file_list.append(item)
            else:
                logger.error(f"Invalid file_list item: {item}")
                raise ValueError(f"Each item in file_list must be a tuple of 2 or 3 elements, got: {item}")
        
        # Initial upload attempt
        all_results = []
        success_list = []
        failed_list = []
        retry_info = {
            "total_retries": 0,
            "retry_attempts": []
        }
        
        # First attempt
        results, success, failed = self._batch_upload_attempt(normalized_file_list, max_workers)
        all_results.extend(results)
        success_list.extend(success)
        failed_list = failed
        
        logger.info(
            f"Initial upload completed: {len(success)}/{len(file_list)} successful, "
            f"{len(failed)} failed"
        )
        
        # Retry failed uploads
        retry_count = 0
        while failed_list and retry_count < max_retries:
            retry_count += 1
            logger.info(
                f"Retry attempt {retry_count}/{max_retries}: "
                f"Retrying {len(failed_list)} failed uploads after {retry_delay}s delay"
            )
            
            # Wait before retry
            time.sleep(retry_delay)
            
            # Prepare file list for retry (with content_type preserved)
            retry_file_list = [(f["file_path"], f["object_name"], f["content_type"]) for f in failed_list]
            
            # Attempt retry
            retry_results, retry_success, retry_failed = self._batch_upload_attempt(
                retry_file_list, 
                max_workers
            )
            
            # Record retry attempt info
            retry_info["retry_attempts"].append({
                "attempt": retry_count,
                "files_retried": len(retry_file_list),
                "successful": len(retry_success),
                "failed": len(retry_failed)
            })
            retry_info["total_retries"] = retry_count
            
            # Update results
            all_results.extend(retry_results)
            success_list.extend(retry_success)
            failed_list = retry_failed
            
            logger.info(
                f"Retry {retry_count} completed: {len(retry_success)} recovered, "
                f"{len(retry_failed)} still failed"
            )
        
        # Final summary
        summary = {
            "total": len(file_list),
            "successful": len(success_list),
            "failed": len(failed_list),
            "results": all_results,
            "success_list": success_list,
            "failed_list": failed_list,
            "retry_info": retry_info
        }
        
        logger.info(
            f"Batch upload completed: {summary['successful']}/{summary['total']} successful, "
            f"{summary['failed']} failed (after {retry_count} retry attempts)"
        )
        
        return summary
    
    def get_files_urls(
        self, 
        object_names: List[str], 
        max_workers: int = 20
    ) -> Dict[str, any]:
        """
        Get presigned URLs for multiple files from MinIO in parallel for high performance.
        
        Args:
            object_names: List of object names in MinIO
            max_workers: Maximum number of concurrent threads (default: 20)
            
        Returns:
            Dict containing:
                - total: Total number of files
                - successful: Number of successful URL generations
                - failed: Number of failed URL generations
                - results: List of individual URL generation results
                - urls: Dict mapping object_name to URL (only successful ones)
                - failed_list: List of failed objects with errors
        """
        if not object_names:
            logger.warning("Empty object names list provided for batch URL generation")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "results": [],
                "urls": {},
                "failed_list": []
            }
        
        logger.info(f"Starting batch URL generation for {len(object_names)} files with {max_workers} workers")
        
        results = []
        urls = {}
        failed_list = []
        
        # Use ThreadPoolExecutor for concurrent URL generation
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all URL generation tasks
            future_to_object = {
                executor.submit(self._get_single_file_url, object_name): object_name 
                for object_name in object_names
            }
            
            # Process completed tasks
            for future in as_completed(future_to_object):
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    urls[result["object_name"]] = result["url"]
                    logger.info(f"✓ Generated URL for: {result['object_name']}")
                else:
                    failed_list.append({
                        "object_name": result["object_name"],
                        "error": result["error"]
                    })
                    logger.error(f"✗ Failed to generate URL for {result['object_name']}: {result['error']}")
        
        summary = {
            "total": len(object_names),
            "successful": len(urls),
            "failed": len(failed_list),
            "results": results,
            "urls": urls,
            "failed_list": failed_list
        }
        
        logger.info(
            f"Batch URL generation completed: {summary['successful']}/{summary['total']} successful, "
            f"{summary['failed']} failed"
        )
        
        return summary


# Global MinIO service instance
minio_service = MinioService()