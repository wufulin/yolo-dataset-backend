"""Service for handling image operations."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo.errors import PyMongoError

from app.models.image import ImageMetadata
from app.services.db_service import db_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImageService:
    """Service class for Image operations."""
    
    def __init__(self):
        """Initialize Image service."""
        self.db = db_service
        self.images = self.db.images
    
    def create_image(self, image: ImageMetadata) -> str:
        """
        Create image metadata.
        
        Args:
            image: ImageMetadata object
            
        Returns:
            str: Created image ID
            
        Raises:
            Exception: For database errors
        """
        try:
            # Convert to dict with alias
            image_dict = image.model_dump(by_alias=True, mode='python')
            
            # Ensure _id is ObjectId, not string (model_dump serializes PyObjectId to string)
            if "_id" in image_dict:
                if isinstance(image_dict["_id"], str):
                    image_dict["_id"] = ObjectId(image_dict["_id"])
                elif not isinstance(image_dict["_id"], ObjectId):
                    image_dict["_id"] = ObjectId()
            else:
                image_dict["_id"] = ObjectId()
            
            # Ensure dataset_id is ObjectId (model_dump serializes PyObjectId to string)
            if "dataset_id" in image_dict:
                from app.models.base import PyObjectId
                if isinstance(image_dict["dataset_id"], str):
                    image_dict["dataset_id"] = ObjectId(image_dict["dataset_id"])
                elif isinstance(image_dict["dataset_id"], PyObjectId):
                    image_dict["dataset_id"] = ObjectId(image_dict["dataset_id"])
            
            result = self.images.insert_one(image_dict)
            logger.info(f"Created image: {result.inserted_id}")
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Failed to create image: {e}", exc_info=True)
            raise Exception(f"Failed to create image: {e}")
    
    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        Get image by ID.
        
        Args:
            image_id: Image ID
            
        Returns:
            Optional[Dict]: Image data with ObjectIds converted to strings
            
        Raises:
            ValueError: If image_id is invalid
            Exception: For other errors
        """
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(image_id):
                logger.info(f"Invalid ObjectId format: {image_id}")
                raise ValueError(f"Invalid ObjectId format: {image_id}")
            
            image = self.images.find_one({"_id": ObjectId(image_id)})
            if image:
                # Convert all ObjectIds to strings for proper serialization
                self.db.convert_objectids_to_str(image)
            return image
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error in get_image: {e}", exc_info=True)
            raise Exception(f"Error in get_image: {e}")
    
    def get_images_by_dataset(
        self, 
        dataset_id: str, 
        skip: int = 0, 
        limit: int = 100, 
        split: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get images by dataset ID with optional split filter.
        
        Args:
            dataset_id: Dataset ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            split: Optional split filter (train/val/test)
            
        Returns:
            List[Dict]: List of images with annotations
            
        Raises:
            ValueError: If dataset_id is invalid
            Exception: For other errors
        """
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(dataset_id):
                logger.info(f"Invalid ObjectId format: {dataset_id}")
                raise ValueError(f"Invalid ObjectId format: {dataset_id}")
            
            query = {"dataset_id": ObjectId(dataset_id)}
            if split:
                query["split"] = split
                
            cursor = self.images.find(query).skip(skip).limit(limit)
            images = []
            for image in cursor:
                image["id"] = str(image["_id"])
                del image["_id"]  # Remove _id and use id instead
                image["dataset_id"] = str(image["dataset_id"])
                self.db.convert_objectids_to_str(image)
                images.append(image)
            return images
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error in get_images_by_dataset: {e}", exc_info=True)
            raise Exception(f"Error in get_images_by_dataset: {e}")
    
    def count_images(self, dataset_id: str, split: Optional[str] = None) -> int:
        """
        Count images in dataset.
        
        Args:
            dataset_id: Dataset ID
            split: Optional split filter (train/val/test)
            
        Returns:
            int: Number of images
            
        Raises:
            ValueError: If dataset_id is invalid
            Exception: For other errors
        """
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(dataset_id):
                logger.info(f"Invalid ObjectId format: {dataset_id}")
                raise ValueError(f"Invalid ObjectId format: {dataset_id}")
            
            query = {"dataset_id": ObjectId(dataset_id)}
            if split:
                query["split"] = split
            return self.images.count_documents(query)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error in count_images: {e}", exc_info=True)
            raise Exception(f"Error in count_images: {e}")
    
    def delete_images_by_dataset(self, dataset_id: str) -> int:
        """
        Delete all images in a dataset.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            int: Number of deleted images
            
        Raises:
            ValueError: If dataset_id is invalid
            Exception: For other errors
        """
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(dataset_id):
                logger.info(f"Invalid ObjectId format: {dataset_id}")
                raise ValueError(f"Invalid ObjectId format: {dataset_id}")
            
            result = self.images.delete_many({"dataset_id": ObjectId(dataset_id)})
            logger.info(f"Deleted {result.deleted_count} images from dataset {dataset_id}")
            return result.deleted_count
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error in delete_images_by_dataset: {e}", exc_info=True)
            raise Exception(f"Error in delete_images_by_dataset: {e}")
    
    def delete_image(self, image_id: str) -> bool:
        """
        Delete a single image.
        
        Args:
            image_id: Image ID
            
        Returns:
            bool: True if successful
            
        Raises:
            ValueError: If image_id is invalid
            Exception: For other errors
        """
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(image_id):
                logger.info(f"Invalid ObjectId format: {image_id}")
                raise ValueError(f"Invalid ObjectId format: {image_id}")
            
            result = self.images.delete_one({"_id": ObjectId(image_id)})
            if result.deleted_count > 0:
                logger.info(f"Deleted image: {image_id}")
            return result.deleted_count > 0
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error in delete_image: {e}", exc_info=True)
            raise Exception(f"Error in delete_image: {e}")


# Global Image service instance
image_service = ImageService()

