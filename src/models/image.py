"""
Pydantic models for image metadata and API requests/responses.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class ImageStatus(str, Enum):
    """Image upload status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ImageMetadata(BaseModel):
    """Image metadata stored in DynamoDB"""
    image_id: str = Field(..., description="Unique image identifier (UUID)")
    user_id: str = Field(..., description="User who uploaded the image")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type (e.g., image/jpeg)")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    upload_timestamp: str = Field(..., description="ISO 8601 timestamp")
    tags: Optional[List[str]] = Field(default=None, description="Image tags")
    description: Optional[str] = Field(default=None, description="Image description")
    status: ImageStatus = Field(default=ImageStatus.COMPLETED, description="Upload status")
    s3_key: str = Field(..., description="S3 object key")
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of {allowed_types}')
        return v


class ImageMetadataDB(ImageMetadata):
    """Extended model with DynamoDB specific fields"""
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
