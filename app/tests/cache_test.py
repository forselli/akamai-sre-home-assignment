from unittest.mock import patch

from app.src.cache import API_RATE_LIMIT, API_RATE_WINDOW, is_rate_limited


@patch("app.src.cache.redis_client")
def test_is_rate_limited_no_existing_key(mock_redis_client):
    """Test when no key exists in Redis."""
    mock_redis_client.get.return_value = None

    result = is_rate_limited()

    mock_redis_client.setex.assert_called_once_with("api_request_count", API_RATE_WINDOW, 1)
    assert result is False


@patch("app.src.cache.redis_client")
def test_is_rate_limited_below_limit(mock_redis_client):
    """Test when the request count is below the rate limit."""
    mock_redis_client.get.return_value = b"3"

    result = is_rate_limited()

    mock_redis_client.incr.assert_called_once_with("api_request_count")
    assert result is False


@patch("app.src.cache.redis_client")
def test_is_rate_limited_at_limit(mock_redis_client):
    """Test when the request count is at the rate limit."""
    mock_redis_client.get.return_value = str(API_RATE_LIMIT).encode()

    result = is_rate_limited()

    assert result is True
    mock_redis_client.incr.assert_not_called()
