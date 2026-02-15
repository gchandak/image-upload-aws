# Quick Start Guide

## 🚀 Get Started in 3 Commands

```bash
# 1. Start LocalStack
docker-compose up -d

# 2. Get API Gateway ID (wait ~30 seconds for init)
API_ID=$(docker-compose logs localstack | grep "API Gateway ID:" | tail -1 | awk '{print $NF}')
echo "API Gateway ID: $API_ID"

# 3. Test the API
curl -s -X POST "http://localhost:4566/restapis/${API_ID}/dev/_user_request_/images/upload-url" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "filename": "test.jpg", "content_type": "image/jpeg", "file_size": 102400}' | python3 -m json.tool
```

---

## ⚠️ Critical: Presigned URL IP Address

**LocalStack returns presigned URLs with internal Docker IP:**
```json
{
  "presigned_url": "http://172.22.0.2:4566/mont-images"
}
```

**❌ This will FAIL from your terminal:**
```bash
curl -X POST "http://172.22.0.2:4566/mont-images" ...
# Error: curl: (28) Failed to connect to 172.22.0.2
```

**✅ Replace with localhost:**
```bash
curl -X POST "http://localhost:4566/mont-images" ...
```

---

## 🎯 Complete Workflow

```bash
# Set API ID
API_ID=$(docker-compose logs localstack | grep "API Gateway ID:" | tail -1 | awk '{print $NF}')

# Step 1: Generate presigned upload URL
echo "=== Generating Upload URL ==="
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:4566/restapis/${API_ID}/dev/_user_request_/images/upload-url" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "filename": "test.png", "content_type": "image/png", "file_size": 102400, "tags": ["demo"], "description": "Test image"}')
IMAGE_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['image_id'])")
S3_KEY=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['fields']['key'])")
echo "Image ID: $IMAGE_ID"
echo "S3 Key: $S3_KEY"

# Step 2: Upload to S3 (⚠️ Replace path with your actual image!)
echo -e "\n=== Uploading to S3 ==="
curl -X POST "http://localhost:4566/mont-images" \
  -F "key=$S3_KEY" \
  -F "Content-Type=image/png" \
  -F "file=@/path/to/your/photo.jpg"
echo "Upload complete!"

# Step 3: Complete the upload and save metadata
echo -e "\n=== Completing Upload ==="
curl -s -X POST "http://localhost:4566/restapis/${API_ID}/dev/_user_request_/images/complete" \
  -H "Content-Type: application/json" \
  -d "{\"image_id\": \"${IMAGE_ID}\", \"user_id\": \"user123\", \"filename\": \"test.png\", \"content_type\": \"image/png\", \"file_size\": 102400, \"tags\": [\"demo\"], \"description\": \"Test image\"}" | python3 -m json.tool

# Step 4: List all images for user
echo -e "\n=== Listing Images ==="
curl -s "http://localhost:4566/restapis/${API_ID}/dev/_user_request_/images?user_id=user123" | python3 -m json.tool

# Step 5: Get download URL
echo -e "\n=== Getting Download URL ==="
curl -s "http://localhost:4566/restapis/${API_ID}/dev/_user_request_/images/${IMAGE_ID}/download-url" | python3 -m json.tool

# Step 6: Delete the image
echo -e "\n=== Deleting Image ==="
curl -s -X DELETE "http://localhost:4566/restapis/${API_ID}/dev/_user_request_/images/${IMAGE_ID}" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}' | python3 -m json.tool

# Step 7: Verify deletion
echo -e "\n=== Verifying Deletion ==="
curl -s "http://localhost:4566/restapis/${API_ID}/dev/_user_request_/images?user_id=user123" | python3 -m json.tool
```

---

## 📋 Copy-Paste Examples

### 1. Upload Image

```bash
# Generate upload URL
curl -X POST "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/upload-url" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123", "filename": "photo.jpg", "content_type": "image/jpeg", "file_size": 102400}'

# Upload to S3 (replace with actual values from response)
curl -X POST "http://localhost:4566/mont-images" \
  -F "key={fields.key from response}" \
  -F "Content-Type=image/jpeg" \
  -F "file=@/path/to/your/photo.jpg"

# Complete upload
curl -X POST "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/complete" \
  -H "Content-Type: application/json" \
  -d '{"image_id": "{IMAGE_ID from step 1}", "user_id": "user123", "filename": "photo.jpg", "content_type": "image/jpeg", "file_size": 102400, "tags": ["demo"], "description": "My photo"}'
```

### 2. List Images

```bash
# All images for a user
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?user_id=user123"

# With date filter
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images?user_id=user123&start_date=2026-02-01T00:00:00&end_date=2026-02-28T23:59:59"
```

### 3. Download Image

```bash
# Get download URL
curl "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/{IMAGE_ID}/download-url"

# Download (replace with presigned_url from response, using localhost!)
curl -o downloaded.jpg "http://localhost:4566/mont-images/images/..."
```

### 4. Delete Image

```bash
curl -X DELETE "http://localhost:4566/restapis/{API_ID}/dev/_user_request_/images/{IMAGE_ID}" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'
```

---

## 🔍 Find API Gateway ID

```bash
# From logs
docker-compose logs localstack | grep "API Gateway ID:"

# Using AWS CLI
aws --endpoint-url=http://localhost:4566 apigateway get-rest-apis --query 'items[0].id' --output text
```

---

## ✅ What's Working

- ✅ Upload presigned URL generation (UUID, S3 keys, 1hr expiry)
- ✅ Direct S3 upload (bypasses Lambda payload limits)
- ✅ Complete upload (saves metadata to DynamoDB)
- ✅ List images with filters (user_id, date range via GSI)
- ✅ Pagination (cursor-based, 50 items/page)
- ✅ Download presigned URLs (15min expiry)
- ✅ Delete (authorization check, removes from S3 + DynamoDB)
- ✅ Rate limiting (1000 req/sec, 500 burst via API Gateway)

---

## 🛠️ Troubleshooting

### Can't connect to 172.22.0.2
Replace Docker internal IP with `localhost` in all presigned URLs.

### API Gateway ID changed
API Gateway ID changes when LocalStack restarts. Get the latest ID from logs.

### Lambda errors
Check logs: `docker-compose logs localstack | grep ERROR`

### Need to restart
```bash
docker-compose restart localstack
# Wait 30 seconds for initialization
```

---

**📖 See [README.md](README.md) for complete documentation**
