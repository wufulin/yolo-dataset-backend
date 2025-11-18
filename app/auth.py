"""Authentication module for the YOLO dataset manager."""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from app.config import settings


security = HTTPBasic()


def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Authenticate user using HTTP Basic auth."""
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "admin")
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username