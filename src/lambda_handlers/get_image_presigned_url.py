"""
Lambda handler for generating presigned URL for image download.
"""
import json
from src.models.responses import PresignedDownloadUrlResponse
from src.services.s3_service import s3_service
from src.services.dynamodb_service import dynamodb_service
from src.utils.api_response import success_response, not_found_response, internal_error_response
from src.utils.logger import setup_logger
from src.utils.config import config

logger = setup_logger(__name__)


def handler(event, context):
    """
    Generate presigned URL for image download.
    
    Request:
        GET /images/{image_id}/download-url
    
    Response:
        {
            "image_id": "uuid",
            "presigned_url": "https://...",
            "expires_in": 900,
            "filename": "photo.jpg",
            "content_type": "image/jpeg"
        }
    """
    try:
        logger.info("Processing download presigned URL request")
        
        # Extract image_id from path parameters
        path_params = event.get('pathParameters') or {}
        image_id = path_params.get('image_id')
        
        if not image_id:
            return validation_error_response("Missing image_id in path")
        
        # Retrieve metadata from DynamoDB
        metadata = dynamodb_service.get_item(image_id)
        
        if not metadata:
            logger.warning(f"Image not found: {image_id}")
            return not_found_response(f"Image not found: {image_id}")
        
        # Verify object exists in S3
        if not s3_service.check_object_exists(metadata.s3_key):
            logger.error(f"Image metadata exists but S3 object missing: {metadata.s3_key}")
            return not_found_response("Image file not found in storage")
        
        # Generate presigned GET URL
        presigned_url = s3_service.generate_presigned_get(
            s3_key=metadata.s3_key,
            expires_in=config.S3_PRESIGNED_URL_EXPIRY_DOWNLOAD,
            filename=metadata.filename
        )
        
        # Prepare response
        response_data = PresignedDownloadUrlResponse(
            image_id=image_id,
            presigned_url=presigned_url,
            expires_in=config.S3_PRESIGNED_URL_EXPIRY_DOWNLOAD,
            filename=metadata.filename,
            content_type=metadata.content_type
        )
        
        logger.info(f"Generated download URL for image: {image_id}")
        
        return success_response(response_data.dict(), status_code=200)
    
    except Exception as e:
        logger.error(f"Error generating download URL: {str(e)}", exc_info=True)
        return internal_error_response(f"Failed to generate download URL: {str(e)}")
