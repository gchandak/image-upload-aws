"""
Unit tests for DynamoDB service.
"""
import pytest
from datetime import datetime
from moto import mock_dynamodb
from src.services.dynamodb_service import DynamoDBService
from src.models.image import ImageMetadata, ImageStatus


@pytest.mark.unit
class TestDynamoDBService:
    """Test DynamoDB service operations."""
    
    def test_put_item(self, dynamodb_client):
        """Test saving image metadata."""
        service = DynamoDBService()
        
        metadata = ImageMetadata(
            image_id="test-image-123",
            user_id="user-456",
            filename="test.jpg",
            content_type="image/jpeg",
            file_size=1024000,
            upload_timestamp=datetime.utcnow().isoformat(),
            tags=["test"],
            description="Test image",
            status=ImageStatus.COMPLETED,
            s3_key="images/user-456/test-image-123_test.jpg"
        )
        
        result = service.put_item(metadata)
        assert result is True
    
    def test_get_item(self, dynamodb_client):
        """Test retrieving image metadata."""
        service = DynamoDBService()
        
        # Create metadata
        metadata = ImageMetadata(
            image_id="test-image-123",
            user_id="user-456",
            filename="test.jpg",
            content_type="image/jpeg",
            file_size=1024000,
            upload_timestamp=datetime.utcnow().isoformat(),
            tags=["test"],
            description="Test image",
            status=ImageStatus.COMPLETED,
            s3_key="images/user-456/test-image-123_test.jpg"
        )
        
        service.put_item(metadata)
        
        # Retrieve metadata
        retrieved = service.get_item("test-image-123")
        assert retrieved is not None
        assert retrieved.image_id == "test-image-123"
        assert retrieved.user_id == "user-456"
        assert retrieved.filename == "test.jpg"
        
        # Non-existent item
        not_found = service.get_item("nonexistent")
        assert not_found is None
    
    def test_delete_item(self, dynamodb_client):
        """Test deleting image metadata."""
        service = DynamoDBService()
        
        # Create metadata
        metadata = ImageMetadata(
            image_id="test-image-123",
            user_id="user-456",
            filename="test.jpg",
            content_type="image/jpeg",
            file_size=1024000,
            upload_timestamp=datetime.utcnow().isoformat(),
            status=ImageStatus.COMPLETED,
            s3_key="images/user-456/test-image-123_test.jpg"
        )
        
        service.put_item(metadata)
        assert service.get_item("test-image-123") is not None
        
        # Delete
        result = service.delete_item("test-image-123")
        assert result is True
        assert service.get_item("test-image-123") is None
    
    def test_query_by_user(self, dynamodb_client):
        """Test querying images by user_id."""
        service = DynamoDBService()
        
        # Create multiple images for different users
        for i in range(5):
            metadata = ImageMetadata(
                image_id=f"image-{i}",
                user_id="user-123",
                filename=f"test-{i}.jpg",
                content_type="image/jpeg",
                file_size=1024000,
                upload_timestamp=f"2026-02-{10+i:02d}T10:00:00",
                status=ImageStatus.COMPLETED,
                s3_key=f"images/user-123/image-{i}.jpg"
            )
            service.put_item(metadata)
        
        # Create images for another user
        for i in range(3):
            metadata = ImageMetadata(
                image_id=f"other-image-{i}",
                user_id="user-456",
                filename=f"test-{i}.jpg",
                content_type="image/jpeg",
                file_size=1024000,
                upload_timestamp=f"2026-02-{10+i:02d}T10:00:00",
                status=ImageStatus.COMPLETED,
                s3_key=f"images/user-456/other-image-{i}.jpg"
            )
            service.put_item(metadata)
        
        # Query by user_id
        images, next_key = service.query_by_user("user-123")
        assert len(images) == 5
        assert all(img.user_id == "user-123" for img in images)
        
        # Query with date range
        images, next_key = service.query_by_user(
            "user-123",
            start_date="2026-02-11T00:00:00",
            end_date="2026-02-13T23:59:59"
        )
        assert len(images) == 3  # Images from 11th, 12th, 13th
    
    def test_scan_all(self, dynamodb_client):
        """Test scanning all images."""
        service = DynamoDBService()
        
        # Create images
        for i in range(10):
            metadata = ImageMetadata(
                image_id=f"image-{i}",
                user_id=f"user-{i % 3}",
                filename=f"test-{i}.jpg",
                content_type="image/jpeg",
                file_size=1024000,
                upload_timestamp=datetime.utcnow().isoformat(),
                status=ImageStatus.COMPLETED,
                s3_key=f"images/user-{i % 3}/image-{i}.jpg"
            )
            service.put_item(metadata)
        
        # Scan all
        images, next_key = service.scan_all(limit=50)
        assert len(images) == 10
    
    def test_update_status(self, dynamodb_client):
        """Test updating image status."""
        service = DynamoDBService()
        
        # Create metadata
        metadata = ImageMetadata(
            image_id="test-image-123",
            user_id="user-456",
            filename="test.jpg",
            content_type="image/jpeg",
            file_size=1024000,
            upload_timestamp=datetime.utcnow().isoformat(),
            status=ImageStatus.PENDING,
            s3_key="images/user-456/test-image-123_test.jpg"
        )
        
        service.put_item(metadata)
        
        # Update status
        result = service.update_status("test-image-123", ImageStatus.COMPLETED.value)
        assert result is True
        
        # Verify update
        retrieved = service.get_item("test-image-123")
        assert retrieved.status == ImageStatus.COMPLETED
