"""Tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_submit_rating_valid(client: TestClient) -> None:
    """Test submitting a valid rating."""
    async def mock_connect(*args, **kwargs):
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_handle.id = "test-workflow-id"
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)
        return mock_client

    with patch("src.api.Client.connect", side_effect=mock_connect):
        payload = {
            "validator_id": 123,
            "target_message_id": 456,
            "target_user_id": 789,
            "channel_id": 100,
            "metrics": [5, 4, 3, 4, 4],
        }

        response = client.post("/submit-rating", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["workflow_id"] == "test-workflow-id"


def test_submit_rating_invalid_metrics_count(client: TestClient) -> None:
    """Test submitting rating with wrong number of metrics."""
    payload = {
        "validator_id": 123,
        "target_message_id": 456,
        "target_user_id": 789,
        "channel_id": 100,
        "metrics": [5, 4, 3],  # Only 3 metrics, should be 5
    }

    response = client.post("/submit-rating", json=payload)

    assert response.status_code == 422  # Validation error


def test_submit_rating_invalid_metric_value(client: TestClient) -> None:
    """Test submitting rating with invalid metric value."""
    payload = {
        "validator_id": 123,
        "target_message_id": 456,
        "target_user_id": 789,
        "channel_id": 100,
        "metrics": [5, 4, 3, 4, 6],  # 6 is out of range
    }

    response = client.post("/submit-rating", json=payload)

    assert response.status_code == 422  # Validation error

