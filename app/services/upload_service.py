"""Service for handling dataset upload operations."""

import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bson import ObjectId
from fastapi import HTTPException, status
from PIL import Image

from app.config import settings
from app.models.dataset import Dataset
from app.services import dataset_service, image_service, minio_service
from app.utils import yolo_validator
from app.utils.file_utils import safe_remove
from app.utils.logger import get_logger

logger = get_logger(__name__)


class UploadService:
    """Service class for upload operations."""

    def __init__(self):
        """Initialize Upload service."""
        pass

    async def process_dataset(self, zip_path: str, dataset_info: Any) -> Dict[str, Any]:
        """
        Process uploaded dataset ZIP file.

        Args:
            zip_path: Path to ZIP file
            dataset_info: Dataset metadata

        Returns:
            Dict[str, Any]: Processing results
        """
        if not dataset_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dataset info is required",
            )

        extract_dir = os.path.join(settings.temp_dir, f"extract_{uuid.uuid4()}")
        try:
            # dataset_root = Path(yolo_validator.extract_zip(zip_path, extract_dir))

            dataset_root = Path(Path(zip_path).parent / "coco8-detect").resolve()
            logger.info(f"******Dataset root: {dataset_root}")

            dataset_type = getattr(dataset_info, "dataset_type", "detect") or "detect"

            dataset_yaml_path = yolo_validator.find_dataset_yaml(str(dataset_root))

            yaml_data = yolo_validator.parse_dataset_yaml(str(dataset_yaml_path))

            is_valid, message = yolo_validator.validate_dataset(
                dataset_yaml_path, dataset_type
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid YOLO dataset: {message}",
                )

            class_names = [yaml_data['names'][i] for i in sorted(yaml_data['names'].keys())]

            dataset = Dataset(
                name=getattr(dataset_info, "name", dataset_root.name),
                description=getattr(dataset_info, "description", ""),
                dataset_type=dataset_type,
                class_names=class_names,
                num_images=0,
                num_annotations=0,
                splits={"train": 0, "val": 0, "test": 0},
                status="processing",
                error_message=None,
                file_size=0,
                storage_path=None,
                created_by="admin",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version=1,
            )

            dataset_id = dataset_service.create_dataset(dataset)

            processed_count = await self._process_images_and_annotations(
                dataset_root,
                dataset_id,
                dataset_type,
                class_names,
            )

            return {
                "status": "success",
                "dataset_id": dataset_id,
                "processed_images": processed_count,
                "dataset_type": dataset_type,
            }
        finally:
            pass
            # safe_remove(extract_dir)
            # safe_remove(zip_path)

    async def _process_images_and_annotations(
        self,
        dataset_root: Path,
        dataset_id: str,
        dataset_type: str,
        class_names: List[str],
    ) -> int:
        """
        Process all images and annotations in dataset.

        Args:
            dataset_root: Root directory of dataset
            dataset_id: Dataset ID in MongoDB
            dataset_type: Type of dataset
            class_names: List of class names

        Returns:
            int: Number of processed images
        """
        train_images, train_annotations, train_size = self.process_split(
            dataset_root,
            "train",
            dataset_id,
            dataset_type,
            class_names,
        )

        val_images, val_annotations, val_size = self.process_split(
            dataset_root,
            "val",
            dataset_id,
            dataset_type,
            class_names,
        )

        test_images, test_annotations, test_size = self.process_split(
            dataset_root,
            "test",
            dataset_id,
            dataset_type,
            class_names,
        )

        dataset_service.update_dataset_stats(
            dataset_id,
            train_images,
            train_annotations,
            train_size,
            val_images,
            val_annotations,
            val_size,
            test_images,
            test_annotations,
            test_size,
        )

        return train_images + val_images + test_images

    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate file MD5 hash.

        Args:
            file_path: Path to the file

        Returns:
            str: MD5 hash of the file
        """
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _get_image_info(self, image_path: Path) -> Tuple[int, int, str]:
        """
        Get image information.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple[int, int, str]: (width, height, format)
        """
        with Image.open(image_path) as img:
            width, height = img.size
            img_format = img.format.lower() if img.format else "jpg"
            return width, height, img_format

    def process_split(
        self,
        dataset_root: Path,
        split_name: str,
        dataset_id: str,
        dataset_type: str,
        class_names: List[str],
        user_id: str = "691c3f00ca496bc2f41f0993",
    ) -> Tuple[int, int, int]:
        """
        Process a single dataset split with batch upload for better performance.

        Args:
            dataset_root: Root directory path of the dataset
            split_name: Split name (train/val/test)
            dataset_id: Dataset ID
            class_names: List of class names
            user_id: User ID for MinIO path (default: "691c3f00ca496bc2f41f0993")

        Returns:
            Tuple[int, int, int]: (image_count, annotation_count, total_file_size)
        """
        dataset_root_path = Path(dataset_root)
        images_dir = dataset_root_path / "images" / split_name
        labels_dir = dataset_root_path / "labels" / split_name

        if not images_dir.exists():
            logger.error(f"  ⚠ Images directory not found: {images_dir}")
            return 0, 0, 0

        if not labels_dir.exists():
            logger.error(f"  ⚠ Labels directory not found: {labels_dir}")
            return 0, 0, 0

        # Get all image files
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
        # find all image files based on the image_extensions
        image_files = [
            f for f in images_dir.glob("*") if f.suffix.lower() in image_extensions
        ]

        logger.info(f"\nProcessing {split_name} split:")
        logger.info(f"  Number of images: {len(image_files)}")

        # Phase 1: Prepare all image documents and upload list
        logger.info(f"  Phase 1: Preparing image data...")
        upload_list = []
        image_doc_list = []
        total_file_size = 0

        for image_path in image_files:
            try:
                # Get image information
                width, height, img_format = self._get_image_info(image_path)
                file_size = image_path.stat().st_size
                file_hash = self._calculate_file_hash(image_path)

                # Accumulate file size
                total_file_size += file_size

                # Corresponding label file
                label_path = labels_dir / f"{image_path.stem}.txt"

                # Parse annotations
                annotations = yolo_validator.parse_annotations(
                    str(label_path),
                    dataset_type,
                    class_names,
                )

                # Set image_id and dataset_id for annotations
                image_id = ObjectId()
                for ann in annotations:
                    ann["image_id"] = image_id
                    ann["dataset_id"] = ObjectId(dataset_id)

                # MinIO path format: {user_id}/{dataset_id}/images/{split}/{filename}
                minio_file_path = (
                    f"{user_id}/{dataset_id}/images/{split_name}/{image_path.name}"
                )

                # Determine content type
                content_type = "image/jpeg"
                if image_path.suffix.lower() in [".png"]:
                    content_type = "image/png"
                elif image_path.suffix.lower() in [".jpg", ".jpeg"]:
                    content_type = "image/jpeg"
                elif image_path.suffix.lower() in [".bmp"]:
                    content_type = "image/bmp"
                elif image_path.suffix.lower() in [".tiff", ".tif"]:
                    content_type = "image/tiff"

                # Add to upload list: (local_path, minio_path, content_type)
                upload_list.append((str(image_path), minio_file_path, content_type))

                # Store image data for later database insertion
                image_doc_list.append(
                    {
                        "_id": image_id,
                        "dataset_id": ObjectId(dataset_id),
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
                        "metadata": {},
                        "is_annotated": len(annotations) > 0,
                        "annotation_count": len(annotations),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                )
            except Exception as e:
                logger.error(
                    f"  ✗ Failed to prepare {image_path.name}: {e}", exc_info=True
                )
                continue

        # Phase 2: Batch upload to MinIO
        logger.info(
            f"\n  Phase 2: Batch uploading {len(upload_list)} images to MinIO..."
        )
        upload_result = minio_service.upload_files(
            upload_list,
            max_workers=15,  # Use more workers for better performance
            max_retries=3,
            retry_delay=1.0,
        )

        logger.info(
            f"  Upload completed: {upload_result['successful']}/{upload_result['total']} successful"
        )
        if upload_result["retry_info"]["total_retries"] > 0:
            logger.info(
                f"  Retries performed: {upload_result['retry_info']['total_retries']}"
            )

        # Phase 3: Insert successfully uploaded image docs to database
        logger.info(f"\n  Phase 3: Inserting image docs into database...")
        successful_paths = set(upload_result["success_list"])

        image_count = 0
        annotation_count = 0
        images_to_insert = []

        for image in image_doc_list:
            if image["file_path"] in successful_paths:
                images_to_insert.append(image)
                annotation_count += len(image["annotations"])

        # Batch insert to database
        if images_to_insert:
            inserted_count = image_service.bulk_save_images(images_to_insert)
            image_count = inserted_count

        # Log failed uploads
        if upload_result["failed_list"]:
            logger.warning(
                f"\n  ⚠ {len(upload_result['failed_list'])} images failed to upload:"
            )
            for failed in upload_result["failed_list"][:10]:  # Show first 10 failures
                logger.warning(f"    - {failed['object_name']}: {failed['error']}")
            if len(upload_result["failed_list"]) > 10:
                logger.warning(
                    f"    ... and {len(upload_result['failed_list']) - 10} more"
                )

        logger.info(f"\n  Split summary:")
        logger.info(f"    Images processed: {image_count}")
        logger.info(f"    Annotations: {annotation_count}")
        logger.info(f"    Total size: {total_file_size / 1024 / 1024:.2f} MB")

        return image_count, annotation_count, total_file_size


# Global Upload service instance
upload_service = UploadService()
