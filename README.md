# Mont Image Service API

A serverless, scalable image upload and management service built with **AWS Lambda**, **API Gateway**, **S3**, and **DynamoDB**, running on **LocalStack** for local development.

## 🏗️ Architecture

### System Components

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│      API Gateway (REST)         │
│  ┌──────────────────────────┐   │
│  │   Rate Limiting:         │   │
│  │   - 1000 req/sec         │   │
│  │   - 500 burst limit      │   │
│  │   - 10K req/day quota    │   │
│  └──────────────────────────┘   │
└───────┬─────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────┐
│              Lambda Functions                    │
│  ┌────────────────┐  ┌──────────────────────┐   │
│  │ Upload         │  │ Complete Upload      │   │
│  │ Presigned URL  │  │ Save Metadata        │   │
│  └────────────────┘  └──────────────────────┘   │
│  ┌────────────────┐  ┌──────────────────────┐   │
│  │ List Images    │  │ Download Presigned   │   │
│  │ (Filters+Page) │  │ URL                  │   │
│  └────────────────┘  └──────────────────────┘   │
│  ┌────────────────┐                              │
│  │ Delete Image   │                              │
│  └────────────────┘                              │
└───────┬──────────────────────┬───────────────────┘
        │                      │
        ▼                      ▼
┌──────────────┐      ┌──────────────────┐
│   Amazon S3  │      │   DynamoDB       │
│              │      │                  │
│  Image       │      │  Metadata:       │
│  Storage     │      │  - image_id (PK) │
│              │      │  - user_id (GSI) │
│  Direct      │      │  - timestamp     │
│  Upload/     │      │  - tags, desc... │
│  Download    │      │                  │
└──────────────┘      └──────────────────┘
```

### 📸 Image Upload Workflow (3-Step Process)

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ STEP 1: Request Presigned URL
     │ POST /images/upload-url
     │ {user_id, filename, content_type, file_size}
     ▼
┌─────────────────┐       ┌──────────────────┐
│  API Gateway    │──────▶│  Lambda:         │
│                 │       │  Generate        │
│  Rate Limited   │       │  Presigned URL   │
└─────────────────┘       └────────┬─────────┘
     ▲                             │
     │                             │ Generate S3 presigned URL
     │                             ▼
     │                    ┌──────────────────┐
     │                    │   Amazon S3      │
     │                    │                  │
     │                    │  • Validates     │
     │  Response:         │  • Creates URL   │
     │  {image_id,        │                  │
     │   presigned_url,   └──────────────────┘
     │   s3_key}                  │
     │                            │
┌────┴─────┐                     │
│  Client  │                     │
└────┬─────┘                     │
     │                            │
     │ STEP 2: Direct Upload to S3
     │ POST {presigned_url}
     │ File data (bypasses API Gateway)
     │                            │
     └────────────────────────────▼
                         ┌──────────────────┐
                         │   Amazon S3      │
                         │                  │
                         │  • Stores image  │
                         │  • Returns 200   │
                         └──────────────────┘
                                  │
                                  │ Upload complete
                                  ▼
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ STEP 3: Complete Upload & Save Metadata
     │ POST /images/complete
     │ {image_id, user_id, filename, content_type, file_size, tags, description}
     ▼
┌─────────────────┐       ┌──────────────────┐
│  API Gateway    │──────▶│  Lambda:         │
│                 │       │  Complete Upload │
└─────────────────┘       └────────┬─────────┘
     ▲                             │
     │                             │ 1. Verify S3 object exists
     │                             ▼
     │                    ┌──────────────────┐
     │                    │   Amazon S3      │
     │                    │  (Verification)  │
     │                    └──────────────────┘
     │                             │
     │                             │ 2. Save metadata
     │                             ▼
     │                    ┌──────────────────┐
     │  Response:         │   DynamoDB       │
     │  {image_id,        │                  │
     │   status:          │  • image_id (PK) │
     │   "completed"}     │  • user_id (GSI) │
     │                    │  • timestamp     │
┌────┴─────┐             │  • tags, desc... │
│  Client  │             └──────────────────┘
└──────────┘
   ✅ Upload Complete!
```

**Why 3 Steps?**
1. **Step 1 (Presigned URL)**: Generates secure, time-limited S3 upload URL
2. **Step 2 (Direct S3 Upload)**: Client uploads directly to S3 without routing through API Gateway (bypasses payload limits, reduces costs)
3. **Step 3 (Metadata Save)**: Verifies S3 upload succeeded and stores searchable metadata in DynamoDB

---

### 📋 List Images Workflow (with Filtering & Pagination)

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ GET /images?user_id=user123&start_date=2026-01-01&limit=50
     │
     ▼
┌─────────────────┐       ┌──────────────────┐
│  API Gateway    │──────▶│  Lambda:         │
│                 │       │  List Images     │
│  Rate Limited   │       │                  │
└─────────────────┘       └────────┬─────────┘
     ▲                             │
     │                             │ Query DynamoDB
     │                             │ (with filters + pagination)
     │                             ▼
     │                    ┌──────────────────┐
     │                    │   DynamoDB       │
     │                    │                  │
     │                    │  Query by:       │
     │                    │  • user_id (GSI) │
     │                    │  • date range    │
     │  Response:         │  • limit         │
     │  {images: [...],   │                  │
     │   count: 25,       │  Returns:        │
     │   next_token,      │  • Matching      │
     │   has_more: true}  │    records       │
     │                    │  • Pagination    │
┌────┴─────┐             │    token         │
│  Client  │             └──────────────────┘
└──────────┘
```

**Key Features:**
- **GSI Query**: Uses `user_id` Global Secondary Index for efficient filtering
- **Pagination**: Cursor-based with `next_token` for scalable result sets
- **Date Filtering**: Range queries on `upload_timestamp`
- **Response**: Returns metadata only (not actual images)

---

### 📥 Download Image Workflow (2-Step Process)

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ STEP 1: Get Download URL
     │ GET /images/{image_id}/download-url
     │
     ▼
┌─────────────────┐       ┌──────────────────┐
│  API Gateway    │──────▶│  Lambda:         │
│                 │       │  Get Download    │
│  Rate Limited   │       │  Presigned URL   │
└─────────────────┘       └────────┬─────────┘
     ▲                             │
     │                             │ 1. Get metadata
     │                             ▼
     │                    ┌──────────────────┐
     │                    │   DynamoDB       │
     │                    │                  │
     │                    │  Retrieve:       │
     │                    │  • s3_key        │
     │                    │  • filename      │
     │                    │  • content_type  │
     │                    └────────┬─────────┘
     │                             │
     │                             │ 2. Generate presigned URL
     │                             ▼
     │                    ┌──────────────────┐
     │  Response:         │   Amazon S3      │
     │  {image_id,        │                  │
     │   presigned_url,   │  • Validates key │
     │   filename,        │  • Creates URL   │
     │   expires_in: 900} │  • 15min expiry  │
     │                    └──────────────────┘
┌────┴─────┐                     │
│  Client  │                     │
└────┬─────┘                     │
     │                            │
     │ STEP 2: Direct Download from S3
     │ GET {presigned_url}
     │ (bypasses API Gateway)
     │                            │
     └────────────────────────────▼
                         ┌──────────────────┐
                         │   Amazon S3      │
                         │                  │
                         │  • Serves image  │
                         │  • Returns file  │
                         └──────────────────┘
                                  │
                                  │ Download complete
                                  ▼
                            ┌──────────┐
                            │  Client  │
                            └──────────┘
                               ✅ Image Downloaded!
```

**Why 2 Steps?**
1. **Step 1 (Get URL)**: Lambda retrieves metadata and generates time-limited download URL
2. **Step 2 (Direct Download)**: Client downloads directly from S3 (no bandwidth through API)

---

### 🗑️ Delete Image Workflow

```
┌──────────┐
│  Client  │
└────┬─────┘
     │
     │ DELETE /images/{image_id}
     │ {user_id: "user123"}
     │
     ▼
┌─────────────────┐       ┌──────────────────┐
│  API Gateway    │──────▶│  Lambda:         │
│                 │       │  Delete Image    │
│  Rate Limited   │       │                  │
└─────────────────┘       └────────┬─────────┘
     ▲                             │
     │                             │ 1. Get metadata & verify ownership
     │                             ▼
     │                    ┌──────────────────┐
     │                    │   DynamoDB       │
     │                    │                  │
     │                    │  Verify:         │
     │                    │  • Image exists  │
     │                    │  • user_id match │
     │                    └────────┬─────────┘
     │                             │
     │         ┌───────────────────┴───────────────────┐
     │         │                                       │
     │         │ 2. Delete from S3    3. Delete metadata
     │         ▼                                       ▼
     │  ┌──────────────┐                    ┌──────────────────┐
     │  │  Amazon S3   │                    │   DynamoDB       │
     │  │              │                    │                  │
     │  │  • Delete    │                    │  • Delete record │
     │  │    object    │                    │    (image_id)    │
     │  └──────────────┘                    └──────────────────┘
     │         │                                       │
     │         └───────────────────┬───────────────────┘
     │                             │
     │  Response:                  │
     │  {image_id,                 │
     │   status: "deleted",        │
     │   message: "Image           │
     │    deleted successfully"}   │
┌────┴─────┐                      │
│  Client  │◀─────────────────────┘
└──────────┘
   ✅ Image Deleted!
```

**Security & Ownership:**
- **Authorization**: Verifies `user_id` matches image owner before deletion
- **Atomic**: Deletes from both S3 and DynamoDB
- **Error Handling**: Returns 401 if unauthorized, 404 if image not found

### Key Features

✅ **Serverless Architecture** - AWS Lambda functions for automatic scaling  
✅ **Presigned URLs** - Direct S3 uploads/downloads (no API proxy overhead)  
✅ **Rate Limiting** - API Gateway throttling (1000 req/sec, 500 burst)  
✅ **Pagination** - Efficient listing with cursor-based pagination  
✅ **Filtering** - Search by user_id and date range using DynamoDB GSI  
✅ **LocalStack** - Complete local AWS environment for development  
✅ **Docker** - Containerized deployment  
✅ **Comprehensive Tests** - Unit & integration tests with pytest  

---

## 📋 Prerequisites

- **Docker** & **Docker Compose** (v20.10+)
- **Python 3.10+** (for local development/testing)
- **AWS CLI** (for LocalStack interaction)

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd /Users/gchandak/Documents/work-personal/monty

# Copy environment variables
cp .env.example .env
```

### 2. Start LocalStack Services

```bash
# Using Docker Compose
docker-compose up -d


**Wait for initialization** (~45 seconds). LocalStack will automatically:
- Create S3 bucket (`mont-images`)
- Create DynamoDB table with GSI
- Deploy all 5 Lambda functions
- Configure API Gateway with throttling
- Set up CORS

### 3. Verify Deployment

```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

### 4. Complete Workflow Example

```bash
# Get the API Gateway ID from logs
API_ID=$(docker-compose logs localstack | grep "API Gateway ID:" | tail -1 | awk '{print $NF}')
echo "Using API Gateway ID: $API_ID"

```

## 📖 API Documentation

### Base URL (LocalStack)
```
http://localhost:4566/restapis/{API_ID}/dev/_user_request_
```

Replace `{API_ID}` with your API Gateway ID from the initialization output.

> **⚠️ Important for Presigned URLs:**  
> LocalStack returns presigned URLs with the internal Docker IP (`http://172.22.0.2:4566`).  
> **When calling from your host machine**, replace `172.22.0.2` with `localhost`:  
> `http://172.22.0.2:4566/...` → `http://localhost:4566/...`

---

### 🔹 1. Generate Presigned Upload URL

**Endpoint:** `POST /images/upload-url`

**Description:** Get a presigned URL for direct S3 upload (bypasses Lambda payload limits).

**Request Body:**
```json
{
  "user_id": "user123",
  "filename": "vacation-photo.jpg",
  "content_type": "image/jpeg",
  "file_size": 2048000,
  "tags": ["vacation", "beach"],
  "description": "Beach vacation photo"
}
```

**Response (200 OK):**
```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "presigned_url": "https://s3.amazonaws.com/mont-images",
  "fields": {
    "key": "images/user123/550e8400_vacation-photo.jpg",
    "Content-Type": "image/jpeg"
  },
  "expires_in": 3600,
  "s3_key": "images/user123/550e8400_vacation-photo.jpg"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/upload-url \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "filename": "test.jpg",
    "content_type": "image/jpeg",
    "file_size": 1024000
  }'
```

**Client Upload (after getting presigned URL):**
```bash
# ⚠️ IMPORTANT: Replace 172.22.0.2 with localhost in the presigned_url!
# Example: http://172.22.0.2:4566/... → http://localhost:4566/...

# Get the key, image ID and presigned url from above response

curl -X POST "${presigned-url}" \
  -F "key={key}" \  
  -F "Content-Type={fields.Content-Type}" \
  -F "file=@/path/to/image.jpg"

# Complete example with actual file:
curl -X POST "http://localhost:4566/mont-images" \
  -F "key=images/user123/550e8400_vacation-photo.jpg" \
  -F "Content-Type=image/jpeg" \
  -F "file=@/Users/yourusername/Desktop/photo.jpg"
```

> 💡 **Tip:** You can also extract and fix the URL automatically:  
> ```bash
> PRESIGNED_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['presigned_url'].replace('172.22.0.2', 'localhost'))")
> ```

---

### 🔹 2. Complete Upload

**Endpoint:** `POST /images/complete`

**Description:** Finalize upload and save metadata to DynamoDB after S3 upload succeeds.

**Request Body:**
```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user123",
  "filename": "vacation-photo.jpg",
  "content_type": "image/jpeg",
  "file_size": 2048000,
  "tags": ["vacation", "beach"],
  "description": "Beach vacation photo"
}
```

**Response (200 OK):**
```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Image upload completed successfully"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/complete" \
  -H "Content-Type: application/json" \
  -d '{
    "image_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user123",
    "filename": "test.jpg",
    "content_type": "image/jpeg",
    "file_size": 1024000,
    "tags": ["demo"],
    "description": "Test image"
  }'
```

---

### 🔹 3. List Images (with Filters)

**Endpoint:** `GET /images`

**Description:** List images with optional filtering by user_id and date range. Supports pagination.

**Query Parameters:**
- `user_id` (optional) - Filter by user
- `start_date` (optional) - Start date (ISO 8601: `2026-01-01T00:00:00`)
- `end_date` (optional) - End date (ISO 8601: `2026-12-31T23:59:59`)
- `limit` (optional, default: 50, max: 100) - Page size
- `next_token` (optional) - Pagination token from previous response

**Response (200 OK):**
```json
{
  "images": [
    {
      "image_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user123",
      "filename": "vacation-photo.jpg",
      "content_type": "image/jpeg",
      "file_size": 2048000,
      "upload_timestamp": "2026-02-13T10:30:00",
      "tags": ["vacation", "beach"],
      "description": "Beach vacation photo",
      "status": "completed",
      "s3_key": "images/user123/550e8400_vacation-photo.jpg"
    }
  ],
  "count": 1,
  "next_token": "eyJMYXN0S2V5IjoiLi4uIn0=",
  "has_more": true
}
```

**cURL Examples:**
```bash
# List all images
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images"

# Filter by user
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?user_id=user123"

# Filter by user and date range
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?user_id=user123&start_date=2026-01-01T00:00:00&end_date=2026-02-13T23:59:59"

# Pagination
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?limit=50&next_token=eyJMYXN0S2V5IjoiLi4uIn0="
```

---

### 🔹 4. Get Download URL

**Endpoint:** `GET /images/{image_id}/download-url`

**Description:** Generate presigned URL for direct S3 download.

**Path Parameters:**
- `image_id` - Image UUID

**Response (200 OK):**
```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "presigned_url": "https://s3.amazonaws.com/mont-images/...",
  "expires_in": 900,
  "filename": "vacation-photo.jpg",
  "content_type": "image/jpeg"
}
```

**cURL Example:**
```bash
# Get download URL
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/550e8400-e29b-41d4-a716-446655440000/download-url"

# Complete example: Get URL and download image
DOWNLOAD_RESPONSE=$(curl -s "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/550e8400-e29b-41d4-a716-446655440000/download-url")

# Extract presigned URL and replace Docker IP with localhost
PRESIGNED_URL=$(echo "$DOWNLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['presigned_url'].replace('172.22.0.2', 'localhost'))")

# Download the image
curl -o downloaded-image.jpg "$PRESIGNED_URL"
```

> **💡 Tip:** The presigned URL expires in 15 minutes. The response includes `expires_in` field showing remaining seconds.

---

### 🔹 5. Delete Image

**Endpoint:** `DELETE /images/{image_id}`

**Description:** Delete image from S3 and metadata from DynamoDB.

**Path Parameters:**
- `image_id` - Image UUID

**Request Body:**
```json
{
  "user_id": "user123"
}
```

**Response (200 OK):**
```json
{
  "image_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "deleted",
  "message": "Image deleted successfully"
}
```

**Error Responses:**
- `401 Unauthorized` - User doesn't own the image
- `404 Not Found` - Image doesn't exist

**cURL Example:**
```bash
curl -X DELETE "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'
```

---

## 🎯 Scalability Strategies

### 1. **Presigned URLs for Direct S3 Access**
- **Upload**: Client uploads directly to S3 (no Lambda payload limit)
- **Download**: Client downloads directly from S3 (no API server bottleneck)
- **Result**: Reduces Lambda invocations and API Gateway bandwidth

### 2. **Rate Limiting & Throttling**
- **API Gateway Limits**:
  - Rate: 1000 requests/second
  - Burst: 500 concurrent requests
  - Quota: 10,000 requests/day per API key
- **Protection**: Prevents abuse and ensures fair usage

### 3. **DynamoDB Global Secondary Index (GSI)**
- **Primary Key**: `image_id` (for fast lookups)
- **GSI**: `user_id` (PK) + `upload_timestamp` (SK)
- **Benefit**: Efficient filtering without full table scans

### 4. **Pagination**
- **Cursor-based**: Uses DynamoDB's `LastEvaluatedKey`
- **Default page size**: 50 items
- **Max page size**: 100 items
- **Benefit**: Prevents large result sets from overwhelming clients

### 5. **Lambda Auto-Scaling**
- **Concurrent executions**: Up to 1000 (default AWS limit)
- **Cold start mitigation**: Provisioned concurrency (optional)
- **Benefit**: Automatic horizontal scaling

### 6. **Connection Pooling**
- **boto3 clients**: Initialized outside handler (reused across invocations)
- **Benefit**: Reduces connection overhead

---

## 🧪 Testing

### Run All Tests
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/ -m unit

# Run integration tests only
pytest tests/integration/ -m integration
```

### Test Coverage
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Test Categories

**Unit Tests** (`tests/unit/`)
- `test_s3_service.py` - S3 operations (presigned URLs, upload/download)
- `test_dynamodb_service.py` - DynamoDB CRUD, GSI queries
- `test_lambda_handlers.py` - Lambda function logic

**Integration Tests** (`tests/integration/`)
- `test_presigned_workflow.py` - End-to-end upload/download workflow
- `test_rate_limiting.py` - Concurrent requests, burst handling

---

## 🛠️ Development

### Project Structure
```
monty/
├── src/
│   ├── lambda_handlers/          # Lambda function handlers
│   │   ├── upload_presigned_url.py
│   │   ├── complete_upload.py
│   │   ├── list_images.py
│   │   ├── get_image_presigned_url.py
│   │   └── delete_image.py
│   ├── services/                 # AWS service wrappers
│   │   ├── s3_service.py
│   │   └── dynamodb_service.py
│   ├── models/                   # Pydantic data models
│   │   ├── image.py
│   │   ├── requests.py
│   │   └── responses.py
│   └── utils/                    # Utilities
│       ├── api_response.py
│       ├── config.py
│       ├── validators.py
│       └── logger.py
├── tests/                        # Test suite
├── infrastructure/               # API Gateway configs
├── docker/                       # Docker & LocalStack setup
├── scripts/                      # Build scripts
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### Environment Variables
See `.env.example` for all configuration options:
- AWS credentials (use `test` for LocalStack)
- S3 bucket name
- DynamoDB table name
- Presigned URL expiration times
- Rate limiting settings

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/ --max-line-length=100 --exclude=__pycache__
```

---

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f localstack

# Rebuild
docker-compose up -d --build
```

---

## 🔧 Troubleshooting

### ⚠️ Presigned URLs with Docker IP (172.22.0.2)

**Problem:** Presigned URLs return internal Docker IP that's not accessible from host machine.

```bash
# ❌ This will fail from your terminal:
curl: (28) Failed to connect to 172.22.0.2 port 4566: Couldn't connect to server
```

**Solution:** Replace `172.22.0.2` with `localhost`:

```bash
# ✅ Correct:
curl -X POST "http://localhost:4566/mont-images" \
  -F "key=images/user123/abc123_test.png" \
  -F "Content-Type=image/png" \
  -F "file=@/Users/yourusername/Desktop/test.png"
```

**Why?** LocalStack runs inside Docker and uses the internal network IP (`172.22.0.2:4566`). Lambda functions see this internal IP through `AWS_ENDPOINT_URL`, but from your host machine (Mac/Windows terminal), you must use `localhost:4566`.

### LocalStack not initializing
```bash
# Check logs
docker-compose logs localstack

# Restart LocalStack
docker-compose restart localstack

# Manual initialization
docker exec -it mont-localstack /etc/localstack/init/ready.d/init-aws.sh
```

### Lambda function errors
```bash
# Invoke Lambda directly
aws --endpoint-url=http://localhost:4566 lambda invoke \
  --function-name upload_presigned_url \
  --payload '{"body": "{\"user_id\":\"test\",\"filename\":\"test.jpg\",\"content_type\":\"image/jpeg\",\"file_size\":1024}"}' \
  response.json

cat response.json
```

### DynamoDB query issues
```bash
# Check table
aws --endpoint-url=http://localhost:4566 dynamodb describe-table \
  --table-name ImageMetadata

# Scan items
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name ImageMetadata
```

### S3 bucket issues
```bash
# List buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# List objects
aws --endpoint-url=http://localhost:4566 s3 ls s3://mont-images --recursive
```

---

## 📊 Performance Metrics

### Expected Performance (LocalStack)
- **Upload URL generation**: < 100ms
- **Metadata save**: < 50ms
- **List images (50 items)**: < 200ms
- **Download URL generation**: < 100ms
- **Delete operation**: < 150ms

### Scaling Limits (AWS Production)
- **Lambda concurrent executions**: 1000 (default), up to 10,000+
- **API Gateway**: 10,000 requests/second
- **DynamoDB**: Unlimited throughput (on-demand mode)
- **S3**: 3,500 PUT/5,500 GET requests/second per prefix