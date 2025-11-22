"""
应用配置文件
包含所有环境相关的配置项
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings configuration."""

    # 应用基础配置
    app_name: str = "YOLO Dataset API"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "yolo-secret-key-simplified"

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017/yolo_datasets?authSource=admin"
    mongo_db_name: str = "yolo_datasets"
    mongodb_max_pool_size: int = 10  # 简化连接池

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "yolo-datasets"
    minio_secure: bool = False

    # 文件上传配置
    allowed_image_formats: list = ["JPEG", "JPG", "PNG", "BMP", "TIFF"]
    max_upload_size: int = 100 * 1024 * 1024 * 1024  # 100GB
    upload_chunk_size: int = 10 * 1024 * 1024  # 10MB
    temp_dir: str = "/tmp/yolo_datasets_upload"

    # 简化JWT配置
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 120  # 2小时
    jwt_refresh_token_expire_days: int = 7

    # 图像处理配置
    thumbnail_sizes: dict = {
        "small": (150, 150),
        "medium": (300, 300)
    }
    default_thumbnail_quality: int = 80

    # YOLO标注配置
    max_annotations_per_image: int = 1000
    annotation_confidence_threshold: float = 0.1
    yolo_validation_timeout: int = 300  # 5 minutes

    # 分页配置
    default_page_size: int = 20
    max_page_size: int = 50  # 限制最大页大小

    model_config = {
        "env_file": ".env.dev",
        "env_file_encoding": "utf-8",
        "extra": "allow"
    }


# 全局配置实例
settings = Settings()

# 支持的图像格式
ALLOWED_IMAGE_FORMATS = set(fmt.lower() for fmt in settings.allowed_image_formats)

# YOLO类别颜色映射（默认）
DEFAULT_CLASS_COLORS = {
    "0": "#FF0000",  # 红色
    "1": "#00FF00",  # 绿色
    "2": "#0000FF",  # 蓝色
    "3": "#FFFF00",  # 黄色
    "4": "#FF00FF",  # 紫色
    "5": "#00FFFF",  # 青色
    "6": "#FFA500",  # 橙色
    "7": "#800080",  # 紫红色
    "8": "#008000",  # 深绿色
    "9": "#000080",  # 海军蓝
}

# 图像质量阈值
IMAGE_QUALITY_THRESHOLDS = {
    "min_sharpness": 30.0,
    "max_blur_score": 20.0,
    "min_brightness": 20.0,
    "max_brightness": 90.0,
    "min_contrast": 30.0,
    "max_noise_level": 40.0
}

# API响应状态码
HTTP_STATUS_CODES = {
    "SUCCESS": 200,
    "CREATED": 201,
    "NO_CONTENT": 204,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "UNSUPPORTED_MEDIA_TYPE": 415,
    "TOO_MANY_REQUESTS": 429,
    "INTERNAL_SERVER_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503
}

# 错误代码
ERROR_CODES = {
    "AUTH_INVALID_CREDENTIALS": "AUTH_INVALID_CREDENTIALS",
    "AUTH_TOKEN_EXPIRED": "AUTH_TOKEN_EXPIRED",
    "AUTH_TOKEN_INVALID": "AUTH_TOKEN_INVALID",
    "AUTH_INSUFFICIENT_PERMISSIONS": "AUTH_INSUFFICIENT_PERMISSIONS",
    "RESOURCE_NOT_FOUND": "RESOURCE_NOT_FOUND",
    "RESOURCE_ALREADY_EXISTS": "RESOURCE_ALREADY_EXISTS",
    "VALIDATION_ERROR": "VALIDATION_ERROR",
    "RATE_LIMIT_EXCEEDED": "RATE_LIMIT_EXCEEDED",
    "FILE_TOO_LARGE": "FILE_TOO_LARGE",
    "UNSUPPORTED_FILE_TYPE": "UNSUPPORTED_FILE_TYPE",
    "STORAGE_QUOTA_EXCEEDED": "STORAGE_QUOTA_EXCEEDED",
    "INTERNAL_SERVER_ERROR": "INTERNAL_SERVER_ERROR",
    "SERVICE_UNAVAILABLE": "SERVICE_UNAVAILABLE"
}
