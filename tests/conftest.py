"""
Pytest configuration and fixtures for testing.
"""
import pytest
import boto3
import os
from moto import mock_s3, mock_dynamodb
from src.utils.config import config


@pytest.fixture(scope="function")
def aws_credentials():
    """Mock AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    """Create mock S3 client."""
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1")
        # Create test bucket
        s3.create_bucket(Bucket=config.S3_BUCKET_NAME)
        yield s3


@pytest.fixture(scope="function")
def dynamodb_client(aws_credentials):
    """Create mock DynamoDB client."""
    with mock_dynamodb():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        
        # Create test table
        table = dynamodb.create_table(
            TableName=config.DYNAMODB_TABLE_NAME,
            KeySchema=[
                {"AttributeName": "image_id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "image_id", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
                {"AttributeName": "upload_timestamp", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": config.DYNAMODB_GSI_NAME,
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                        {"AttributeName": "upload_timestamp", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 5,
                        "WriteCapacityUnits": 5
                    }
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            }
        )
        
        yield dynamodb


@pytest.fixture
def sample_image_metadata():
    """Sample image metadata for testing."""
    return {
        "user_id": "test-user-123",
        "filename": "test-image.jpg",
        "content_type": "image/jpeg",
        "file_size": 1024000,
        "tags": ["test", "sample"],
        "description": "Test image"
    }


@pytest.fixture
def sample_lambda_event():
    """Sample Lambda event for testing."""
    def _create_event(method="POST", path="/images/upload-url", body=None, path_params=None, query_params=None):
        return {
            "httpMethod": method,
            "path": path,
            "pathParameters": path_params or {},
            "queryStringParameters": query_params or {},
            "body": body,
            "headers": {
                "Content-Type": "application/json"
            }
        }
    return _create_event


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    class LambdaContext:
        function_name = "test-function"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        aws_request_id = "test-request-id"
    
    return LambdaContext()
