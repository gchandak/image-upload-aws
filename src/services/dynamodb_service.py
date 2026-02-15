"""
DynamoDB service for image metadata storage with GSI support.
"""
import boto3
from botocore.exceptions import ClientError
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.utils.config import config
from src.utils.logger import setup_logger
from src.models.image import ImageMetadata, ImageMetadataDB

logger = setup_logger(__name__)


class DynamoDBService:
    """Service for DynamoDB operations."""
    
    def __init__(self):
        """Initialize DynamoDB client."""
        self.table_name = config.DYNAMODB_TABLE_NAME
        self.gsi_name = config.DYNAMODB_GSI_NAME
        
        # Use LocalStack endpoint if configured
        endpoint_url = config.get_dynamodb_endpoint()
        
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            endpoint_url=endpoint_url
        )
        
        self.table = self.dynamodb.Table(self.table_name)
        logger.info(f"DynamoDB service initialized with table: {self.table_name}")
    
    def put_item(self, metadata: ImageMetadata) -> bool:
        """
        Save image metadata to DynamoDB.
        
        Args:
            metadata: ImageMetadata object
        
        Returns:
            True if successful
        
        Raises:
            ClientError: If put operation fails
        """
        try:
            now = datetime.utcnow().isoformat()
            
            item = metadata.dict()
            item['created_at'] = now
            item['updated_at'] = now
            item['status'] = metadata.status.value
            
            self.table.put_item(Item=item)
            logger.info(f"Saved metadata for image: {metadata.image_id}")
            return True
        
        except ClientError as e:
            logger.error(f"Failed to save metadata: {str(e)}")
            raise
    
    def get_item(self, image_id: str) -> Optional[ImageMetadata]:
        """
        Retrieve image metadata by ID.
        
        Args:
            image_id: Image identifier
        
        Returns:
            ImageMetadata object or None if not found
        """
        try:
            response = self.table.get_item(Key={'image_id': image_id})
            
            if 'Item' not in response:
                logger.info(f"Image not found: {image_id}")
                return None
            
            item = response['Item']
            return ImageMetadata(**item)
        
        except ClientError as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            raise
    
    def delete_item(self, image_id: str) -> bool:
        """
        Delete image metadata from DynamoDB.
        
        Args:
            image_id: Image identifier
        
        Returns:
            True if successful
        
        Raises:
            ClientError: If delete operation fails
        """
        try:
            self.table.delete_item(Key={'image_id': image_id})
            logger.info(f"Deleted metadata for image: {image_id}")
            return True
        
        except ClientError as e:
            logger.error(f"Failed to delete metadata: {str(e)}")
            raise
    
    def query_by_user(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        last_evaluated_key: Optional[Dict] = None
    ) -> Tuple[List[ImageMetadata], Optional[Dict]]:
        """
        Query images by user_id using GSI with optional date range filter.
        
        Args:
            user_id: User identifier
            start_date: Start date for filtering (ISO 8601)
            end_date: End date for filtering (ISO 8601)
            limit: Maximum number of items to return
            last_evaluated_key: Pagination token
        
        Returns:
            Tuple of (list of ImageMetadata, next pagination token)
        """
        try:
            # Build key condition expression
            key_condition = 'user_id = :user_id'
            expression_values = {':user_id': user_id}
            
            # Add date range to key condition if both dates provided
            if start_date and end_date:
                key_condition += ' AND upload_timestamp BETWEEN :start_date AND :end_date'
                expression_values[':start_date'] = start_date
                expression_values[':end_date'] = end_date
            elif start_date:
                key_condition += ' AND upload_timestamp >= :start_date'
                expression_values[':start_date'] = start_date
            elif end_date:
                key_condition += ' AND upload_timestamp <= :end_date'
                expression_values[':end_date'] = end_date
            
            query_params = {
                'IndexName': self.gsi_name,
                'KeyConditionExpression': key_condition,
                'ExpressionAttributeValues': expression_values,
                'Limit': limit,
                'ScanIndexForward': False  # Sort by timestamp descending (newest first)
            }
            
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = self.table.query(**query_params)
            
            images = [ImageMetadata(**item) for item in response.get('Items', [])]
            next_key = response.get('LastEvaluatedKey')
            
            logger.info(f"Queried {len(images)} images for user: {user_id}")
            return images, next_key
        
        except ClientError as e:
            logger.error(f"Failed to query images: {str(e)}")
            raise
    
    def scan_all(
        self,
        limit: int = 50,
        last_evaluated_key: Optional[Dict] = None
    ) -> Tuple[List[ImageMetadata], Optional[Dict]]:
        """
        Scan all images (no filter).
        
        Args:
            limit: Maximum number of items to return
            last_evaluated_key: Pagination token
        
        Returns:
            Tuple of (list of ImageMetadata, next pagination token)
        """
        try:
            scan_params = {
                'Limit': limit
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = self.table.scan(**scan_params)
            
            images = [ImageMetadata(**item) for item in response.get('Items', [])]
            next_key = response.get('LastEvaluatedKey')
            
            logger.info(f"Scanned {len(images)} images")
            return images, next_key
        
        except ClientError as e:
            logger.error(f"Failed to scan images: {str(e)}")
            raise
    
    def update_status(self, image_id: str, status: str) -> bool:
        """
        Update image upload status.
        
        Args:
            image_id: Image identifier
            status: New status value
        
        Returns:
            True if successful
        """
        try:
            now = datetime.utcnow().isoformat()
            
            self.table.update_item(
                Key={'image_id': image_id},
                UpdateExpression='SET #status = :status, updated_at = :updated_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': status,
                    ':updated_at': now
                }
            )
            
            logger.info(f"Updated status for image {image_id} to {status}")
            return True
        
        except ClientError as e:
            logger.error(f"Failed to update status: {str(e)}")
            raise


# Global service instance (reused across Lambda invocations)
dynamodb_service = DynamoDBService()
