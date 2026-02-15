"""
Configuration management from environment variables.
"""
import os
from typing import Optional


class Config:
    """Application configuration from environment variables."""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID: str = os.getenv('AWS_ACCESS_KEY_ID', 'test')
    AWS_SECRET_ACCESS_KEY: str = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
    
    # LocalStack Configuration (AWS_ENDPOINT_URL is set by LocalStack automatically)
    AWS_ENDPOINT_URL: Optional[str] = os.getenv('AWS_ENDPOINT_URL')
    
    # S3 Configuration
    S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME', 'mont-images')
    S3_PRESIGNED_URL_EXPIRY_UPLOAD: int = int(os.getenv('S3_PRESIGNED_URL_EXPIRY_UPLOAD', '3600'))
    S3_PRESIGNED_URL_EXPIRY_DOWNLOAD: int = int(os.getenv('S3_PRESIGNED_URL_EXPIRY_DOWNLOAD', '900'))
    
    # DynamoDB Configuration
    DYNAMODB_TABLE_NAME: str = os.getenv('DYNAMODB_TABLE_NAME', 'ImageMetadata')
    DYNAMODB_GSI_NAME: str = os.getenv('DYNAMODB_GSI_NAME', 'UserIdTimestampIndex')
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = int(os.getenv('DEFAULT_PAGE_SIZE', '50'))
    MAX_PAGE_SIZE: int = int(os.getenv('MAX_PAGE_SIZE', '100'))
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def get_s3_endpoint(cls) -> Optional[str]:
        """Get S3 endpoint URL for LocalStack."""
        return cls.AWS_ENDPOINT_URL
    
    @classmethod
    def get_dynamodb_endpoint(cls) -> Optional[str]:
        """Get DynamoDB endpoint URL for LocalStack."""
        return cls.AWS_ENDPOINT_URL


# Global config instance
config = Config()
