"""Main FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import datasets, upload
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
