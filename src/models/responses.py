"""
Response models for API endpoints.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from src.models.image import ImageMetadata


class PresignedUrlResponse(BaseModel):
    """Response containing presigned URL for upload"""
    image_id: str = Field(..., description="Unique image identifier")
    presigned_url: str = Field(..., description="Presigned URL for upload")
    fields: Dict[str, str] = Field(..., description="Form fields for POST upload")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    s3_key: str = Field(..., description="S3 object key")


class PresignedDownloadUrlResponse(BaseModel):
    """Response containing presigned URL for download"""
    image_id: str = Field(..., description="Image identifier")
    presigned_url: str = Field(..., description="Presigned URL for download")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")


class CompleteUploadResponse(BaseModel):
    """Response after completing upload"""
    image_id: str = Field(..., description="Image identifier")
    status: str = Field(..., description="Upload status")
    message: str = Field(..., description="Status message")


class ListImagesResponse(BaseModel):
    """Response for listing images"""
    images: List[ImageMetadata] = Field(..., description="List of images")
    count: int = Field(..., description="Number of images in current page")
    next_token: Optional[str] = Field(default=None, description="Token for next page")
    has_more: bool = Field(..., description="Whether more results exist")


class DeleteImageResponse(BaseModel):
    """Response after deleting an image"""
    image_id: str = Field(..., description="Deleted image identifier")
    status: str = Field(..., description="Deletion status")
    message: str = Field(..., description="Status message")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
