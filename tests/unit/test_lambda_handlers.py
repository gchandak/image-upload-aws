"""
Unit tests for Lambda handlers.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.lambda_handlers import upload_presigned_url, list_images, delete_image
from src.models.image import ImageMetadata, ImageStatus


@pytest.mark.unit
class TestUploadPresignedUrlHandler:
    """Test upload presigned URL handler."""
    
    @patch('src.lambda_handlers.upload_presigned_url.s3_service')
    def test_successful_presigned_url_generation(self, mock_s3_service, sample_lambda_event, lambda_context):
        """Test successful presigned URL generation."""
        # Mock S3 service response
        mock_s3_service.generate_presigned_post.return_value = {
            "url": "https://s3.amazonaws.com/test-bucket",
            "fields": {
                "key": "images/test-user/test-image.jpg",
                "Content-Type": "image/jpeg"
            }
        }
        
        # Create request
        body = {
            "user_id": "test-user",
            "filename": "test-image.jpg",
            "content_type": "image/jpeg",
            "file_size": 1024000
        }
        
        event = sample_lambda_event(
            method="POST",
            path="/images/upload-url",
            body=json.dumps(body)
        )
        
        # Call handler
        response = upload_presigned_url.handler(event, lambda_context)
        
        # Verify response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "image_id" in body
        assert "presigned_url" in body
        assert "fields" in body
        assert body["expires_in"] == 3600
    
    def test_validation_error(self, sample_lambda_event, lambda_context):
        """Test validation error for invalid request."""
        # Invalid request (missing required fields)
        body = {
            "user_id": "test-user"
            # Missing filename, content_type, file_size
        }
        
        event = sample_lambda_event(
            method="POST",
            path="/images/upload-url",
            body=json.dumps(body)
        )
        
        # Call handler
        response = upload_presigned_url.handler(event, lambda_context)
        
        # Verify error response
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "ValidationError"


@pytest.mark.unit
class TestListImagesHandler:
    """Test list images handler."""
    
    @patch('src.lambda_handlers.list_images.dynamodb_service')
    def test_list_images_with_user_filter(self, mock_dynamodb_service, sample_lambda_event, lambda_context):
        """Test listing images filtered by user_id."""
        # Mock DynamoDB service response
        mock_images = [
            ImageMetadata(
                image_id=f"image-{i}",
                user_id="test-user",
                filename=f"test-{i}.jpg",
                content_type="image/jpeg",
                file_size=1024000,
                upload_timestamp=datetime.utcnow().isoformat(),
                status=ImageStatus.COMPLETED,
                s3_key=f"images/test-user/image-{i}.jpg"
            )
            for i in range(5)
        ]
        
        mock_dynamodb_service.query_by_user.return_value = (mock_images, None)
        
        # Create request
        event = sample_lambda_event(
            method="GET",
            path="/images",
            query_params={"user_id": "test-user", "limit": "50"}
        )
        
        # Call handler
        response = list_images.handler(event, lambda_context)
        
        # Verify response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 5
        assert body["has_more"] is False
        assert len(body["images"]) == 5
    
    @patch('src.lambda_handlers.list_images.dynamodb_service')
    def test_list_images_without_filter(self, mock_dynamodb_service, sample_lambda_event, lambda_context):
        """Test listing all images without filter."""
        mock_images = [
            ImageMetadata(
                image_id=f"image-{i}",
                user_id=f"user-{i}",
                filename=f"test-{i}.jpg",
                content_type="image/jpeg",
                file_size=1024000,
                upload_timestamp=datetime.utcnow().isoformat(),
                status=ImageStatus.COMPLETED,
                s3_key=f"images/user-{i}/image-{i}.jpg"
            )
            for i in range(10)
        ]
        
        mock_dynamodb_service.scan_all.return_value = (mock_images, None)
        
        # Create request
        event = sample_lambda_event(
            method="GET",
            path="/images",
            query_params={}
        )
        
        # Call handler
        response = list_images.handler(event, lambda_context)
        
        # Verify response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["count"] == 10


@pytest.mark.unit
class TestDeleteImageHandler:
    """Test delete image handler."""
    
    @patch('src.lambda_handlers.delete_image.s3_service')
    @patch('src.lambda_handlers.delete_image.dynamodb_service')
    def test_successful_deletion(self, mock_dynamodb_service, mock_s3_service, sample_lambda_event, lambda_context):
        """Test successful image deletion."""
        # Mock DynamoDB service response
        mock_metadata = ImageMetadata(
            image_id="test-image-123",
            user_id="test-user",
            filename="test.jpg",
            content_type="image/jpeg",
            file_size=1024000,
            upload_timestamp=datetime.utcnow().isoformat(),
            status=ImageStatus.COMPLETED,
            s3_key="images/test-user/test-image-123.jpg"
        )
        
        mock_dynamodb_service.get_item.return_value = mock_metadata
        mock_dynamodb_service.delete_item.return_value = True
        mock_s3_service.delete_object.return_value = True
        
        # Create request
        body = {"user_id": "test-user"}
        
        event = sample_lambda_event(
            method="DELETE",
            path="/images/test-image-123",
            body=json.dumps(body),
            path_params={"image_id": "test-image-123"}
        )
        
        # Call handler
        response = delete_image.handler(event, lambda_context)
        
        # Verify response
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "deleted"
        assert body["image_id"] == "test-image-123"
    
    @patch('src.lambda_handlers.delete_image.dynamodb_service')
    def test_unauthorized_deletion(self, mock_dynamodb_service, sample_lambda_event, lambda_context):
        """Test unauthorized deletion attempt."""
        # Mock DynamoDB service response
        mock_metadata = ImageMetadata(
            image_id="test-image-123",
            user_id="owner-user",
            filename="test.jpg",
            content_type="image/jpeg",
            file_size=1024000,
            upload_timestamp=datetime.utcnow().isoformat(),
            status=ImageStatus.COMPLETED,
            s3_key="images/owner-user/test-image-123.jpg"
        )
        
        mock_dynamodb_service.get_item.return_value = mock_metadata
        
        # Create request (different user trying to delete)
        body = {"user_id": "malicious-user"}
        
        event = sample_lambda_event(
            method="DELETE",
            path="/images/test-image-123",
            body=json.dumps(body),
            path_params={"image_id": "test-image-123"}
        )
        
        # Call handler
        response = delete_image.handler(event, lambda_context)
        
        # Verify unauthorized response
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"] == "Unauthorized"
