# """
# FastAPI应用主入口

# 启动整个认证和用户管理系统。
# """

# import logging
# import sys
# from contextlib import asynccontextmanager
# from typing import AsyncGenerator

# from fastapi import FastAPI, HTTPException, Request, status
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from fastapi.exceptions import RequestValidationError
# from starlette.exceptions import HTTPException as StarletteHTTPException

# from core.config import settings
# from db.mongodb import init_database, health_check
# from models import *
# from services import *
# from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, UploadFile, File, Form, BackgroundTasks
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from fastapi.responses import StreamingResponse, JSONResponse
# from typing import Dict, Any, List, Optional
# from datetime import datetime, timedelta


# # 配置日志记录器
# logging.basicConfig(
#     level=getattr(logging, settings.log_level.upper()),
#     format=settings.log_format,
#     handlers=[
#         logging.StreamHandler(sys.stdout),
#         logging.FileHandler("app.log", encoding="utf-8")
#     ]
# )

# logger = logging.getLogger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
#     """应用程序生命周期管理
    
#     在应用启动时初始化数据库，在应用关闭时清理资源。
    
#     Args:
#         app: FastAPI应用实例
#     """
#     # 启动时的初始化
#     logger.info(f"启动 {settings.app_name} v{settings.app_version}")
    
#     try:
#         # 初始化数据库
#         await init_database()
#         logger.info("数据库初始化完成")
        
#         # 执行健康检查
#         db_health = await health_check()
#         if db_health["status"] != "healthy":
#             logger.error(f"数据库健康检查失败: {db_health}")
#             raise Exception("数据库连接失败")
        
#         logger.info("应用程序启动完成")
        
#         #yield控制权给应用
#         yield
        
#     except Exception as e:
#         logger.error(f"应用程序启动失败: {e}")
#         raise
#     finally:
#         # 关闭时的清理
#         logger.info("正在关闭应用程序...")
#         from db.mongodb import close_mongo_connection
#         await close_mongo_connection()
#         logger.info("应用程序已关闭")


# # 创建FastAPI应用实例
# app = FastAPI(
#     title=settings.app_name,
#     version=settings.app_version,
#     description="FastAPI认证和用户管理系统",
#     docs_url="/docs",
#     redoc_url="/redoc",
#     openapi_url="/openapi.json",
#     lifespan=lifespan
# )


# # 添加CORS中间件
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 简化：允许所有来源
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # 全局异常处理器
# @app.exception_handler(HTTPException)
# async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
#     """HTTP异常处理器"""
#     logger.error(f"HTTP异常: {exc.status_code} - {exc.detail} - {request.url}")
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "error": "HTTP_ERROR",
#             "message": exc.detail,
#             "status_code": exc.status_code
#         }
#     )


# @app.exception_handler(StarletteHTTPException)
# async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
#     """Starlette HTTP异常处理器"""
#     logger.error(f"Starlette HTTP异常: {exc.status_code} - {exc.detail} - {request.url}")
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "error": "HTTP_ERROR",
#             "message": exc.detail,
#             "status_code": exc.status_code
#         }
#     )


# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
#     """请求验证异常处理器"""
#     logger.error(f"请求验证失败: {exc.errors()} - {request.url}")
#     return JSONResponse(
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#         content={
#             "error": "VALIDATION_ERROR",
#             "message": "请求数据验证失败",
#             "details": exc.errors()
#         }
#     )


# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
#     """全局异常处理器"""
#     logger.error(f"全局异常: {exc} - {request.url}", exc_info=True)
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={
#             "error": "INTERNAL_SERVER_ERROR",
#             "message": "内部服务器错误"
#         }
#     )


# # 安全方案
# security = HTTPBearer()

# # =============================================================================
# # 认证路由
# # =============================================================================

# async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
#     """获取当前用户（依赖函数）- 简化版"""
#     # 在简化的认证系统中，直接返回admin用户
#     return {
#         "id": "admin",
#         "username": "admin",
#         "email": "admin@example.com",
#         "full_name": "Administrator",
#         "is_active": True,
#         "is_verified": True
#     }

# @app.post("/auth/login", summary="管理员登录", description="仅支持admin/admin认证")
# async def login(username: str, password: str) -> Dict[str, Any]:
#     """简单的管理员登录"""
#     auth_service = AuthService()
#     return await auth_service.login(username, password)

# @app.get("/auth/me", summary="获取当前用户信息")
# async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
#     """获取当前用户信息"""
#     logger.info(f"获取当前用户信息: {current_user.get('email')}")
#     return current_user

# @app.get("/auth/health", summary="认证服务健康检查")
# async def auth_health_check() -> dict:
#     """认证服务健康检查"""
#     return {
#         "status": "healthy",
#         "service": "authentication",
#         "mode": "simplified",
#         "timestamp": "2025-11-17T18:27:10Z"
#     }

# # =============================================================================
# # 数据集路由
# # =============================================================================

# @app.post("/datasets/validate", response_model=ValidationResponse)
# async def start_dataset_validation(
#     request: ValidationRequest,
#     background_tasks: BackgroundTasks
# ):
#     """开始数据集验证"""
#     try:
#         dataset_service = DatasetService()
#         job = await dataset_service.create_validation_job(
#             request.upload_session_id,
#             request.dataset_name
#         )
        
#         background_tasks.add_task(
#             dataset_service.start_validation,
#             job["job_id"],
#             None
#         )
        
#         return ValidationResponse(
#             job_id=job["job_id"],
#             status=ValidationStatus(job["status"]),
#             message="验证任务已启动"
#         )
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         logger.error(f"启动验证失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"启动验证失败: {str(e)}")

# @app.get("/datasets/validation/{job_id}", response_model=ValidationResult)
# async def get_validation_result(job_id: str):
#     """获取验证结果"""
#     try:
#         dataset_service = DatasetService()
#         job = await dataset_service.get_validation_job(job_id)
#         if not job:
#             raise HTTPException(status_code=404, detail="验证任务不存在")
        
#         validation_results = job.get("validation_results", {})
        
#         return ValidationResult(
#             job_id=job["job_id"],
#             upload_session_id=job["upload_session_id"],
#             filename=job["filename"],
#             status=ValidationStatus(job["status"]),
#             is_valid=validation_results.get("is_valid", False),
#             progress=job["progress"],
#             validation_results=validation_results,
#             error_details=validation_results.get("errors", []),
#             warnings=validation_results.get("warnings", []),
#             summary=validation_results.get("summary", {}),
#             created_at=job["created_at"],
#             completed_at=job.get("completed_at")
#         )
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"获取验证结果失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"获取验证结果失败: {str(e)}")

# @app.get("/datasets/list", response_model=DatasetListResponse)
# async def list_datasets(
#     limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
#     offset: int = Query(0, ge=0, description="偏移量")
# ):
#     """列出所有数据集"""
#     try:
#         dataset_service = DatasetService()
#         datasets = await dataset_service.list_datasets(limit, offset)
        
#         return DatasetListResponse(
#             datasets=datasets,
#             total=len(datasets),
#             offset=offset,
#             limit=limit
#         )
        
#     except Exception as e:
#         logger.error(f"列出数据集失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"列出数据集失败: {str(e)}")

# # =============================================================================
# # 上传路由
# # =============================================================================

# @app.post("/upload/initiate", response_model=UploadSessionResponse)
# async def initiate_upload(session_data: UploadSessionCreate):
#     """创建上传会话"""
#     try:
#         # 模拟获取集合
#         upload_service = UploadService(None)
#         session = await upload_service.create_session(session_data)
        
#         expires_at = datetime.utcnow() + timedelta(hours=24)
        
#         return UploadSessionResponse(
#             session_id=session.session_id,
#             upload_url=f"/upload/chunk/{session.session_id}",
#             chunk_size=session.chunk_size,
#             total_chunks=session.total_chunks,
#             expires_at=expires_at
#         )
        
#     except Exception as e:
#         logger.error(f"创建上传会话失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"创建上传会话失败: {str(e)}")

# @app.post("/upload/chunk/{session_id}")
# async def upload_chunk(
#     session_id: str,
#     chunk_file: UploadFile = File(...)
# ):
#     """上传分片"""
#     try:
#         chunk_data = await chunk_file.read()
#         chunk_index = int(chunk_file.filename.split('_')[-1])
        
#         upload_service = UploadService(None)
#         success = await upload_service.upload_chunk(session_id, chunk_index, chunk_data)
        
#         return {
#             "success": success,
#             "chunk_index": chunk_index,
#             "message": "分片上传成功" if success else "分片上传失败"
#         }
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         logger.error(f"上传分片失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"上传分片失败: {str(e)}")

# @app.post("/upload/complete/{session_id}")
# async def complete_upload(
#     session_id: str,
#     request: CompleteUploadRequest
# ):
#     """完成上传并合并文件"""
#     try:
#         upload_service = UploadService(None)
#         success = await upload_service.complete_upload(session_id, request.final_checksum)
        
#         return {
#             "success": success,
#             "message": "文件上传完成",
#             "session_id": session_id
#         }
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         logger.error(f"完成上传失败: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"完成上传失败: {str(e)}")

# # =============================================================================
# # 图像路由
# # =============================================================================

# @app.post("/api/v1/images/", response_model=ImageUploadResponse, summary="上传图像")
# async def upload_image(
#     dataset_id: str = Form(..., description="数据集ID"),
#     file: UploadFile = File(..., description="图像文件"),
#     tags: Optional[str] = Form(None, description="标签列表（逗号分隔）"),
#     notes: Optional[str] = Form(None, description="备注"),
#     current_user: Dict = Depends(get_current_user)
# ):
#     """上传图像文件到指定数据集"""
#     try:
#         file_size = len(await file.read())
#         if file_size > settings.max_file_size:
#             raise HTTPException(
#                 status_code=HTTP_STATUS_CODES["FILE_TOO_LARGE"],
#                 detail=f"文件大小超过限制 ({settings.max_file_size / 1024 / 1024:.1f}MB)"
#             )
        
#         await file.seek(0)
#         file_data = await file.read()
        
#         tag_list = []
#         if tags:
#             tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
#         image_create = ImageCreate(
#             dataset_id=dataset_id,
#             original_filename=file.filename,
#             file_data=file_data,
#             content_type=file.content_type,
#             metadata=ImageMetadata(tags=tag_list, notes=notes) if tags or notes else None
#         )
        
#         # 模拟图像服务
#         image_id = str(uuid.uuid4())
#         image_data = Image(
#             image_id=image_id,
#             dataset_id=dataset_id,
#             original_filename=file.filename,
#             stored_filename=f"{image_id}_{file.filename}",
#             file_path=f"/datasets/{dataset_id}/images/{image_id}",
#             thumbnail_path=f"/datasets/{dataset_id}/thumbnails/{image_id}",
#             dimensions=ImageDimensions(width=1920, height=1080, channels=3),
#             file_info=ImageFileInfo(size_bytes=len(file_data), format="JPEG"),
#             uploader_id=current_user["id"],
#             created_at=datetime.utcnow(),
#             updated_at=datetime.utcnow()
#         )
        
#         return ImageUploadResponse(
#             data=image_data,
#             message="图像上传成功"
#         )
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=HTTP_STATUS_CODES["INTERNAL_SERVER_ERROR"],
#             detail=f"上传失败: {str(e)}"
#         )

# @app.get("/api/v1/images/datasets/{dataset_id}/images", response_model=ImageListResponse, summary="获取数据集图像列表")
# async def get_dataset_images(
#     dataset_id: str,
#     page: int = Query(1, ge=1, description="页码"),
#     limit: int = Query(20, ge=1, le=100, description="每页数量"),
#     sort_by: str = Query("created_at", description="排序字段"),
#     sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向")
# ):
#     """获取指定数据集的图像列表"""
#     try:
#         # 模拟返回空列表
#         return ImageListResponse(
#             data=[],
#             pagination={
#                 "page": page,
#                 "limit": limit,
#                 "total": 0,
#                 "pages": 0
#             },
#             message="图像列表获取成功"
#         )
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=HTTP_STATUS_CODES["INTERNAL_SERVER_ERROR"],
#             detail=f"获取数据集图像列表失败: {str(e)}"
#         )

# @app.get("/api/v1/images/images/{image_id}", response_model=ImageDetailResponse, summary="获取图像详情")
# async def get_image(image_id: str):
#     """获取指定图像的详细信息"""
#     try:
#         # 模拟返回图像详情
#         image_data = {
#             "image_id": image_id,
#             "dataset_id": "dataset_001",
#             "original_filename": "sample.jpg",
#             "dimensions": {"width": 1920, "height": 1080, "channels": 3},
#             "file_info": {"size_bytes": 1024000, "format": "JPEG"},
#             "created_at": datetime.utcnow()
#         }
        
#         return ImageDetailResponse(
#             data=image_data,
#             message="图像详情获取成功"
#         )
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=HTTP_STATUS_CODES["INTERNAL_SERVER_ERROR"],
#             detail=f"获取图像详情失败: {str(e)}"
#         )

# @app.get("/api/v1/images/images/{image_id}/thumbnail", summary="获取图像缩略图")
# async def get_thumbnail(image_id: str):
#     """获取指定图像的缩略图"""
#     try:
#         return {
#             "thumbnail_url": f"/datasets/dataset_001/thumbnails/{image_id}_thumb.jpg",
#             "message": "缩略图获取成功"
#         }
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=HTTP_STATUS_CODES["INTERNAL_SERVER_ERROR"],
#             detail=f"获取缩略图失败: {str(e)}"
#         )

# # =============================================================================
# # 标注路由
# # =============================================================================

# @app.post("/api/v1/annotations/images/{image_id}/annotations", response_model=AnnotationResponse, summary="创建标注")
# async def create_annotation(
#     image_id: str,
#     annotation_data: AnnotationCreate,
#     current_user: Dict = Depends(get_current_user)
# ):
#     """为指定图像创建新的标注"""
#     try:
#         # 简化实现，返回模拟数据
#         annotation_id = str(uuid.uuid4())
        
#         annotation = Annotation(
#             annotation_id=annotation_id,
#             image_id=image_id,
#             dataset_id=annotation_data.dataset_id,
#             annotator_id=current_user["id"],
#             yolo_annotation=annotation_data.yolo_annotation,
#             bounding_box=BoundingBox(x=100, y=100, width=200, height=200),
#             labels=AnnotationLabels(class_name=f"class_{annotation_data.yolo_annotation.class_id}"),
#             created_at=datetime.utcnow(),
#             updated_at=datetime.utcnow()
#         )
        
#         return AnnotationResponse(
#             data=annotation,
#             message="标注创建成功"
#         )
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=HTTP_STATUS_CODES["INTERNAL_SERVER_ERROR"],
#             detail=f"创建标注失败: {str(e)}"
#         )

# @app.get("/api/v1/annotations/images/{image_id}/annotations", summary="获取图像标注")
# async def get_image_annotations(
#     image_id: str,
#     format: str = Query("json", regex="^(json|yolo|coco)$", description="标注格式")
# ):
#     """获取指定图像的标注数据"""
#     try:
#         # 模拟返回空标注列表
#         return {
#             "success": True,
#             "data": {
#                 "image_id": image_id,
#                 "annotations": [],
#                 "format": format
#             },
#             "message": "标注数据获取成功"
#         }
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=HTTP_STATUS_CODES["INTERNAL_SERVER_ERROR"],
#             detail=f"获取标注失败: {str(e)}"
#         )


# # 根路径
# @app.get("/", summary="根路径")
# async def root() -> dict:
#     """根路径
    
#     返回应用程序的基本信息。
    
#     Returns:
#         dict: 应用信息
#     """
#     return {
#         "message": f"欢迎使用 {settings.app_name}",
#         "version": settings.app_version,
#         "status": "running",
#         "docs_url": "/docs",
#         "health_check": "/health"
#     }


# # 健康检查端点
# @app.get("/health", summary="健康检查")
# async def health_check_endpoint() -> dict:
#     """应用程序健康检查
    
#     检查应用程序和数据库的运行状态。
    
#     Returns:
#         dict: 健康状态信息
#     """
#     try:
#         # 检查数据库状态
#         db_health = await health_check()
        
#         # 汇总健康状态
#         overall_status = "healthy" if db_health["status"] == "healthy" else "unhealthy"
        
#         return {
#             "status": overall_status,
#             "timestamp": "2025-11-17T18:27:10Z",
#             "application": {
#                 "name": settings.app_name,
#                 "version": settings.app_version,
#                 "debug": settings.debug
#             },
#             "database": db_health
#         }
        
#     except Exception as e:
#         logger.error(f"健康检查失败: {e}")
#         return {
#             "status": "unhealthy",
#             "timestamp": "2025-11-17T18:27:10Z",
#             "error": str(e)
#         }


# # API信息端点
# @app.get("/api/info", summary="API信息")
# async def api_info() -> dict:
#     """API信息
    
#     返回API的详细信息和使用指南。
    
#     Returns:
#         dict: API信息
#     """
#     return {
#         "name": settings.app_name,
#         "version": settings.app_version,
#         "description": "YOLO数据集标注API - 专注YOLO格式数据集处理",
#         "features": [
#             "简单管理员认证 (admin/admin)",
#             "数据集上传和管理",
#             "YOLO格式验证",
#             "图像管理和存储",
#             "标注数据管理",
#             "YOLO格式坐标转换"
#         ],
#         "endpoints": {
#             "认证": {
#                 "登录": "POST /auth/login",
#                 "当前用户": "GET /auth/me"
#             },
#             "数据集": {
#                 "启动验证": "POST /datasets/validate",
#                 "查询验证结果": "GET /datasets/validation/{job_id}",
#                 "列出数据集": "GET /datasets/list"
#             },
#             "图像管理": {
#                 "获取图像列表": "GET /api/v1/images/datasets/{dataset_id}/images",
#                 "获取图像详情": "GET /api/v1/images/images/{image_id}",
#                 "获取缩略图": "GET /api/v1/images/images/{image_id}/thumbnail"
#             },
#             "标注管理": {
#                 "获取图像标注": "GET /api/v1/annotations/images/{image_id}/annotations",
#                 "创建标注": "POST /api/v1/annotations/images/{image_id}/annotations"
#             }
#         },
#         "documentation": {
#             "swagger": "/docs",
#             "redoc": "/redoc",
#             "openapi": "/openapi.json"
#         },
#         "security": {
#             "authentication": "Bearer Token (简化版)"
#         }
#     }


# if __name__ == "__main__":
#     import uvicorn
    
#     logger.info(f"启动开发服务器: http://{settings.host}:{settings.port}")
    
#     uvicorn.run(
#         "main:app",
#         host=settings.host,
#         port=settings.port,
#         reload=settings.debug,
#         log_level=settings.log_level.lower()
#     )


"""Main FastAPI application."""
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import annotations, datasets, upload
from app.auth import authenticate_user
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="YOLO Dataset API",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add global exception handler
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # Include routers
    application.include_router(
        datasets.router,
        prefix="/api/v1",
        tags=["datasets"]
    )
    application.include_router(
        upload.router,
        prefix="/api/v1",
        tags=["upload"]
    )
    application.include_router(
        annotations.router, 
        prefix="/api/v1",
        tags=["annotations"]
    )
    
    logger.info(f"Application '{settings.app_name}' v{settings.app_version} created successfully")
    
    return application


app = create_application()


@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("Root endpoint accessed")
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}