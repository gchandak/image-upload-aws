#!/bin/bash

# LocalStack AWS Resource Initialization Script
# This script creates all necessary AWS resources for the Mont image service

set -e

echo "========================================="
echo "Initializing AWS Resources in LocalStack"
echo "========================================="

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
S3_BUCKET_NAME=${S3_BUCKET_NAME:-mont-images}
DYNAMODB_TABLE_NAME=${DYNAMODB_TABLE_NAME:-ImageMetadata}
DYNAMODB_GSI_NAME=${DYNAMODB_GSI_NAME:-UserIdTimestampIndex}
API_GATEWAY_NAME="ImageServiceAPI"
API_STAGE="dev"

# LocalStack endpoint
ENDPOINT_URL="http://localhost:4566"

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
sleep 5

# Create S3 bucket
echo "Creating S3 bucket: $S3_BUCKET_NAME"
aws --endpoint-url=$ENDPOINT_URL s3 mb s3://$S3_BUCKET_NAME --region $AWS_REGION || true

# Enable S3 versioning
echo "Enabling S3 versioning..."
aws --endpoint-url=$ENDPOINT_URL s3api put-bucket-versioning \
    --bucket $S3_BUCKET_NAME \
    --versioning-configuration Status=Enabled \
    --region $AWS_REGION || true

# Configure S3 CORS
echo "Configuring S3 CORS..."
aws --endpoint-url=$ENDPOINT_URL s3api put-bucket-cors \
    --bucket $S3_BUCKET_NAME \
    --cors-configuration '{
        "CORSRules": [{
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "POST", "PUT", "DELETE"],
            "AllowedHeaders": ["*"],
            "MaxAgeSeconds": 3000
        }]
    }' \
    --region $AWS_REGION || true

# Create DynamoDB table
echo "Creating DynamoDB table: $DYNAMODB_TABLE_NAME"
aws --endpoint-url=$ENDPOINT_URL dynamodb create-table \
    --table-name $DYNAMODB_TABLE_NAME \
    --attribute-definitions \
        AttributeName=image_id,AttributeType=S \
        AttributeName=user_id,AttributeType=S \
        AttributeName=upload_timestamp,AttributeType=S \
    --key-schema \
        AttributeName=image_id,KeyType=HASH \
    --global-secondary-indexes \
        "[{
            \"IndexName\": \"$DYNAMODB_GSI_NAME\",
            \"KeySchema\": [
                {\"AttributeName\": \"user_id\", \"KeyType\": \"HASH\"},
                {\"AttributeName\": \"upload_timestamp\", \"KeyType\": \"RANGE\"}
            ],
            \"Projection\": {\"ProjectionType\": \"ALL\"},
            \"ProvisionedThroughput\": {
                \"ReadCapacityUnits\": 5,
                \"WriteCapacityUnits\": 5
            }
        }]" \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region $AWS_REGION || true

echo "Waiting for DynamoDB table to be active..."
sleep 3

# Package Lambda functions
echo "Packaging Lambda functions..."
cd /app

# Create deployment package directory
mkdir -p /tmp/lambda_packages

# Function to create Lambda deployment package
create_lambda_package() {
    FUNCTION_NAME=$1
    echo "Creating package for $FUNCTION_NAME..."
    
    # Create temporary directory
    TEMP_DIR="/tmp/lambda_packages/$FUNCTION_NAME"
    mkdir -p $TEMP_DIR
    
    # Copy source code
    cp -r /app/src $TEMP_DIR/
    
    # Install dependencies directly into the package
    cd $TEMP_DIR
    pip install --upgrade pip -q
    pip install -r /app/requirements.txt -t . --upgrade -q
    cd /app
    
    # Create ZIP file
    cd $TEMP_DIR
    zip -r /tmp/lambda_packages/${FUNCTION_NAME}.zip . -q
    cd /app
    
    echo "Package created: ${FUNCTION_NAME}.zip"
}

# Create packages for all Lambda functions
LAMBDA_FUNCTIONS=("upload_presigned_url" "complete_upload" "list_images" "get_image_presigned_url" "delete_image")

for FUNC in "${LAMBDA_FUNCTIONS[@]}"; do
    create_lambda_package $FUNC
done

# Create Lambda functions
echo "Creating Lambda functions..."

for FUNC in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "Creating Lambda function: $FUNC"
    
    aws --endpoint-url=$ENDPOINT_URL lambda create-function \
        --function-name $FUNC \
        --runtime python3.10 \
        --role arn:aws:iam::000000000000:role/lambda-role \
        --handler src.lambda_handlers.${FUNC}.handler \
        --zip-file fileb:///tmp/lambda_packages/${FUNC}.zip \
        --timeout 30 \
        --memory-size 256 \
        --environment "Variables={
            AWS_REGION=$AWS_REGION,
            LOCALSTACK_ENDPOINT=$ENDPOINT_URL,
            S3_BUCKET_NAME=$S3_BUCKET_NAME,
            DYNAMODB_TABLE_NAME=$DYNAMODB_TABLE_NAME,
            DYNAMODB_GSI_NAME=$DYNAMODB_GSI_NAME,
            S3_PRESIGNED_URL_EXPIRY_UPLOAD=3600,
            S3_PRESIGNED_URL_EXPIRY_DOWNLOAD=900,
            LOG_LEVEL=INFO
        }" \
        --region $AWS_REGION || true
done

# Create API Gateway REST API
echo "Creating API Gateway REST API..."

API_ID=$(aws --endpoint-url=$ENDPOINT_URL apigateway create-rest-api \
    --name $API_GATEWAY_NAME \
    --description "Mont Image Service API" \
    --region $AWS_REGION \
    --output text \
    --query 'id')

echo "API Gateway ID: $API_ID"

# Get root resource ID
ROOT_RESOURCE_ID=$(aws --endpoint-url=$ENDPOINT_URL apigateway get-resources \
    --rest-api-id $API_ID \
    --region $AWS_REGION \
    --output text \
    --query 'items[0].id')

# Create /images resource
IMAGES_RESOURCE_ID=$(aws --endpoint-url=$ENDPOINT_URL apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part images \
    --region $AWS_REGION \
    --output text \
    --query 'id')

# Create /images/upload-url resource
UPLOAD_URL_RESOURCE_ID=$(aws --endpoint-url=$ENDPOINT_URL apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $IMAGES_RESOURCE_ID \
    --path-part upload-url \
    --region $AWS_REGION \
    --output text \
    --query 'id')

# Create /images/complete resource
COMPLETE_RESOURCE_ID=$(aws --endpoint-url=$ENDPOINT_URL apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $IMAGES_RESOURCE_ID \
    --path-part complete \
    --region $AWS_REGION \
    --output text \
    --query 'id')

# Create /images/{image_id} resource
IMAGE_ID_RESOURCE_ID=$(aws --endpoint-url=$ENDPOINT_URL apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $IMAGES_RESOURCE_ID \
    --path-part '{image_id}' \
    --region $AWS_REGION \
    --output text \
    --query 'id')

# Create /images/{image_id}/download-url resource
DOWNLOAD_URL_RESOURCE_ID=$(aws --endpoint-url=$ENDPOINT_URL apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $IMAGE_ID_RESOURCE_ID \
    --path-part download-url \
    --region $AWS_REGION \
    --output text \
    --query 'id')

# Function to create API Gateway method with Lambda integration
create_method() {
    RESOURCE_ID=$1
    HTTP_METHOD=$2
    LAMBDA_FUNCTION=$3
    
    echo "Creating $HTTP_METHOD method for resource $RESOURCE_ID -> $LAMBDA_FUNCTION"
    
    # Create method
    aws --endpoint-url=$ENDPOINT_URL apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method $HTTP_METHOD \
        --authorization-type NONE \
        --region $AWS_REGION || true
    
    # Set Lambda integration
    aws --endpoint-url=$ENDPOINT_URL apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method $HTTP_METHOD \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$AWS_REGION:000000000000:function:$LAMBDA_FUNCTION/invocations" \
        --region $AWS_REGION || true
}

# Create API methods
create_method $UPLOAD_URL_RESOURCE_ID POST upload_presigned_url
create_method $COMPLETE_RESOURCE_ID POST complete_upload
create_method $IMAGES_RESOURCE_ID GET list_images
create_method $DOWNLOAD_URL_RESOURCE_ID GET get_image_presigned_url
create_method $IMAGE_ID_RESOURCE_ID DELETE delete_image

# Enable CORS for all resources
enable_cors() {
    RESOURCE_ID=$1
    
    aws --endpoint-url=$ENDPOINT_URL apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method OPTIONS \
        --authorization-type NONE \
        --region $AWS_REGION || true
    
    aws --endpoint-url=$ENDPOINT_URL apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method OPTIONS \
        --type MOCK \
        --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
        --region $AWS_REGION || true
    
    aws --endpoint-url=$ENDPOINT_URL apigateway put-integration-response \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method OPTIONS \
        --status-code 200 \
        --response-parameters '{
            "method.response.header.Access-Control-Allow-Headers": "'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'",
            "method.response.header.Access-Control-Allow-Methods": "'"'"'GET,POST,PUT,DELETE,OPTIONS'"'"'",
            "method.response.header.Access-Control-Allow-Origin": "'"'"'*'"'"'"
        }' \
        --region $AWS_REGION || true
    
    aws --endpoint-url=$ENDPOINT_URL apigateway put-method-response \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method OPTIONS \
        --status-code 200 \
        --response-parameters '{
            "method.response.header.Access-Control-Allow-Headers": true,
            "method.response.header.Access-Control-Allow-Methods": true,
            "method.response.header.Access-Control-Allow-Origin": true
        }' \
        --region $AWS_REGION || true
}

enable_cors $UPLOAD_URL_RESOURCE_ID
enable_cors $COMPLETE_RESOURCE_ID
enable_cors $IMAGES_RESOURCE_ID
enable_cors $DOWNLOAD_URL_RESOURCE_ID
enable_cors $IMAGE_ID_RESOURCE_ID

# Deploy API
echo "Deploying API to stage: $API_STAGE"
aws --endpoint-url=$ENDPOINT_URL apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $API_STAGE \
    --region $AWS_REGION || true

# Configure throttling
echo "Configuring API throttling..."
aws --endpoint-url=$ENDPOINT_URL apigateway update-stage \
    --rest-api-id $API_ID \
    --stage-name $API_STAGE \
    --patch-operations \
        op=replace,path=/*/*/throttling/rateLimit,value=1000 \
        op=replace,path=/*/*/throttling/burstLimit,value=500 \
    --region $AWS_REGION || true

echo "========================================="
echo "AWS Resources Created Successfully!"
echo "========================================="
echo "S3 Bucket: $S3_BUCKET_NAME"
echo "DynamoDB Table: $DYNAMODB_TABLE_NAME"
echo "API Gateway ID: $API_ID"
echo "API Endpoint: $ENDPOINT_URL/restapis/$API_ID/$API_STAGE/_user_request_"
echo "========================================="
echo ""
echo "Example API URL:"
echo "POST $ENDPOINT_URL/restapis/$API_ID/$API_STAGE/_user_request_/images/upload-url"
echo ""
echo "Test with:"
echo "aws --endpoint-url=$ENDPOINT_URL apigateway get-rest-apis"
echo "========================================="
