"""MongoDB service for handling dataset and annotation operations."""
from typing import Dict, List, Optional, Any
from bson import ObjectId
from pymongo import MongoClient, ReturnDocument, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError, DuplicateKeyError, OperationFailure
from app.config import settings
from app.models.dataset import Dataset, ImageMetadata, UploadSession


class MongoService:
    """Service class for MongoDB operations."""
    
    def __init__(self, max_pool_size: int = 50, retry_writes: bool = True):
        """Initialize MongoDB client with connection pooling."""
        self.client = MongoClient(
            settings.mongodb_url,
            maxPoolSize=max_pool_size,
            retryWrites=retry_writes,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        self.db = self.client[settings.mongo_db_name]
        self.datasets = self.db.datasets
        self.images = self.db.images
        self.upload_sessions = self.db.upload_sessions
        self.dataset_statistics = self.db.dataset_statistics
        self.users = self.db.users
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test database connection."""
        try:
            self.client.admin.command('ping')
            print("Successfully connected to MongoDB")
        except PyMongoError as e:
            raise Exception(f"Failed to connect to MongoDB: {e}")
    
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
            result = self.datasets.insert_one(dataset.dict(by_alias=True))
            return str(result.inserted_id)
        except DuplicateKeyError:
            raise ValueError(f"Dataset with name '{dataset.name}' already exists")
        except PyMongoError as e:
            raise Exception(f"Failed to create dataset: {e}")
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset by ID.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            Optional[Dict]: Dataset data or None
        """
        dataset = self.datasets.find_one({"_id": ObjectId(dataset_id)})
        if dataset:
            dataset["id"] = str(dataset["_id"])
        return dataset
    
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
        result = self.images.insert_one(image.dict(by_alias=True))
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
            image["dataset_id"] = str(image["dataset_id"])
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
            image["dataset_id"] = str(image["dataset_id"])
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


# Global MongoDB service instance
mongo_service = MongoService()