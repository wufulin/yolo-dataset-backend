"""
YOLO Dataset Initialization Script
Reads YOLO format datasets and inserts them into MongoDB

Usage:
    python scripts/init_dataset.py
"""

import sys
import os
import yaml
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from bson import ObjectId
from PIL import Image
from minio import Minio
from minio.error import S3Error

from app.config import settings
from app.utils.logger import get_logger

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
    
    def parse_yolo_annotation(self, label_path: Path, class_names: List[str]) -> List[Dict[str, Any]]:
        """
        Parse YOLO format annotation file
        
        Args:
            label_path: Path to annotation file
            class_names: List of class names
        
        Returns:
            List of annotations
        """
        annotations = []
        
        if not label_path.exists():
            return annotations
        
        with open(label_path, 'r') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                parts = line.split()
                if len(parts) < 5:
                    logger.error(f"  ⚠ Skipping invalid line {line_num}: {line}")
                    continue
                
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                
                # Validate normalized coordinates
                if not (0 <= x_center <= 1 and 0 <= y_center <= 1 and 0 <= width <= 1 and 0 <= height <= 1):
                    logger.error(f"  ⚠ Skipping out-of-range annotation line {line_num}: {line}")
                    continue
                
                if class_id >= len(class_names):
                    logger.error(f"  ⚠ Skipping unknown class ID {class_id} (line {line_num})")
                    continue
                
                annotation = {
                    "_id": ObjectId(),
                    "annotation_type": "detect",
                    "class_id": class_id,
                    "class_name": class_names[class_id],
                    "bbox": {
                        "x_center": x_center,
                        "y_center": y_center,
                        "width": width,
                        "height": height
                    },
                    "confidence": None,
                    "is_crowd": False,
                    "area": width * height,
                    "metadata": {},
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                annotations.append(annotation)
                
            except (ValueError, IndexError) as e:
                logger.error(f"  ⚠ Parse error (line {line_num}): {e}")
                continue
        
        return annotations
    
    def create_dataset(self) -> str:
        """
        Create dataset record
        
        Returns:
            Dataset ID
        """
        # Check if dataset with same name already exists
        existing = self.datasets_collection.find_one({"name": "COCO8-Detect"})
        if existing:
            logger.error(f"⚠ Dataset 'COCO8-Detect' already exists, deleting old data...")
            self.datasets_collection.delete_one({"_id": existing["_id"]})
            self.images_collection.delete_many({"dataset_id": existing["_id"]})
        
        dataset_doc = {
            "_id": ObjectId(),
            "name": "COCO8-Detect",
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
        Process a single dataset split
        
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
        image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
        
        logger.info(f"\nProcessing {split_name} split:")
        logger.info(f"  Number of images: {len(image_files)}")
        
        image_count = 0
        annotation_count = 0
        total_file_size = 0
        
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
                annotations = self.parse_yolo_annotation(label_path, self.class_names)
                
                # Set image_id and dataset_id for annotations
                image_id = ObjectId()
                for ann in annotations:
                    ann["image_id"] = image_id
                    ann["dataset_id"] = self.dataset_id
                
                # MinIO path format: datasets/{dataset_id}/images/{split}/{filename}
                minio_file_path = f"datasets/{str(self.dataset_id)}/images/{split_name}/{image_path.name}"
                
                # Upload image to MinIO
                upload_success = self.upload_to_minio(image_path, minio_file_path)
                if not upload_success:
                    logger.error(f"  ✗ Skipped {image_path.name}: MinIO upload failed")
                    continue
                
                # Create image document
                image_doc = {
                    "_id": image_id,
                    "dataset_id": self.dataset_id,
                    "filename": image_path.name,
                    "file_path": minio_file_path,  # MinIO storage path
                    "file_size": file_size,
                    "file_hash": file_hash,
                    "width": width,
                    "height": height,
                    "channels": 3,
                    "format": img_format,
                    "split": split_name,
                    "annotations": annotations,
                    "metadata": {
                        "source": "coco8-detect",
                        "original_path": str(image_path.relative_to(self.dataset_path))
                    },
                    "is_annotated": len(annotations) > 0,
                    "annotation_count": len(annotations),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                # Insert into database
                self.images_collection.insert_one(image_doc)
                
                image_count += 1
                annotation_count += len(annotations)
                
                logger.info(f"  ✓ {image_path.name}: {width}x{height}, {len(annotations)} annotations, {file_size/1024:.1f}KB [Uploaded to MinIO]")
                
            except Exception as e:
                logger.error(f"  ✗ Processing failed {image_path.name}: {e}", exc_info=True)
                continue
        
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
    # COCO8 dataset path
    dataset_path = "data/coco8-detect"
    
    # Check if path exists
    if not os.path.exists(dataset_path):
        logger.error(f"✗ Error: Dataset path does not exist: {dataset_path}")
        sys.exit(1)
    
    # Create importer and execute import
    importer = YOLODatasetImporter(dataset_path)
    importer.import_dataset()


if __name__ == "__main__":
    main()