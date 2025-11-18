"""YOLO format validation and parsing service."""
import os
import zipfile
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.utils.logger import get_logger

logger = get_logger(__name__)


class YOLOValidator:
    """YOLO format validation and parsing class."""
    
    def __init__(self):
        """Initialize validator."""
        logger.info("Initializing YOLO validator")
        self.supported_types = ['detect', 'obb', 'segment', 'pose', 'classify']
        logger.info(f"YOLO validator initialized with supported types: {self.supported_types}")
    
    def validate_dataset(self, dataset_path: str) -> Tuple[bool, str]:
        """
        Validate YOLO dataset using Ultralytics check_dataset.
        
        Args:
            dataset_path: Path to dataset directory
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        logger.info(f"Validating YOLO dataset at: {dataset_path}")
        try:
            # Import ultralytics and check dataset
            from ultralytics.hub import check_dataset
            
            result = check_dataset(dataset_path)
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
    
    def extract_zip(self, zip_path: str, extract_dir: str) -> str:
        """
        Extract ZIP file and find dataset root.
        
        Args:
            zip_path: Path to ZIP file
            extract_dir: Directory to extract to
            
        Returns:
            str: Path to dataset root directory
        """
        logger.info(f"Extracting ZIP file: {zip_path} to {extract_dir}")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            logger.info(f"ZIP extraction completed: {zip_path}")
            
            # Look for dataset.yaml or data.yaml
            dataset_yaml = self._find_dataset_yaml(extract_dir)
            if dataset_yaml:
                dataset_root = os.path.dirname(dataset_yaml)
                logger.info(f"Found dataset YAML at: {dataset_yaml}, root: {dataset_root}")
                return dataset_root
            
            # If no YAML found, return the extract directory
            logger.info(f"No dataset YAML found in {extract_dir}, using extract directory as root")
            return extract_dir
        except Exception as e:
            logger.error(f"Failed to extract ZIP file {zip_path}: {e}", exc_info=True)
            raise Exception(f"Failed to extract ZIP file {zip_path}: {str(e)}")
    
    def _find_dataset_yaml(self, directory: str) -> Optional[str]:
        """
        Find dataset YAML file in directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            Optional[str]: Path to YAML file or None
        """
        logger.info(f"Searching for dataset YAML in: {directory}")
        for root, _, files in os.walk(directory):
            for file in files:
                if file in ['dataset.yaml', 'data.yaml']:
                    yaml_path = os.path.join(root, file)
                    logger.info(f"Found dataset YAML: {yaml_path}")
                    return yaml_path
        logger.info(f"No dataset YAML found in: {directory}")
        return None
    
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
            with open(yaml_path, 'r') as f:
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
        logger.info(f"Parsing annotations: {annotation_path}, type: {dataset_type}")
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
                            "class_id": class_id,
                            "class_name": class_name,
                            "x_center": float(parts[1]),
                            "y_center": float(parts[2]),
                            "width": float(parts[3]),
                            "height": float(parts[4])
                        }
                        annotations.append(annotation)
                
                elif dataset_type == 'obb':
                    if len(parts) >= 9:
                        annotation = {
                            "class_id": class_id,
                            "class_name": class_name,
                            "points": [float(x) for x in parts[1:9]]
                        }
                        annotations.append(annotation)
                
                elif dataset_type == 'segment':
                    if len(parts) > 1:
                        annotation = {
                            "class_id": class_id,
                            "class_name": class_name,
                            "points": [float(x) for x in parts[1:]]
                        }
                        annotations.append(annotation)
                
                elif dataset_type == 'pose':
                    if len(parts) > 1:
                        annotation = {
                            "class_id": class_id,
                            "class_name": class_name,
                            "keypoints": [float(x) for x in parts[1:]]
                        }
                        annotations.append(annotation)
                
                elif dataset_type == 'classify':
                    annotation = {
                        "class_id": class_id,
                        "class_name": class_name
                    }
                    annotations.append(annotation)
                    
        except Exception as e:
            logger.error(f"Error parsing annotations {annotation_path}: {str(e)}", exc_info=True)
        
        logger.info(f"Parsed {len(annotations)} annotations from {annotation_path}")
        return annotations


# Global YOLO validator instance
yolo_validator = YOLOValidator()