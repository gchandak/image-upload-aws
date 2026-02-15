"""
Lambda handler for generating presigned URL for image upload.
"""
import json
import uuid
from datetime import datetime
from pydantic import ValidationError
from src.models.requests import UploadPresignedUrlRequest
from src.models.responses import PresignedUrlResponse
from src.services.s3_service import s3_service
from src.utils.api_response import success_response, validation_error_response, internal_error_response
from src.utils.validators import sanitize_filename
from src.utils.logger import setup_logger
from src.utils.config import config

logger = setup_logger(__name__)


def handler(event, context):
    """
    Generate presigned URL for direct S3 upload.
    
    Request:
        POST /images/upload-url
        Body: {
            "user_id": "user123",
            "filename": "photo.jpg",
            "content_type": "image/jpeg",
            "file_size": 1024000,
            "tags": ["vacation", "beach"],
            "description": "Beach vacation photo"
        }
    
    Response:
        {
            "image_id": "uuid",
            "presigned_url": "https://...",
            "fields": {...},
            "expires_in": 3600,
            "s3_key": "images/user123/uuid.jpg"
        }
    """
    try:
        logger.info("Processing upload presigned URL request")
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate request
        try:
            request = UploadPresignedUrlRequest(**body)
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return validation_error_response(
                "Invalid request data",
                details={"errors": e.errors()}
            )
        
        # Generate unique image ID
        image_id = str(uuid.uuid4())
        
        # Sanitize filename
        safe_filename = sanitize_filename(request.filename)
        
        # Create S3 key: images/{user_id}/{image_id}_{filename}
        s3_key = f"images/{request.user_id}/{image_id}_{safe_filename}"
        
        # Generate presigned POST URL
        presigned_data = s3_service.generate_presigned_post(
            s3_key=s3_key,
            content_type=request.content_type,
            file_size=request.file_size,
            expires_in=config.S3_PRESIGNED_URL_EXPIRY_UPLOAD
        )
        
        # Prepare response
        response_data = PresignedUrlResponse(
            image_id=image_id,
            presigned_url=presigned_data['url'],
            fields=presigned_data['fields'],
            expires_in=config.S3_PRESIGNED_URL_EXPIRY_UPLOAD,
            s3_key=s3_key
        )
        
        logger.info(f"Generated presigned URL for image: {image_id}")
        
        return success_response(response_data.dict(), status_code=200)
    
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}", exc_info=True)
        return internal_error_response(f"Failed to generate upload URL: {str(e)}")
