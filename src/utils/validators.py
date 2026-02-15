"""
Input validation utilities.
"""
import re
from typing import Optional
from datetime import datetime


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        uuid_string: String to validate
    
    Returns:
        True if valid UUID, False otherwise
    """
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(uuid_string))


def validate_image_extension(filename: str) -> bool:
    """
    Validate image file extension.
    
    Args:
        filename: Filename to validate
    
    Returns:
        True if valid image extension, False otherwise
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    return any(filename.lower().endswith(ext) for ext in allowed_extensions)


def validate_content_type(content_type: str) -> bool:
    """
    Validate image content type.
    
    Args:
        content_type: MIME type to validate
    
    Returns:
        True if valid content type, False otherwise
    """
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
    return content_type in allowed_types


def validate_iso_date(date_string: Optional[str]) -> bool:
    """
    Validate ISO 8601 date format.
    
    Args:
        date_string: Date string to validate
    
    Returns:
        True if valid ISO date, False otherwise
    """
    if not date_string:
        return True
    
    try:
        datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Replace unsafe characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_len = 255 - len(ext) - 1
        filename = f"{name[:max_name_len]}.{ext}" if ext else name[:255]
    
    return filename
