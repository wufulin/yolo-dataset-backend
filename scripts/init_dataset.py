"""
YOLO Dataset Initialization Script
Reads YOLO format datasets and inserts them into MongoDB

Usage:
    python scripts/init_dataset.py
"""
import argparse
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple
import yaml

from bson import ObjectId
from minio import Minio
from minio.error import S3Error
from PIL import Image
from pymongo import MongoClient

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.utils.logger import get_logger
from app.services.minio_service import minio_service
from app.services import image_service
from app.utils import yolo_validator

logger = get_logger(__name__)


class YOLODatasetImporter:
    """YOLO Dataset Importer"""
    
    def __init__(self, dataset_path: str):
        """
        Initialize the importer
        
        Args:
            dataset_path: Root directory path of the dataset
        """
        self.dataset_path = Path(dataset_path)
        self.yaml_path = self.dataset_path / "coco8.yaml"
        
        # Connect to MongoDB
        self.client = MongoClient(settings.mongodb_url)
        self.db = self.client[settings.mongo_db_name]
        self.datasets_collection = self.db.datasets
        self.images_collection = self.db.images
        
        # Connect to MinIO
        self.minio_client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket_name
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
        
        # Dataset information
        self.dataset_config = None
        self.class_names = []
        self.dataset_id = None
        
        logger.info(f"✓ Connected to MongoDB: {settings.mongo_db_name}")
        logger.info(f"✓ Connected to MinIO: {settings.minio_endpoint}")
    
    def _ensure_bucket_exists(self):
        """Ensure MinIO bucket exists, create if not exists"""
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"✓ Created MinIO bucket: {self.bucket_name}")
            else:
                logger.info(f"✓ MinIO bucket exists: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"⚠ MinIO bucket check/creation failed: {e}")
            raise
    
    def upload_to_minio(self, local_path: Path, minio_path: str) -> bool:
        """
        Upload file to MinIO
        
        Args:
            local_path: Local file path
            minio_path: Object path in MinIO
        
        Returns:
            Whether upload was successful
        """
        try:
            # Determine content type
            content_type = "image/jpeg"
            if local_path.suffix.lower() in ['.png']:
                content_type = "image/png"
            elif local_path.suffix.lower() in ['.jpg', '.jpeg']:
                content_type = "image/jpeg"
            
            # Upload file
            self.minio_client.fput_object(
                self.bucket_name,
                minio_path,
                str(local_path),
                content_type=content_type
            )
            return True
        except S3Error as e:
            logger.error(f"  ⚠ MinIO upload failed: {e}")
            return False
    
    def load_yaml_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.yaml_path}")
        
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.dataset_config = config
        self.class_names = [config['names'][i] for i in sorted(config['names'].keys())]
        
        logger.info(f"✓ Loaded config file")
        logger.info(f"  Number of classes: {len(self.class_names)}")
        logger.info(f"  Class list: {', '.join(self.class_names[:10])}{'...' if len(self.class_names) > 10 else ''}")
        
        return config
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file MD5 hash"""
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def get_image_info(self, image_path: Path) -> Tuple[int, int, str]:
        """
        Get image information
        
        Returns:
            (width, height, format)
        """
        with Image.open(image_path) as img:
            width, height = img.size
            img_format = img.format.lower() if img.format else 'jpg'
            return width, height, img_format
    
    
    def create_dataset(self) -> str:
        """
        Create dataset record
        
        Returns:
            Dataset ID
        """
        # Check if dataset with same name already exists
        dataset_name = self.dataset_path.name
        existing = self.datasets_collection.find_one({"name": dataset_name})
        if existing:
            logger.error(f"⚠ Dataset {dataset_name} already exists, deleting old data...")
            self.datasets_collection.delete_one({"_id": existing["_id"]})
            self.images_collection.delete_many({"dataset_id": existing["_id"]})
        
        dataset_doc = {
            "_id": ObjectId(),
            "name": dataset_name,
            "description": "COCO8 dataset for object detection (first 8 images from COCO train2017)",
            "dataset_type": "detect",
            "class_names": self.class_names,
            "num_images": 0,  # Will be updated later
            "num_annotations": 0,  # Will be updated later
            "splits": {
                "train": 0,
                "val": 0
            },
            "status": "processing",
            "error_message": None,
            "file_size": 0,  # Will be updated with total dataset size
            "storage_path": None,  # No longer recording local path
            "created_by": "admin",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "version": 1
        }
        
        result = self.datasets_collection.insert_one(dataset_doc)
        self.dataset_id = result.inserted_id
        
        logger.info(f"✓ Created dataset record (ID: {self.dataset_id})")
        return str(self.dataset_id)
    
    def process_split(self, split_name: str) -> Tuple[int, int, int]:
        """
        Process a single dataset split with batch upload for better performance
        
        Args:
            split_name: Split name (train/val)
        
        Returns:
            (image_count, annotation_count, total_file_size)
        """
        images_dir = self.dataset_path / "images" / split_name
        labels_dir = self.dataset_path / "labels" / split_name
        
        if not images_dir.exists():
            logger.error(f"  ⚠ Images directory not found: {images_dir}")
            return 0, 0, 0
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        # find all image files based on the image_extensions
        image_files = [f for f in images_dir.glob("*") if f.suffix.lower() in image_extensions]
        
        logger.info(f"\nProcessing {split_name} split:")
        logger.info(f"  Number of images: {len(image_files)}")
        
        # Phase 1: Prepare all image data and upload list
        logger.info(f"  Phase 1: Preparing image data...")
        upload_list = []
        image_data_list = []
        total_file_size = 0
        dataset_type = yolo_validator.get_dataset_type(self.dataset_path)
        
        for image_path in image_files:
            try:
                # Get image information
                width, height, img_format = self.get_image_info(image_path)
                file_size = image_path.stat().st_size
                file_hash = self.calculate_file_hash(image_path)
                
                # Accumulate file size
                total_file_size += file_size
                
                # Corresponding label file
                label_path = labels_dir / f"{image_path.stem}.txt"
                
                # Parse annotations
                annotations = yolo_validator.parse_annotations(label_path, dataset_type, self.class_names)
                
                # Set image_id and dataset_id for annotations
                image_id = ObjectId()
                for ann in annotations:
                    ann["image_id"] = image_id
                    ann["dataset_id"] = self.dataset_id
                
                # MinIO path format: {user_id}/{dataset_id}/images/{split}/{filename}
                minio_file_path = f"691c3f00ca496bc2f41f0993/{str(self.dataset_id)}/images/{split_name}/{image_path.name}"
                
                # Determine content type
                content_type = "image/jpeg"
                if image_path.suffix.lower() in ['.png']:
                    content_type = "image/png"
                elif image_path.suffix.lower() in ['.jpg', '.jpeg']:
                    content_type = "image/jpeg"
                elif image_path.suffix.lower() in ['.bmp']:
                    content_type = "image/bmp"
                elif image_path.suffix.lower() in ['.tiff', '.tif']:
                    content_type = "image/tiff"
                
                # Add to upload list: (local_path, minio_path, content_type)
                upload_list.append((str(image_path), minio_file_path, content_type))
                
                # Store image data for later database insertion
                image_data_list.append({
                    "_id": image_id,
                    "dataset_id": self.dataset_id,
                    "filename": image_path.name,
                    "file_path": minio_file_path,
                    "file_size": file_size,
                    "file_hash": file_hash,
                    "width": width,
                    "height": height,
                    "channels": 3,
                    "format": img_format,
                    "split": split_name,
                    "annotations": annotations,
                    "metadata": {
                        "source": self.dataset_path.name,
                        "original_path": str(image_path.relative_to(self.dataset_path))
                    },
                    "is_annotated": len(annotations) > 0,
                    "annotation_count": len(annotations),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                
                logger.info(f"  ✓ Prepared {image_path.name}: {width}x{height}, {len(annotations)} annotations, {file_size/1024:.1f}KB")
                
            except Exception as e:
                logger.error(f"  ✗ Failed to prepare {image_path.name}: {e}", exc_info=True)
                continue
        
        # Phase 2: Batch upload to MinIO
        logger.info(f"\n  Phase 2: Batch uploading {len(upload_list)} images to MinIO...")
        upload_result = minio_service.upload_files(
            upload_list,
            max_workers=15,  # Use more workers for better performance
            max_retries=3,
            retry_delay=1.0
        )
        
        logger.info(f"  Upload completed: {upload_result['successful']}/{upload_result['total']} successful")
        if upload_result['retry_info']['total_retries'] > 0:
            logger.info(f"  Retries performed: {upload_result['retry_info']['total_retries']}")
        
        # Phase 3: Insert successfully uploaded images to database
        logger.info(f"\n  Phase 3: Inserting image records to database...")
        successful_paths = set(upload_result['success_list'])
        
        image_count = 0
        annotation_count = 0
        images_to_insert = []
        
        for image_data in image_data_list:
            if image_data["file_path"] in successful_paths:
                images_to_insert.append(image_data)
                annotation_count += len(image_data["annotations"])
        
        # Batch insert to database
        if images_to_insert:
            inserted_count = image_service.bulk_save_images(images_to_insert)
            image_count = inserted_count
        
        # Log failed uploads
        if upload_result['failed_list']:
            logger.warning(f"\n  ⚠ {len(upload_result['failed_list'])} images failed to upload:")
            for failed in upload_result['failed_list'][:10]:  # Show first 10 failures
                logger.warning(f"    - {failed['object_name']}: {failed['error']}")
            if len(upload_result['failed_list']) > 10:
                logger.warning(f"    ... and {len(upload_result['failed_list']) - 10} more")
        
        logger.info(f"\n  Split summary:")
        logger.info(f"    Images processed: {image_count}")
        logger.info(f"    Annotations: {annotation_count}")
        logger.info(f"    Total size: {total_file_size / 1024 / 1024:.2f} MB")
        
        return image_count, annotation_count, total_file_size
    
    def update_dataset_stats(self, train_images: int, train_annotations: int, train_size: int,
                            val_images: int, val_annotations: int, val_size: int):
        """Update dataset statistics"""
        total_size = train_size + val_size
        
        self.datasets_collection.update_one(
            {"_id": self.dataset_id},
            {
                "$set": {
                    "num_images": train_images + val_images,
                    "num_annotations": train_annotations + val_annotations,
                    "file_size": total_size,  # Total dataset size
                    "splits": {
                        "train": train_images,
                        "val": val_images
                    },
                    "status": "active",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"\n✓ Dataset statistics updated")
        logger.info(f"  Total images: {train_images + val_images}")
        logger.info(f"  Total annotations: {train_annotations + val_annotations}")
        logger.info(f"  Dataset size: {total_size / 1024 / 1024:.2f} MB")
        logger.info(f"  Train set: {train_images} images, {train_annotations} annotations, {train_size / 1024 / 1024:.2f} MB")
        logger.info(f"  Val set: {val_images} images, {val_annotations} annotations, {val_size / 1024 / 1024:.2f} MB")
    
    def import_dataset(self):
        """Execute complete dataset import workflow"""
        logger.info("=" * 60)
        logger.info("YOLO Dataset Import Tool")
        logger.info("=" * 60)
        
        try:
            # 1. Load configuration
            self.load_yaml_config()
            
            # 2. Create dataset record
            self.create_dataset()
            
            # 3. Process training set
            train_images, train_annotations, train_size = self.process_split("train")
            
            # 4. Process validation set
            val_images, val_annotations, val_size = self.process_split("val")
            
            # 5. Update statistics
            self.update_dataset_stats(
                train_images, train_annotations, train_size,
                val_images, val_annotations, val_size
            )
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ Dataset import successful!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"\n✗ Import failed: {e}", exc_info=True)
            # If failed, update dataset status to error
            if self.dataset_id:
                self.datasets_collection.update_one(
                    {"_id": self.dataset_id},
                    {
                        "$set": {
                            "status": "error",
                            "error_message": str(e),
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
            raise
        
        finally:
            self.client.close()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Initialize YOLO dataset")
    parser.add_argument("--dataset_path", type=str, default="../data/coco8-detect-1024MB", help="Path to the dataset")
    
    args = parser.parse_args()

    dataset_path = args.dataset_path

    # Check if path exists
    if not os.path.exists(dataset_path):
        logger.error(f"✗ Error: Dataset path does not exist: {dataset_path}")
        sys.exit(1)
    
    # Create importer and execute import
    importer = YOLODatasetImporter(dataset_path)
    importer.import_dataset()


if __name__ == "__main__":
    main()