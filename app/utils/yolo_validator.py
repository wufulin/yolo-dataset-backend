"""YOLO format validation and parsing service."""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from app.utils.logger import get_logger

logger = get_logger(__name__)


class YOLOValidator:
    """YOLO format validation and parsing class."""

    def __init__(self):
        """Initialize validator."""
        self.supported_types = ['detect', 'obb', 'segment', 'pose', 'classify']

    def validate_dataset(self, dataset_path: str, dataset_type: str) -> Tuple[bool, str]:
        """
        Validate YOLO dataset using Ultralytics check_dataset.

        Args:
            dataset_path: Path to dataset directory
            dataset_type: Type of dataset

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        logger.info(f"Validating YOLO dataset at: {dataset_path}")
        try:
            # Import ultralytics and check dataset
            from ultralytics.hub import check_dataset

            result = check_dataset(dataset_path, dataset_type)
            if isinstance(result, str) and "error" in result.lower():
                logger.error(f"Dataset validation failed: {result}")
                return False, result
            logger.info(f"Dataset validation successful for: {dataset_path}")
            return True, "Dataset validation successful"

        except ImportError:
            logger.error("Ultralytics package not available")
            return False, "Ultralytics package not available"
        except Exception as e:
            logger.error(f"Dataset validation error: {e}", exc_info=True)
            return False, f"Validation error: {str(e)}"

    def find_dataset_yaml(self, directory: str) -> Path:
        """Find dataset YAML file in directory."""
        directory = Path(directory)
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return None
        yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))
        if yaml_files:
            return yaml_files[0]
        logger.error(f"No dataset YAML found in: {directory}")
        raise Exception(f"No dataset YAML found in: {directory}")

    def parse_dataset_yaml(self, yaml_path: str) -> Dict[str, Any]:
        """
        Parse dataset YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Dict: Parsed YAML content
        """
        logger.info(f"Parsing dataset YAML: {yaml_path}")
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            logger.info(f"Successfully parsed YAML file: {yaml_path}")
            return data or {}
        except Exception as e:
            logger.error(f"Failed to parse YAML {yaml_path}: {e}", exc_info=True)
            raise Exception(f"Failed to parse YAML: {str(e)}")

    def get_dataset_type(self, dataset_path: str) -> str:
        """
        Detect dataset type from directory structure and content.

        Args:
            dataset_path: Path to dataset directory

        Returns:
            str: Dataset type
        """
        logger.info(f"Detecting dataset type for: {dataset_path}")

        # Check for OBB specific files
        if self._has_obb_annotations(dataset_path):
            logger.info(f"Detected OBB dataset type for: {dataset_path}")
            return 'obb'

        # Check for classify specific files
        if self._has_classify_annotations(dataset_path):
            logger.info(f"Detected classify dataset type for: {dataset_path}")
            return 'classify'

        # Check for segmentation files
        if self._has_segmentation_annotations(dataset_path):
            logger.info(f"Detected segmentation dataset type for: {dataset_path}")
            return 'segment'

        # Check for pose files
        if self._has_pose_annotations(dataset_path):
            logger.info(f"Detected pose dataset type for: {dataset_path}")
            return 'pose'

        # Default to detection
        logger.info(f"Detected detection dataset type for: {dataset_path}")
        return 'detect'

    def _has_classify_annotations(self, dataset_path: str) -> bool:
        """Check if dataset has classify annotations."""
        # Look for classify specific files
        classify_patterns = ['classify', 'classification']
        for pattern in classify_patterns:
            if any(pattern in f.lower() for f in os.listdir(dataset_path)):
                return True
        return False

    def _has_obb_annotations(self, dataset_path: str) -> bool:
        """Check if dataset has OBB annotations."""
        # Look for OBB specific file patterns
        obb_patterns = ['obb', 'rotated', 'rbox']
        for pattern in obb_patterns:
            if any(pattern in f.lower() for f in os.listdir(dataset_path)):
                return True
        return False

    def _has_segmentation_annotations(self, dataset_path: str) -> bool:
        """Check if dataset has segmentation annotations."""
        # Look for segmentation files
        seg_dirs = ['segments', 'masks', 'polygons']
        for seg_dir in seg_dirs:
            seg_path = os.path.join(dataset_path, seg_dir)
            if os.path.exists(seg_path):
                return True
        return False

    def _has_pose_annotations(self, dataset_path: str) -> bool:
        """Check if dataset has pose annotations."""
        # Look for pose specific files
        pose_patterns = ['keypoints', 'pose', 'skeleton']
        for pattern in pose_patterns:
            if any(pattern in f.lower() for f in os.listdir(dataset_path)):
                return True
        return False

    def parse_annotations(self, annotation_path: str, dataset_type: str,
                          class_names: List[str]) -> List[Dict[str, Any]]:
        """
        Parse annotation file based on dataset type.

        Args:
            annotation_path: Path to annotation file
            dataset_type: Type of dataset
            class_names: List of class names

        Returns:
            List[Dict]: List of annotations
        """

        annotations = []

        try:
            with open(annotation_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if not parts:
                    continue

                class_id = int(parts[0])
                class_name = class_names[class_id] if class_id < len(class_names) else f"class_{class_id}"

                if dataset_type == 'detect':
                    if len(parts) >= 5:
                        annotation = {
                            "annotation_type": "detect",
                            "class_id": class_id,
                            "class_name": class_name,
                            "bbox": {
                                "x_center": float(parts[1]),
                                "y_center": float(parts[2]),
                                "width": float(parts[3]),
                                "height": float(parts[4])
                            },
                            "confidence": None,
                            "is_crowd": False,
                            "area": float(parts[3]) * float(parts[4]),
                            "metadata": {},
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }
                        annotations.append(annotation)

                elif dataset_type == 'obb':
                    if len(parts) >= 9:
                        annotation = {
                            "annotation_type": "obb",
                            "class_id": class_id,
                            "class_name": class_name,
                            "points": [float(x) for x in parts[1:9]],
                            "confidence": None,
                            "is_crowd": False,
                            "area": None,
                            "metadata": {},
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }
                        annotations.append(annotation)

                elif dataset_type == 'segment':
                    if len(parts) > 1:
                        annotation = {
                            "annotation_type": "segment",
                            "class_id": class_id,
                            "class_name": class_name,
                            "points": [float(x) for x in parts[1:]],
                            "confidence": None,
                            "is_crowd": False,
                            "area": None,
                            "metadata": {},
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }
                        annotations.append(annotation)

                elif dataset_type == 'pose':
                    if len(parts) > 1:
                        annotation = {
                            "annotation_type": "pose",
                            "class_id": class_id,
                            "class_name": class_name,
                            "keypoints": [float(x) for x in parts[1:]],
                            "skeleton": None,
                            "confidence": None,
                            "is_crowd": False,
                            "area": None,
                            "metadata": {},
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc)
                        }
                        annotations.append(annotation)

                elif dataset_type == 'classify':
                    annotation = {
                        "annotation_type": "classify",
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": None,
                        "is_crowd": False,
                        "area": None,
                        "metadata": {},
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc)
                    }
                    annotations.append(annotation)

        except Exception as e:
            logger.error(f"Error parsing annotations {annotation_path}: {str(e)}", exc_info=True)

        logger.info(f"Parsed {len(annotations)} annotations from {annotation_path}")
        return annotations


# Global YOLO validator instance
yolo_validator = YOLOValidator()
