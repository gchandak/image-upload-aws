"""
Lambda handler for listing images with filters (user_id, date range).
"""
import json
import base64
from pydantic import ValidationError
from src.models.requests import ListImagesRequest
from src.models.responses import ListImagesResponse
from src.services.dynamodb_service import dynamodb_service
from src.utils.api_response import success_response, validation_error_response, internal_error_response
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def handler(event, context):
    """
    List images with optional filters.
    
    Request:
        GET /images?user_id=user123&start_date=2026-01-01T00:00:00&end_date=2026-02-13T23:59:59&limit=50&next_token=...
    
    Response:
        {
            "images": [...],
            "count": 50,
            "next_token": "base64_encoded_token",
            "has_more": true
        }
    """
    try:
        logger.info("Processing list images request")
        
        # Parse query parameters
        query_params = event.get('queryStringParameters') or {}
        
        # Build request object
        request_data = {
            'user_id': query_params.get('user_id'),
            'start_date': query_params.get('start_date'),
            'end_date': query_params.get('end_date'),
            'limit': int(query_params.get('limit', 50)),
            'next_token': query_params.get('next_token')
        }
        
        # Validate request
        try:
            request = ListImagesRequest(**request_data)
        except ValidationError as e:
            logger.warning(f"Validation error: {e}")
            return validation_error_response(
                "Invalid request parameters",
                details={"errors": e.errors()}
            )
        
        # Decode pagination token if present
        last_evaluated_key = None
        if request.next_token:
            try:
                last_evaluated_key = json.loads(base64.b64decode(request.next_token))
            except Exception as e:
                logger.warning(f"Invalid pagination token: {e}")
                return validation_error_response("Invalid pagination token")
        
        # Query based on filters
        if request.user_id:
            # Query by user_id using GSI with optional date range
            images, next_key = dynamodb_service.query_by_user(
                user_id=request.user_id,
                start_date=request.start_date,
                end_date=request.end_date,
                limit=request.limit,
                last_evaluated_key=last_evaluated_key
            )
        else:
            # Scan all images (no filter)
            images, next_key = dynamodb_service.scan_all(
                limit=request.limit,
                last_evaluated_key=last_evaluated_key
            )
        
        # Encode next pagination token
        next_token = None
        if next_key:
            next_token = base64.b64encode(json.dumps(next_key).encode()).decode()
        
        # Prepare response
        response_data = ListImagesResponse(
            images=images,
            count=len(images),
            next_token=next_token,
            has_more=next_key is not None
        )
        
        logger.info(f"Listed {len(images)} images")
        
        return success_response(response_data.dict(), status_code=200)
    
    except Exception as e:
        logger.error(f"Error listing images: {str(e)}", exc_info=True)
        return internal_error_response(f"Failed to list images: {str(e)}")
