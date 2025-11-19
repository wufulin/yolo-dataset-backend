"""Service for handling dataset operations."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.dataset import Dataset, ImageMetadata
from app.services.db_service import db_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatasetService:
    """Service class for Dataset operations."""
    
    def __init__(self):
        """Initialize Dataset service."""
        self.db = db_service
        self.datasets = self.db.datasets
        self.images = self.db.images
    
    def create_dataset(self, dataset: Dataset) -> str:
        """
        Create a new dataset with error handling.
        
        Args:
            dataset: Dataset object to create
            
        Returns:
            str: Created dataset ID
            
        Raises:
            ValueError: If dataset name already exists
            Exception: For other database errors
        """
        try:
            dataset_dict = dataset.model_dump(by_alias=True, mode='python')
            
            # Ensure _id is ObjectId
            if "_id" in dataset_dict and isinstance(dataset_dict["_id"], str):
                dataset_dict["_id"] = ObjectId(dataset_dict["_id"])
                                
            result = self.datasets.insert_one(dataset_dict)
            
            # Verify insertion was successful
            if not result.acknowledged:
                logger.error("Dataset insertion was not acknowledged by MongoDB")
                raise Exception("Dataset insertion was not acknowledged by MongoDB")
            
            if not result.inserted_id:
                logger.error("No dataset ID returned from MongoDB")
                raise Exception("No dataset ID returned from MongoDB")
            
            logger.info(f"Inserted dataset ID: {result.inserted_id}")
            
            return str(result.inserted_id)
            
        except DuplicateKeyError:
            logger.error(f"Dataset with name '{dataset.name}' already exists")
            raise ValueError(f"Dataset with name '{dataset.name}' already exists")
        except PyMongoError as e:
            logger.error(f"Failed to create dataset: {e}", exc_info=True)
            raise Exception(f"Failed to create dataset: {e}")
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset by ID.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            Optional[Dict]: Dataset data or None
        """
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(dataset_id):
                logger.info(f"Invalid ObjectId format: {dataset_id}")
                raise ValueError(f"Invalid ObjectId format: {dataset_id}")
            
            dataset = self.datasets.find_one({"_id": ObjectId(dataset_id)})
            return dataset
        except Exception as e:
            logger.error(f"Error in get_dataset: {e}", exc_info=True)
            raise Exception(f"Error in get_dataset: {e}")
    
    def list_datasets(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all datasets with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[Dict]: List of datasets
        """
        cursor = self.datasets.find().skip(skip).limit(limit).sort("created_at", -1)
        datasets = []
        for dataset in cursor:
            dataset["id"] = str(dataset["_id"])
            del dataset["_id"]  # Remove _id and use id instead
            # Convert any other ObjectId fields to string
            for key, value in dataset.items():
                if isinstance(value, ObjectId):
                    dataset[key] = str(value)
            datasets.append(dataset)
        return datasets
    
    def update_dataset_stats(self, dataset_id: str, num_images: int, 
                           num_annotations: int, splits: Dict[str, int]) -> bool:
        """
        Update dataset statistics.
        
        Args:
            dataset_id: Dataset ID
            num_images: Number of images
            num_annotations: Number of annotations
            splits: Split counts
            
        Returns:
            bool: True if successful
        """
        result = self.datasets.update_one(
            {"_id": ObjectId(dataset_id)},
            {
                "$set": {
                    "num_images": num_images,
                    "num_annotations": num_annotations,
                    "splits": splits,
                    "updated_at": Dataset.get_current_time()
                }
            }
        )
        return result.modified_count > 0
    
    def create_image(self, image: ImageMetadata) -> str:
        """
        Create image metadata.
        
        Args:
            image: ImageMetadata object
            
        Returns:
            str: Created image ID
        """
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
        return str(result.inserted_id)
    
    def get_images_by_dataset(self, dataset_id: str, skip: int = 0, 
                            limit: int = 100, split: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get images by dataset ID with optional split filter.
        
        Args:
            dataset_id: Dataset ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            split: Optional split filter
            
        Returns:
            List[Dict]: List of images with annotations
        """
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
    
    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        Get image by ID.
        
        Args:
            image_id: Image ID
            
        Returns:
            Optional[Dict]: Image data or None
        """
        image = self.images.find_one({"_id": ObjectId(image_id)})
        if image:
            image["id"] = str(image["_id"])
            del image["_id"]  # Remove _id and use id instead
            image["dataset_id"] = str(image["dataset_id"])
            self.db.convert_objectids_to_str(image)
        return image
    
    def count_images(self, dataset_id: str, split: Optional[str] = None) -> int:
        """
        Count images in dataset.
        
        Args:
            dataset_id: Dataset ID
            split: Optional split filter
            
        Returns:
            int: Number of images
        """
        query = {"dataset_id": ObjectId(dataset_id)}
        if split:
            query["split"] = split
        return self.images.count_documents(query)
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete dataset and all associated images.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            bool: True if successful
        """
        # Delete all images in the dataset
        self.images.delete_many({"dataset_id": ObjectId(dataset_id)})
        
        # Delete the dataset
        result = self.datasets.delete_one({"_id": ObjectId(dataset_id)})
        return result.deleted_count > 0


# Global Dataset service instance
dataset_service = DatasetService()

