"""Service for handling dataset operations."""
from datetime import datetime
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
            if not ObjectId.is_valid(dataset_id):
                logger.info(f"Invalid ObjectId format: {dataset_id}")
                raise ValueError(f"Invalid ObjectId format: {dataset_id}")

            dataset = self.datasets.find_one({"_id": ObjectId(dataset_id)})
            if dataset:
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

    def update_dataset_stats(
        self,
        dataset_id: str,
        train_images: int,
        train_annotations: int,
        train_size: int,
        val_images: int,
        val_annotations: int,
        val_size: int,
        test_images: int,
        test_annotations: int,
        test_size: int
    ):
        """
        Update dataset statistics in MongoDB for a given dataset.

        Args:
            dataset_id: The ID of the dataset to update
            train_images: Number of train images
            train_annotations: Number of train annotations
            train_size: Total size of train images (in bytes)
            val_images: Number of val images
            val_annotations: Number of val annotations
            val_size: Total size of val images (in bytes)
        """
        total_size = train_size + val_size + test_size
        total_images = train_images + val_images + test_images
        total_annotations = train_annotations + val_annotations + test_annotations

        try:
            result = self.datasets.update_one(
                {"_id": ObjectId(dataset_id)},
                {
                    "$set": {
                        "num_images": total_images,
                        "num_annotations": total_annotations,
                        "file_size": total_size,
                        "splits": {
                            "train": train_images,
                            "val": val_images,
                            "test": test_images
                        },
                        "status": "active",
                        "updated_at": datetime.utcnow(),
                    }
                }
            )
            if result.modified_count == 0:
                logger.warning(f"No dataset updated for id {dataset_id}")
            logger.info(f"\n✓ Dataset statistics updated")
            logger.info(f"  Total images: {total_images}")
            logger.info(f"  Total annotations: {total_annotations}")
            logger.info(f"  Dataset size: {total_size / 1024 / 1024:.2f} MB")
            logger.info(
                f"  Train set: {train_images} images, {train_annotations} annotations, {train_size / 1024 / 1024:.2f} MB"
            )
            logger.info(
                f"  Val set: {val_images} images, {val_annotations} annotations, {val_size / 1024 / 1024:.2f} MB"
            )
            logger.info(
                f"  Test set: {test_images} images, {test_annotations} annotations, {test_size / 1024 / 1024:.2f} MB"
            )
        except Exception as e:
            logger.error(f"Failed to update dataset stats: {e}", exc_info=True)
            raise Exception(f"Failed to update dataset stats: {e}")


# Global Dataset service instance
dataset_service = DatasetService()
