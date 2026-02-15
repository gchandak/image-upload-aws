"""
Request models for API endpoints.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime


class UploadPresignedUrlRequest(BaseModel):
    """Request to generate presigned URL for upload"""
    user_id: str = Field(..., description="User ID uploading the image", min_length=1)
    filename: str = Field(..., description="Original filename", min_length=1)
    content_type: str = Field(..., description="MIME type", min_length=1)
    file_size: int = Field(..., description="File size in bytes", gt=0, le=10_485_760)  # Max 10MB
    tags: Optional[List[str]] = Field(default=None, description="Image tags")
    description: Optional[str] = Field(default=None, description="Image description", max_length=500)
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of {allowed_types}')
        return v


class CompleteUploadRequest(BaseModel):
    """Request to mark upload as complete and save metadata"""
    image_id: str = Field(..., description="Image UUID", min_length=1)
    user_id: str = Field(..., description="User ID", min_length=1)
    filename: str = Field(..., description="Original filename", min_length=1)
    content_type: str = Field(..., description="MIME type", min_length=1)
    file_size: int = Field(..., description="File size in bytes", gt=0)
    tags: Optional[List[str]] = Field(default=None, description="Image tags")
    description: Optional[str] = Field(default=None, description="Image description", max_length=500)
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
        if v not in allowed_types:
            raise ValueError(f'Content type must be one of {allowed_types}')
        return v


class ListImagesRequest(BaseModel):
    """Request to list images with filters"""
    user_id: Optional[str] = Field(default=None, description="Filter by user ID")
    start_date: Optional[str] = Field(default=None, description="Start date filter (ISO 8601)")
    end_date: Optional[str] = Field(default=None, description="End date filter (ISO 8601)")
    limit: Optional[int] = Field(default=50, description="Page size", ge=1, le=100)
    next_token: Optional[str] = Field(default=None, description="Pagination token")
    
    @validator('start_date', 'end_date')
    def validate_date(cls, v):
        if v:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Date must be in ISO 8601 format')
        return v


class DeleteImageRequest(BaseModel):
    """Request to delete an image"""
    image_id: str = Field(..., description="Image UUID to delete", min_length=1)
    user_id: str = Field(..., description="User ID (for authorization)", min_length=1)
