"""
Integration test for rate limiting and throttling.
"""
import pytest
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
from src.lambda_handlers import list_images


@pytest.mark.integration
@pytest.mark.slow
class TestRateLimiting:
    """Test rate limiting and throttling behavior."""
    
    def test_concurrent_requests(self, sample_lambda_event, lambda_context):
        """Test handling multiple concurrent requests."""
        
        @patch('src.lambda_handlers.list_images.dynamodb_service')
        def make_request(mock_dynamodb_service):
            """Make a single request."""
            mock_dynamodb_service.scan_all.return_value = ([], None)
            
            event = sample_lambda_event(
                method="GET",
                path="/images",
                query_params={"limit": "10"}
            )
            
            return list_images.handler(event, lambda_context)
        
        # Simulate 100 concurrent requests
        num_requests = 100
        successful_requests = 0
        failed_requests = 0
        
        print(f"\n--- Testing {num_requests} Concurrent Requests ---")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            
            for future in as_completed(futures):
                try:
                    response = future.result()
                    if response["statusCode"] == 200:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                except Exception as e:
                    failed_requests += 1
                    print(f"Request failed: {str(e)}")
        
        print(f"Successful requests: {successful_requests}")
        print(f"Failed requests: {failed_requests}")
        
        # At least 90% should succeed (accounting for potential throttling)
        success_rate = successful_requests / num_requests
        assert success_rate >= 0.9, f"Success rate {success_rate} below threshold"
    
    @patch('src.lambda_handlers.list_images.dynamodb_service')
    def test_burst_handling(self, mock_dynamodb_service, sample_lambda_event, lambda_context):
        """Test handling burst of requests."""
        mock_dynamodb_service.scan_all.return_value = ([], None)
        
        # Send burst of 50 requests rapidly
        burst_size = 50
        responses = []
        
        print(f"\n--- Testing Burst of {burst_size} Requests ---")
        
        start_time = time.time()
        
        for i in range(burst_size):
            event = sample_lambda_event(
                method="GET",
                path="/images",
                query_params={"limit": "10"}
            )
            
            response = list_images.handler(event, lambda_context)
            responses.append(response)
        
        end_time = time.time()
        duration = end_time - start_time
        
        successful = sum(1 for r in responses if r["statusCode"] == 200)
        
        print(f"Processed {burst_size} requests in {duration:.2f} seconds")
        print(f"Successful: {successful}/{burst_size}")
        print(f"Throughput: {burst_size/duration:.2f} requests/second")
        
        # Most requests should succeed
        assert successful >= burst_size * 0.9
    
    @patch('src.lambda_handlers.list_images.dynamodb_service')
    def test_pagination_performance(self, mock_dynamodb_service, sample_lambda_event, lambda_context):
        """Test pagination with large result sets."""
        from src.models.image import ImageMetadata, ImageStatus
        from datetime import datetime
        
        # Create mock dataset of 1000 images
        mock_images = [
            ImageMetadata(
                image_id=f"image-{i:04d}",
                user_id=f"user-{i % 10}",
                filename=f"test-{i}.jpg",
                content_type="image/jpeg",
                file_size=1024000,
                upload_timestamp=datetime.utcnow().isoformat(),
                status=ImageStatus.COMPLETED,
                s3_key=f"images/user-{i % 10}/image-{i}.jpg"
            )
            for i in range(50)  # First page
        ]
        
        mock_dynamodb_service.scan_all.return_value = (mock_images, {"LastKey": "next-token"})
        
        print("\n--- Testing Pagination Performance ---")
        
        event = sample_lambda_event(
            method="GET",
            path="/images",
            query_params={"limit": "50"}
        )
        
        start_time = time.time()
        response = list_images.handler(event, lambda_context)
        end_time = time.time()
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        
        print(f"Retrieved {body['count']} images in {(end_time - start_time)*1000:.2f}ms")
        print(f"Has more pages: {body['has_more']}")
        
        # Response time should be reasonable (< 500ms)
        assert (end_time - start_time) < 0.5
        assert body["count"] == 50
        assert body["has_more"] is True
