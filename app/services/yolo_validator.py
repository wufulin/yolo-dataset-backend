"""YOLO format validation and parsing service."""
import os
import tempfile
import zipfile
import yaml
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import subprocess
import sys
from app.config import settings


class YOLOValidator:
    """YOLO format validation and parsing class."""
    
    def __init__(self):
        """Initialize validator."""
        self.supported_types = ['detect', 'obb', 'segment', 'pose', 'classify']
    
    def validate_dataset(self, dataset_path: str) -> Tuple[bool, str]:
        """
        Validate YOLO dataset using Ultralytics check_dataset.
        
        Args:
            dataset_path: Path to dataset directory
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # Import ultralytics and check dataset
            from ultralytics.hub import check_dataset
            
            result = check_dataset(dataset_path)
            if isinstance(result, str) and "error" in result.lower():
                return False, result
            return True, "Dataset validation successful"
            
        except ImportError:
            return False, "Ultralytics package not available"
        except Exception as e:
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
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Look for dataset.yaml or data.yaml
        dataset_yaml = self._find_dataset_yaml(extract_dir)
        if dataset_yaml:
            return os.path.dirname(dataset_yaml)
        
        # If no YAML found, return the extract directory
        return extract_dir
    
    def _find_dataset_yaml(self, directory: str) -> Optional[str]:
        """
        Find dataset YAML file in directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            Optional[str]: Path to YAML file or None
        """
        for root, _, files in os.walk(directory):
            for file in files:
                if file in ['dataset.yaml', 'data.yaml']:
                    return os.path.join(root, file)
        return None
    
    def parse_dataset_yaml(self, yaml_path: str) -> Dict[str, Any]:
        """
        Parse dataset YAML file.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            Dict: Parsed YAML content
        """
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
            return data or {}
        except Exception as e:
            raise Exception(f"Failed to parse YAML: {str(e)}")
    
    def get_dataset_type(self, dataset_path: str) -> str:
        """
        Detect dataset type from directory structure and content.
        
        Args:
            dataset_path: Path to dataset directory
            
        Returns:
            str: Dataset type
        """
        # Check for OBB specific files
        if self._has_obb_annotations(dataset_path):
            return 'obb'
        
        # Check for segmentation files
        if self._has_segmentation_annotations(dataset_path):
            return 'segment'
        
        # Check for pose files
        if self._has_pose_annotations(dataset_path):
            return 'pose'
        
        # Default to detection
        return 'detect'
    
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
            print(f"Error parsing annotations {annotation_path}: {str(e)}")
        
        return annotations


# Global YOLO validator instance
yolo_validator = YOLOValidator()