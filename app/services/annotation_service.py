"""Annotation service for handling annotation operations."""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
from app.config import settings
from app.models.annotation import Annotation, AnnotationStats, AnnotationFilter, BaseAnnotation
from app.services.mongo_service import mongo_service


class AnnotationService:
    """Service class for annotation operations."""
    
    def __init__(self):
        """Initialize annotation service."""
        self.db = mongo_service.db
        self.annotations = self.db.annotations
        self.annotation_stats = self.db.annotation_stats
    
    def create_annotation(self, annotation_data: dict) -> str:
        """
        Create a new annotation.
        
        Args:
            annotation_data: Annotation data
            
        Returns:
            str: Created annotation ID
        """
        # Validate required fields
        required_fields = ['image_id', 'dataset_id', 'class_id', 'class_name', 'annotation_type']
        for field in required_fields:
            if field not in annotation_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Convert string IDs to ObjectId
        annotation_data['image_id'] = ObjectId(annotation_data['image_id'])
        annotation_data['dataset_id'] = ObjectId(annotation_data['dataset_id'])
        
        # Insert annotation
        result = self.annotations.insert_one(annotation_data)
        annotation_id = str(result.inserted_id)
        
        # Update image annotation count
        self._update_image_annotation_count(annotation_data['image_id'])
        
        # Update dataset statistics
        self._update_dataset_annotation_stats(annotation_data['dataset_id'])
        
        return annotation_id
    
    def get_annotation(self, annotation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get annotation by ID.
        
        Args:
            annotation_id: Annotation ID
            
        Returns:
            Optional[Dict]: Annotation data or None
        """
        annotation = self.annotations.find_one({"_id": ObjectId(annotation_id)})
        if annotation:
            return self._convert_object_ids(annotation)
        return None
    
    def get_annotations_by_image(self, image_id: str) -> List[Dict[str, Any]]:
        """
        Get all annotations for an image.
        
        Args:
            image_id: Image ID
            
        Returns:
            List[Dict]: List of annotations
        """
        cursor = self.annotations.find({"image_id": ObjectId(image_id)})
        annotations = []
        for annotation in cursor:
            annotations.append(self._convert_object_ids(annotation))
        return annotations
    
    def get_annotations_with_filter(self, filter_criteria: Dict[str, Any], 
                                  skip: int = 0, limit: int = 100) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get annotations with filter criteria.
        
        Args:
            filter_criteria: Filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple[List[Dict], int]: (annotations, total_count)
        """
        # Apply filter and get total count
        total = self.annotations.count_documents(filter_criteria)
        
        # Get paginated results
        cursor = self.annotations.find(filter_criteria).skip(skip).limit(limit)
        annotations = []
        for annotation in cursor:
            annotations.append(self._convert_object_ids(annotation))
        
        return annotations, total
    
    def update_annotation(self, annotation_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update annotation.
        
        Args:
            annotation_id: Annotation ID
            update_data: Data to update
            
        Returns:
            bool: True if successful
        """
        # Remove immutable fields
        immutable_fields = ['_id', 'image_id', 'dataset_id', 'annotation_type', 'created_at']
        for field in immutable_fields:
            update_data.pop(field, None)
        
        # Add updated_at timestamp
        update_data['updated_at'] = BaseAnnotation.get_current_time()
        
        result = self.annotations.update_one(
            {"_id": ObjectId(annotation_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    
    def delete_annotation(self, annotation_id: str) -> bool:
        """
        Delete annotation.
        
        Args:
            annotation_id: Annotation ID
            
        Returns:
            bool: True if successful
        """
        # Get annotation before deletion to update counts
        annotation = self.get_annotation(annotation_id)
        if not annotation:
            return False
        
        # Delete annotation
        result = self.annotations.delete_one({"_id": ObjectId(annotation_id)})
        
        if result.deleted_count > 0:
            # Update image annotation count
            self._update_image_annotation_count(ObjectId(annotation['image_id']))
            
            # Update dataset statistics
            self._update_dataset_annotation_stats(ObjectId(annotation['dataset_id']))
            
            return True
        
        return False
    
    def get_dataset_annotation_stats(self, dataset_id: str) -> Dict[str, Any]:
        """
        Get annotation statistics for a dataset.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            Dict: Annotation statistics
        """
        pipeline = [
            {"$match": {"dataset_id": ObjectId(dataset_id)}},
            {"$group": {
                "_id": None,
                "total_annotations": {"$sum": 1},
                "annotations_by_class": {"$push": "$class_name"},
                "annotations_by_type": {"$push": "$annotation_type"},
                "avg_confidence": {"$avg": "$confidence"}
            }}
        ]
        
        result = list(self.annotations.aggregate(pipeline))
        if result:
            stats = result[0]
            
            # Count annotations by class
            class_counts = {}
            for class_name in stats.get('annotations_by_class', []):
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
            
            # Count annotations by type
            type_counts = {}
            for ann_type in stats.get('annotations_by_type', []):
                type_counts[ann_type] = type_counts.get(ann_type, 0) + 1
            
            return {
                "dataset_id": dataset_id,
                "total_annotations": stats.get('total_annotations', 0),
                "annotations_by_class": class_counts,
                "annotations_by_type": type_counts,
                "avg_confidence": stats.get('avg_confidence')
            }
        
        return {
            "dataset_id": dataset_id,
            "total_annotations": 0,
            "annotations_by_class": {},
            "annotations_by_type": {},
            "avg_confidence": None
        }
    
    def get_class_distribution(self, dataset_id: str, split: Optional[str] = None) -> Dict[str, Any]:
        """
        Get class distribution for a dataset.
        
        Args:
            dataset_id: Dataset ID
            split: Optional split filter
            
        Returns:
            Dict: Class distribution
        """
        # Build match stage
        match_stage = {"dataset_id": ObjectId(dataset_id)}
        if split:
            # Need to join with images collection to filter by split
            pipeline = [
                {"$lookup": {
                    "from": "images",
                    "localField": "image_id",
                    "foreignField": "_id",
                    "as": "image"
                }},
                {"$unwind": "$image"},
                {"$match": {
                    "dataset_id": ObjectId(dataset_id),
                    "image.split": split
                }},
                {"$group": {
                    "_id": "$class_name",
                    "count": {"$sum": 1}
                }}
            ]
            
            result = list(self.annotations.aggregate(pipeline))
            class_distribution = {item['_id']: item['count'] for item in result}
            
            # Get total counts
            total_annotations = sum(class_distribution.values())
            total_images = mongo_service.count_images(dataset_id, split)
            
        else:
            # Simple aggregation without split filter
            pipeline = [
                {"$match": {"dataset_id": ObjectId(dataset_id)}},
                {"$group": {
                    "_id": "$class_name",
                    "count": {"$sum": 1}
                }}
            ]
            
            result = list(self.annotations.aggregate(pipeline))
            class_distribution = {item['_id']: item['count'] for item in result}
            
            # Get total counts
            total_annotations = sum(class_distribution.values())
            total_images = mongo_service.count_images(dataset_id)
        
        return {
            "dataset_id": dataset_id,
            "split": split,
            "total_images": total_images,
            "total_annotations": total_annotations,
            "classes": class_distribution
        }
    
    def _update_image_annotation_count(self, image_id: ObjectId) -> None:
        """
        Update annotation count for an image.
        
        Args:
            image_id: Image ID
        """
        count = self.annotations.count_documents({"image_id": image_id})
        mongo_service.db.images.update_one(
            {"_id": image_id},
            {"$set": {
                "annotation_count": count,
                "is_annotated": count > 0,
                "updated_at": datetime.utcnow()
            }}
        )
    
    def _update_dataset_annotation_stats(self, dataset_id: ObjectId) -> None:
        """
        Update annotation statistics for a dataset.
        
        Args:
            dataset_id: Dataset ID
        """
        count = self.annotations.count_documents({"dataset_id": dataset_id})
        mongo_service.db.datasets.update_one(
            {"_id": dataset_id},
            {"$set": {
                "num_annotations": count,
                "updated_at": datetime.utcnow()
            }}
        )
    
    def _convert_object_ids(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert ObjectId fields to strings.
        
        Args:
            document: MongoDB document
            
        Returns:
            Dict: Document with string IDs
        """
        if '_id' in document:
            document['id'] = str(document['_id'])
            del document['_id']
        
        for field in ['image_id', 'dataset_id']:
            if field in document and isinstance(document[field], ObjectId):
                document[field] = str(document[field])
        
        return document


# Global annotation service instance
annotation_service = AnnotationService()