"""
Integration test for presigned URL workflow.
"""
import pytest
import json
import time
from unittest.mock import patch
from datetime import datetime
from src.lambda_handlers import upload_presigned_url, complete_upload, get_image_presigned_url
from src.models.image import ImageStatus


@pytest.mark.integration
class TestPresignedWorkflow:
    """Test complete presigned URL workflow."""
    
    @patch('src.services.s3_service.s3_service.s3_client')
    @patch('src.services.dynamodb_service.dynamodb_service.table')
    def test_complete_upload_workflow(self, mock_table, mock_s3, sample_lambda_event, lambda_context):
        """Test complete upload workflow: generate URL -> upload -> complete -> download."""
        
        # Step 1: Generate presigned URL for upload
        print("\n--- Step 1: Generate Presigned URL ---")
        
        mock_s3.generate_presigned_post.return_value = {
            "url": "https://s3.amazonaws.com/test-bucket",
            "fields": {
                "key": "images/test-user/test-image.jpg",
                "Content-Type": "image/jpeg"
            }
        }
        
        upload_request = {
            "user_id": "test-user-123",
            "filename": "vacation-photo.jpg",
            "content_type": "image/jpeg",
            "file_size": 2048000,
            "tags": ["vacation", "beach"],
            "description": "Beach vacation photo"
        }
        
        event = sample_lambda_event(
            method="POST",
            path="/images/upload-url",
            body=json.dumps(upload_request)
        )
        
        response = upload_presigned_url.handler(event, lambda_context)
        assert response["statusCode"] == 200
        
        upload_response = json.loads(response["body"])
        image_id = upload_response["image_id"]
        s3_key = upload_response["s3_key"]
        
        print(f"Generated image_id: {image_id}")
        print(f"S3 key: {s3_key}")
        print(f"Presigned URL expires in: {upload_response['expires_in']} seconds")
        
        # Step 2: Simulate file upload to S3 (client would upload here)
        print("\n--- Step 2: Simulate S3 Upload ---")
        print("(In production, client uploads file using presigned URL)")
        
        # Mock S3 object exists
        mock_s3.head_object.return_value = {
            "ContentType": "image/jpeg",
            "ContentLength": 2048000
        }
        
        # Step 3: Complete upload and save metadata
        print("\n--- Step 3: Complete Upload ---")
        
        mock_table.put_item.return_value = {}
        
        complete_request = {
            "image_id": image_id,
            "user_id": "test-user-123",
            "filename": "vacation-photo.jpg",
            "content_type": "image/jpeg",
            "file_size": 2048000,
            "tags": ["vacation", "beach"],
            "description": "Beach vacation photo"
        }
        
        event = sample_lambda_event(
            method="POST",
            path="/images/complete",
            body=json.dumps(complete_request)
        )
        
        response = complete_upload.handler(event, lambda_context)
        assert response["statusCode"] == 200
        
        complete_response = json.loads(response["body"])
        print(f"Upload status: {complete_response['status']}")
        print(f"Message: {complete_response['message']}")
        
        # Step 4: Generate download URL
        print("\n--- Step 4: Generate Download URL ---")
        
        # Mock DynamoDB get_item
        mock_table.get_item.return_value = {
            "Item": {
                "image_id": image_id,
                "user_id": "test-user-123",
                "filename": "vacation-photo.jpg",
                "content_type": "image/jpeg",
                "file_size": 2048000,
                "upload_timestamp": datetime.utcnow().isoformat(),
                "tags": ["vacation", "beach"],
                "description": "Beach vacation photo",
                "status": ImageStatus.COMPLETED.value,
                "s3_key": s3_key
            }
        }
        
        mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/download-url"
        
        event = sample_lambda_event(
            method="GET",
            path=f"/images/{image_id}/download-url",
            path_params={"image_id": image_id}
        )
        
        response = get_image_presigned_url.handler(event, lambda_context)
        assert response["statusCode"] == 200
        
        download_response = json.loads(response["body"])
        print(f"Download URL generated: {download_response['presigned_url']}")
        print(f"Expires in: {download_response['expires_in']} seconds")
        
        # Verify workflow completed successfully
        assert download_response["image_id"] == image_id
        assert download_response["filename"] == "vacation-photo.jpg"
        assert download_response["content_type"] == "image/jpeg"
        
        print("\n--- Workflow Completed Successfully ---")
