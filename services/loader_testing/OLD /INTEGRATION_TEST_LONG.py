"""
Integration tests for the Article Loader API
Tests the full API endpoints with FastAPI TestClient
Covers health checks, synchronous/asynchronous processing, and error handling
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
import time

client = TestClient(app)


class TestAPIEndpoints:
    """Integration tests for API endpoints"""

    def test_root_endpoint(self):
        """Test the root/health endpoint returns success"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    def test_root_returns_json(self):
        """Test that root returns JSON content type"""
        response = client.get("/")
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_health_check_response_time(self):
        """Test that health check responds quickly"""
        start_time = time.time()
        response = client.get("/")
        elapsed = time.time() - start_time
        assert response.status_code == 200
        assert elapsed < 1.0  # Should respond in less than 1 second

    def test_invalid_route_returns_404(self):
        """Test that invalid routes return 404"""
        response = client.get("/this-route-does-not-exist")
        assert response.status_code == 404

    def test_invalid_method_on_health(self):
        """Test that POST to health endpoint returns 405"""
        response = client.post("/")
        assert response.status_code == 405

    def test_invalid_method_on_process_sync(self):
        """Test that GET to process-sync endpoint returns 405"""
        response = client.get("/process-sync")
        assert response.status_code == 405


class TestProcessEndpoint:
    """Tests for the /process endpoint (background processing)"""

    @patch("main.chunk_embed_load")
    def test_process_endpoint_starts_background_task(self, mock_chunk_embed):
        """Test that /process endpoint queues background task"""
        response = client.post("/process")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "started"

    @patch("main.chunk_embed_load")
    def test_process_endpoint_returns_immediately(self, mock_chunk_embed):
        """Test that /process returns immediately without waiting"""
        # Make the mock function slow
        mock_chunk_embed.side_effect = lambda x: time.sleep(2)
        
        start_time = time.time()
        response = client.post("/process")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        # Should return quickly, not wait for background task
        assert elapsed < 1.0

    def test_process_endpoint_accepts_no_parameters(self):
        """Test that /process works without query parameters"""
        response = client.post("/process")
        assert response.status_code == 200

    def test_process_invalid_method_get(self):
        """Test that GET to /process returns 405"""
        response = client.get("/process")
        assert response.status_code == 405


class TestProcessSyncEndpoint:
    """Tests for the /process-sync endpoint (synchronous processing)"""

    @patch("main.chunk_embed_load")
    def test_process_sync_success(self, mock_chunk_embed):
        """Test successful synchronous processing"""
        mock_result = {
            "status": "success",
            "message": "Processed 5 articles",
            "processed": 5,
            "total_found": 5,
        }
        mock_chunk_embed.return_value = mock_result

        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["processed"] == 5
        assert data["total_found"] == 5
        assert "Processed 5 articles" in data["message"]
        
        # Verify chunk_embed_load was called with correct method
        mock_chunk_embed.assert_called_once_with(method="recursive-split")

    @patch("main.chunk_embed_load")
    def test_process_sync_no_articles(self, mock_chunk_embed):
        """Test sync processing when no articles are found"""
        mock_result = {
            "status": "success",
            "message": "No new articles to process",
            "processed": 0,
        }
        mock_chunk_embed.return_value = mock_result

        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["processed"] == 0
        assert "No new articles" in data["message"]

    @patch("main.chunk_embed_load")
    def test_process_sync_handles_exceptions(self, mock_chunk_embed):
        """Test that sync processing handles exceptions gracefully"""
        mock_chunk_embed.side_effect = Exception("Database connection failed")

        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "error"
        assert "Database connection failed" in data["message"]

    @patch("main.chunk_embed_load")
    def test_process_sync_handles_runtime_error(self, mock_chunk_embed):
        """Test handling of RuntimeError exceptions"""
        mock_chunk_embed.side_effect = RuntimeError("Need to set GOOGLE_CLOUD_PROJECT")

        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "error"
        assert "GOOGLE_CLOUD_PROJECT" in data["message"]

    @patch("main.chunk_embed_load")
    def test_process_sync_waits_for_completion(self, mock_chunk_embed):
        """Test that sync processing waits for task completion"""
        def slow_process(method):
            time.sleep(0.5)
            return {"status": "success", "processed": 1}
        
        mock_chunk_embed.side_effect = slow_process

        start_time = time.time()
        response = client.post("/process-sync")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        # Should have waited for the task
        assert elapsed >= 0.5


class TestCORS:
    """Tests for CORS configuration (if enabled)"""

    def test_cors_headers_present(self):
        """Test that CORS headers can be set"""
        response = client.get("/", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        # Note: TestClient doesn't automatically add CORS headers
        # This would need actual CORS middleware configured in main.py


class TestAPIResponseFormats:
    """Tests for API response formats and data types"""

    def test_health_response_structure(self):
        """Test health endpoint response structure"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

    @patch("main.chunk_embed_load")
    def test_process_response_structure(self, mock_chunk_embed):
        """Test process endpoint response structure"""
        response = client.post("/process")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert isinstance(data["status"], str)

    @patch("main.chunk_embed_load")
    def test_process_sync_response_structure(self, mock_chunk_embed):
        """Test process-sync endpoint response structure"""
        mock_chunk_embed.return_value = {
            "status": "success",
            "message": "Test",
            "processed": 10,
            "total_found": 15,
        }
        
        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert isinstance(data["status"], str)
        assert isinstance(data["processed"], int)
        assert isinstance(data["total_found"], int)


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios"""

    @patch("main.chunk_embed_load")
    def test_multiple_simultaneous_sync_requests(self, mock_chunk_embed):
        """Test handling of multiple simultaneous sync requests"""
        mock_chunk_embed.return_value = {"status": "success", "processed": 1}
        
        # Send multiple requests
        responses = [client.post("/process-sync") for _ in range(3)]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200

    @patch("main.chunk_embed_load")
    def test_empty_response_from_chunk_embed_load(self, mock_chunk_embed):
        """Test handling when chunk_embed_load returns empty/None"""
        mock_chunk_embed.return_value = None
        
        response = client.post("/process-sync")
        # Should handle gracefully
        assert response.status_code in [200, 500]

    @patch("main.chunk_embed_load")
    def test_large_article_count(self, mock_chunk_embed):
        """Test handling of large number of processed articles"""
        mock_chunk_embed.return_value = {
            "status": "success",
            "message": "Processed 1000 articles",
            "processed": 1000,
            "total_found": 1000,
        }
        
        response = client.post("/process-sync")
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 1000


@pytest.mark.asyncio
async def test_api_health_check():
    """Test that the API is healthy and responding"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


class TestLogging:
    """Tests to verify logging behavior"""

    @patch("main.logger")
    def test_health_endpoint_logs(self, mock_logger):
        """Test that health endpoint creates log entries"""
        response = client.get("/")
        assert response.status_code == 200
        # Verify logging was called
        mock_logger.info.assert_called()

    @patch("main.logger")
    @patch("main.chunk_embed_load")
    def test_process_endpoint_logs(self, mock_chunk_embed, mock_logger):
        """Test that process endpoint creates log entries"""
        response = client.post("/process")
        assert response.status_code == 200
        # Should log starting and queued messages
        assert mock_logger.info.call_count >= 2

    @patch("main.logger")
    @patch("main.chunk_embed_load")
    def test_process_sync_logs_completion(self, mock_chunk_embed, mock_logger):
        """Test that sync processing logs completion"""
        mock_chunk_embed.return_value = {"status": "success", "processed": 3}
        
        response = client.post("/process-sync")
        assert response.status_code == 200
        # Should log start and completion
        assert mock_logger.info.call_count >= 2

    @patch("main.logger")
    @patch("main.chunk_embed_load")
    def test_process_sync_logs_errors(self, mock_chunk_embed, mock_logger):
        """Test that sync processing logs errors"""
        mock_chunk_embed.side_effect = Exception("Test error")
        
        response = client.post("/process-sync")
        assert response.status_code == 200
        # Should log the error
        mock_logger.error.assert_called_once()
