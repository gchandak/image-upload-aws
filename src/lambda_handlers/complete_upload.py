"""
Lambda handler for completing image upload and saving metadata.
"""
import json
from datetime import datetime
from pydantic import ValidationError
from src.models.requests import CompleteUploadRequest
from src.models.responses import CompleteUploadResponse
from src.models.image import ImageMetadata, ImageStatus
from src.services.s3_service import s3_service
from src.services.dynamodb_service import dynamodb_service
from src.utils.api_response import success_response, validation_error_response, not_found_response, internal_error_response
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def handler(event, context):
    """
    Complete image upload by verifying S3 object and saving metadata to DynamoDB.
    
    Request:
        POST /images/complete
        Body: {
            "image_id": "uuid",
            "user_id": "user123",
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "file_size": 102400,
            "tags": ["vacation"],
            "description": "Beach photo"
        }
    
    Response:
        {
            "image_id": "uuid",
            "status": "completed",
            "message": "Image upload completed successfully"
        }
    """
    try:
        logger.info("Processing complete upload request")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate request
        try:
            request = CompleteUploadRequest(**body)
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return validation_error_response(
                "Invalid request data",
                details={"errors": e.errors()}
            )
        
        # Extract metadata from event (should be stored temporarily during presigned URL generation)
        # For this implementation, we'll extract from path parameters or query string
        # In production, you might store this in a temporary cache (Redis/DynamoDB) during step 1
        
        # Extract metadata from request body
        filename = request.filename
        content_type = request.content_type
        file_size = request.file_size
        tags = request.tags
        description = request.description
        
        # Construct S3 key
        s3_key = f"images/{request.user_id}/{request.image_id}_{filename}"
        
        # Verify object exists in S3
        if not s3_service.check_object_exists(s3_key):
            logger.warning(f"Image not found in S3: {s3_key}")
            return not_found_response("Image not uploaded to S3. Please upload the file first.")
        
        # Get actual file metadata from S3
        s3_metadata = s3_service.get_object_metadata(s3_key)
        if s3_metadata:
            content_type = s3_metadata.get('content_type', content_type)
            file_size = s3_metadata.get('content_length', file_size)
        
        # Create metadata object
        metadata = ImageMetadata(
            image_id=request.image_id,
            user_id=request.user_id,
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            upload_timestamp=datetime.utcnow().isoformat(),
            tags=tags,
            description=description,
            status=ImageStatus.COMPLETED,
            s3_key=s3_key
        )
        
        # Save to DynamoDB
        dynamodb_service.put_item(metadata)
        
        # Prepare response
        response_data = CompleteUploadResponse(
            image_id=request.image_id,
            status="completed",
            message="Image upload completed successfully"
        )
        
        logger.info(f"Completed upload for image: {request.image_id}")
        
        return success_response(response_data.dict(), status_code=200)
    
    except Exception as e:
        logger.error(f"Error completing upload: {str(e)}", exc_info=True)
        return internal_error_response(f"Failed to complete upload: {str(e)}")
