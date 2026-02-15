"""
Unit tests for S3 service.
"""
import pytest
from moto import mock_s3
from botocore.exceptions import ClientError
from src.services.s3_service import S3Service
from src.utils.config import config


@pytest.mark.unit
class TestS3Service:
    """Test S3 service operations."""
    
    def test_generate_presigned_post(self, s3_client):
        """Test generating presigned POST URL."""
        service = S3Service()
        
        result = service.generate_presigned_post(
            s3_key="test/image.jpg",
            content_type="image/jpeg",
            file_size=1024000
        )
        
        assert "url" in result
        assert "fields" in result
        assert result["fields"]["Content-Type"] == "image/jpeg"
    
    def test_generate_presigned_get(self, s3_client):
        """Test generating presigned GET URL."""
        service = S3Service()
        
        # Create a test object
        s3_client.put_object(
            Bucket=config.S3_BUCKET_NAME,
            Key="test/image.jpg",
            Body=b"test data"
        )
        
        url = service.generate_presigned_get(
            s3_key="test/image.jpg",
            filename="downloaded-image.jpg"
        )
        
        assert isinstance(url, str)
        assert "test/image.jpg" in url
    
    def test_check_object_exists(self, s3_client):
        """Test checking if object exists."""
        service = S3Service()
        
        # Object doesn't exist
        assert not service.check_object_exists("nonexistent.jpg")
        
        # Create object
        s3_client.put_object(
            Bucket=config.S3_BUCKET_NAME,
            Key="exists.jpg",
            Body=b"test data"
        )
        
        # Object exists
        assert service.check_object_exists("exists.jpg")
    
    def test_delete_object(self, s3_client):
        """Test deleting object from S3."""
        service = S3Service()
        
        # Create object
        s3_client.put_object(
            Bucket=config.S3_BUCKET_NAME,
            Key="to-delete.jpg",
            Body=b"test data"
        )
        
        assert service.check_object_exists("to-delete.jpg")
        
        # Delete object
        result = service.delete_object("to-delete.jpg")
        assert result is True
        assert not service.check_object_exists("to-delete.jpg")
    
    def test_get_object_metadata(self, s3_client):
        """Test getting object metadata."""
        service = S3Service()
        
        # Create object
        s3_client.put_object(
            Bucket=config.S3_BUCKET_NAME,
            Key="metadata-test.jpg",
            Body=b"test data",
            ContentType="image/jpeg"
        )
        
        metadata = service.get_object_metadata("metadata-test.jpg")
        
        assert metadata is not None
        assert metadata["content_type"] == "image/jpeg"
        assert metadata["content_length"] == 9  # len("test data")
        
        # Non-existent object
        metadata = service.get_object_metadata("nonexistent.jpg")
        assert metadata is None
