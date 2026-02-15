"""
Utility functions for API Gateway response formatting.
"""
import json
from typing import Any, Dict, Optional
from http import HTTPStatus


def create_response(
    status_code: int,
    body: Any,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Create API Gateway formatted response.
    
    Args:
        status_code: HTTP status code
        body: Response body (will be JSON serialized)
        headers: Optional HTTP headers
    
    Returns:
        API Gateway response dictionary
    """
    default_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body) if not isinstance(body, str) else body
    }


def success_response(data: Any, status_code: int = HTTPStatus.OK) -> Dict[str, Any]:
    """Create a success response."""
    return create_response(status_code, data)


def error_response(
    error: str,
    message: str,
    status_code: int = HTTPStatus.BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create an error response."""
    body = {
        'error': error,
        'message': message
    }
    if details:
        body['details'] = details
    
    return create_response(status_code, body)


def validation_error_response(message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a validation error response."""
    return error_response('ValidationError', message, HTTPStatus.BAD_REQUEST, details)


def not_found_response(message: str = 'Resource not found') -> Dict[str, Any]:
    """Create a not found error response."""
    return error_response('NotFound', message, HTTPStatus.NOT_FOUND)


def internal_error_response(message: str = 'Internal server error') -> Dict[str, Any]:
    """Create an internal server error response."""
    return error_response('InternalError', message, HTTPStatus.INTERNAL_SERVER_ERROR)


def unauthorized_response(message: str = 'Unauthorized') -> Dict[str, Any]:
    """Create an unauthorized error response."""
    return error_response('Unauthorized', message, HTTPStatus.UNAUTHORIZED)


def throttle_response(message: str = 'Too many requests') -> Dict[str, Any]:
    """Create a throttle error response."""
    return error_response('ThrottleError', message, HTTPStatus.TOO_MANY_REQUESTS)
