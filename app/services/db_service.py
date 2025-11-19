"""Database service for MongoDB connection management."""
from typing import Any, Dict, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """Service class for MongoDB connection management (Singleton)."""
    
    _instance: Optional['DatabaseService'] = None
    
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, max_pool_size: int = 50, retry_writes: bool = True):
        """Initialize MongoDB client with connection pooling."""
        # Prevent re-initialization if already initialized
        if hasattr(self, 'client'):
            return

        self.client = MongoClient(
            settings.mongodb_url,
            maxPoolSize=settings.mongodb_max_pool_size,
            retryWrites=retry_writes,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        self.db = self.client[settings.mongo_db_name]
        
        # Collections
        self.datasets = self.db.datasets
        self.images = self.db.images
        self.upload_sessions = self.db.upload_sessions
        self.dataset_statistics = self.db.dataset_statistics
        self.users = self.db.users
        self.annotations = self.db.annotations
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test database connection."""
        try:
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise Exception(f"Failed to connect to MongoDB: {e}")
            
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def convert_objectids_to_str(self, doc: Dict[str, Any]) -> None:
        """
        Recursively convert ObjectId fields to strings in a document.
        
        Args:
            doc: Document dictionary to process (modified in place)
        """
        if not isinstance(doc, dict):
            return
        
        for key, value in list(doc.items()):
            if isinstance(value, ObjectId):
                doc[key] = str(value)
            elif isinstance(value, dict):
                self.convert_objectids_to_str(value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, ObjectId):
                        value[i] = str(item)
                    elif isinstance(item, dict):
                        self.convert_objectids_to_str(item)


# Global Database service instance
db_service = DatabaseService()
