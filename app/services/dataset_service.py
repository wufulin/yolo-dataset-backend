"""Service for handling dataset operations."""
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.dataset import Dataset
from app.services.db_service import db_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatasetService:
    """Service class for Dataset operations."""
    
    def __init__(self):
        """Initialize Dataset service."""
        self.db = db_service
        self.datasets = self.db.datasets
    
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
            dataset_dict = dataset.model_dump(by_alias=True)
                                
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
            Optional[Dict]: Dataset data with ObjectIds converted to strings
        """
        try:
            # Validate ObjectId format
            if not ObjectId.is_valid(dataset_id):
                logger.info(f"Invalid ObjectId format: {dataset_id}")
                raise ValueError(f"Invalid ObjectId format: {dataset_id}")
            
            dataset = self.datasets.find_one({"_id": ObjectId(dataset_id)})
            if dataset:
                # Convert all ObjectIds to strings for proper serialization
                self.db.convert_objectids_to_str(dataset)
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
            self.db.convert_objectids_to_str(dataset)
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


# Global Dataset service instance
dataset_service = DatasetService()

