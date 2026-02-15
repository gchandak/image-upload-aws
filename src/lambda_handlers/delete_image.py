"""
Lambda handler for deleting an image.
"""
import json
from pydantic import ValidationError
from src.models.requests import DeleteImageRequest
from src.models.responses import DeleteImageResponse
from src.services.s3_service import s3_service
from src.services.dynamodb_service import dynamodb_service
from src.utils.api_response import success_response, validation_error_response, not_found_response, unauthorized_response, internal_error_response
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def handler(event, context):
    """
    Delete an image from S3 and DynamoDB.
    
    Request:
        DELETE /images/{image_id}
        Body: {
            "user_id": "user123"
        }
    
    Response:
        {
            "image_id": "uuid",
            "status": "deleted",
            "message": "Image deleted successfully"
        }
    """
    try:
        logger.info("Processing delete image request")
        
        # Extract image_id from path parameters
        path_params = event.get('pathParameters') or {}
        image_id = path_params.get('image_id')
        
        if not image_id:
            return validation_error_response("Missing image_id in path")
        
        # Parse request body for user_id (for authorization)
        body = json.loads(event.get('body', '{}'))
        user_id = body.get('user_id')
        
        if not user_id:
            return validation_error_response("Missing user_id in request body")
        
        # Retrieve metadata from DynamoDB
        metadata = dynamodb_service.get_item(image_id)
        
        if not metadata:
            logger.warning(f"Image not found: {image_id}")
            return not_found_response(f"Image not found: {image_id}")
        
        # Verify user owns the image (basic authorization)
        if metadata.user_id != user_id:
            logger.warning(f"Unauthorized delete attempt by {user_id} for image {image_id}")
            return unauthorized_response("You don't have permission to delete this image")
        
        # Delete from S3
        try:
            s3_service.delete_object(metadata.s3_key)
        except Exception as e:
            logger.error(f"Failed to delete from S3: {str(e)}")
            # Continue to delete metadata even if S3 deletion fails
        
        # Delete from DynamoDB
        dynamodb_service.delete_item(image_id)
        
        # Prepare response
        response_data = DeleteImageResponse(
            image_id=image_id,
            status="deleted",
            message="Image deleted successfully"
        )
        
        logger.info(f"Deleted image: {image_id}")
        
        return success_response(response_data.dict(), status_code=200)
    
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}", exc_info=True)
        return internal_error_response(f"Failed to delete image: {str(e)}")
