"""
S3 service for image storage with presigned URL support.
"""
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional
from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class S3Service:
    """Service for S3 operations."""
    
    def __init__(self):
        """Initialize S3 client."""
        self.bucket_name = config.S3_BUCKET_NAME
        
        # Use LocalStack endpoint if configured
        endpoint_url = config.get_s3_endpoint()
        
        self.s3_client = boto3.client(
            's3',
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            endpoint_url=endpoint_url
        )
        
        logger.info(f"S3 service initialized with bucket: {self.bucket_name}")
    
    def generate_presigned_post(
        self,
        s3_key: str,
        content_type: str,
        file_size: int,
        expires_in: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Generate presigned POST URL for direct S3 upload.
        
        Args:
            s3_key: S3 object key
            content_type: MIME type
            file_size: File size in bytes
            expires_in: URL expiration in seconds
        
        Returns:
            Dictionary with presigned URL and form fields
        
        Raises:
            ClientError: If presigned URL generation fails
        """
        if expires_in is None:
            expires_in = config.S3_PRESIGNED_URL_EXPIRY_UPLOAD
        
        try:
            conditions = [
                {"bucket": self.bucket_name},
                {"key": s3_key},
                {"Content-Type": content_type},
                ["content-length-range", file_size, file_size]
            ]
            
            fields = {
                "Content-Type": content_type
            }
            
            presigned_post = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=s3_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned POST URL for key: {s3_key}")
            return presigned_post
        
        except ClientError as e:
            logger.error(f"Failed to generate presigned POST URL: {str(e)}")
            raise
    
    def generate_presigned_get(
        self,
        s3_key: str,
        expires_in: Optional[int] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Generate presigned GET URL for direct S3 download.
        
        Args:
            s3_key: S3 object key
            expires_in: URL expiration in seconds
            filename: Optional filename for Content-Disposition header
        
        Returns:
            Presigned URL string
        
        Raises:
            ClientError: If presigned URL generation fails
        """
        if expires_in is None:
            expires_in = config.S3_PRESIGNED_URL_EXPIRY_DOWNLOAD
        
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': s3_key
            }
            
            if filename:
                params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
            
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned GET URL for key: {s3_key}")
            return presigned_url
        
        except ClientError as e:
            logger.error(f"Failed to generate presigned GET URL: {str(e)}")
            raise
    
    def check_object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def delete_object(self, s3_key: str) -> bool:
        """
        Delete object from S3.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            True if deletion successful
        
        Raises:
            ClientError: If deletion fails
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted object: {s3_key}")
            return True
        
        except ClientError as e:
            logger.error(f"Failed to delete object {s3_key}: {str(e)}")
            raise
    
    def get_object_metadata(self, s3_key: str) -> Optional[Dict[str, any]]:
        """
        Get object metadata from S3.
        
        Args:
            s3_key: S3 object key
        
        Returns:
            Object metadata dictionary or None if not found
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag')
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise


# Global service instance (reused across Lambda invocations)
s3_service = S3Service()
