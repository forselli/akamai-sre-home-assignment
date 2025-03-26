from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from cache import redis_client
from healthcheck import check_database, check_redis, get_health  # Replace with actual module name
from psycopg2.extensions import QueryCanceledError
from redis.exceptions import RedisError
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    with patch("healthcheck.engine.connect") as mock_connect:
        mock_conn = MagicMock(spec=Connection)
        mock_connect.return_value.__enter__.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("healthcheck.redis_client") as mock_redis:
        yield mock_redis


def test_check_database_success(mock_db_connection):
    """Test database health check when everything is working."""
    mock_db_connection.execute.return_value.scalar.side_effect = ["10MB", 5]

    result = check_database()

    assert result["status"] == "healthy"
    assert "Database write operations successfully checked" in result["message"]
    assert "database_size" in result["metrics"]
    assert "active_write_transactions" in result["metrics"]


def test_check_database_high_active_writes(mock_db_connection):
    """Test database health check when active write transactions exceed threshold."""
    mock_db_connection.execute.return_value.scalar.side_effect = ["10MB", 100]

    result = check_database()

    assert result["status"] == "unhealthy"
    assert "High number of active write transactions" in result["message"]


def test_check_database_query_timeout(mock_db_connection):
    """Test database health check when a query times out."""
    mock_db_connection.execute.side_effect = QueryCanceledError()

    result = check_database()

    assert result["status"] == "unhealthy"
    assert "Database query timeout" in result["message"]


def test_check_database_sqlalchemy_error(mock_db_connection):
    """Test database health check when a SQLAlchemy error occurs."""
    mock_db_connection.execute.side_effect = SQLAlchemyError("DB error")

    result = check_database()

    assert result["status"] == "unhealthy"
    assert "Database error: DB error" in result["message"]


def test_check_redis_success(mock_redis):
    """Test Redis health check when everything is working."""
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True
    mock_redis.get.return_value = b"test_value"
    mock_redis.delete.return_value = True
    mock_redis.info.return_value = {"used_memory": 5000000, "maxmemory": 100000000}

    result = check_redis()

    assert result["status"] == "healthy"
    assert "Redis connection and operations successfully checked" in result["message"]
    assert "memory_usage_percent" in result["metrics"]


def test_check_redis_ping_failure(mock_redis):
    """Test Redis health check when ping fails."""
    mock_redis.ping.return_value = False

    result = check_redis()

    assert result["status"] == "unhealthy"
    assert "Redis ping failed" in result["message"]


def test_check_redis_write_failure(mock_redis):
    """Test Redis health check when a write operation fails."""
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = False

    result = check_redis()

    assert result["status"] == "unhealthy"
    assert "Redis write operation failed" in result["message"]


def test_check_redis_high_memory_usage(mock_redis):
    """Test Redis health check when memory usage is above threshold."""
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True
    mock_redis.get.return_value = b"test_value"
    mock_redis.delete.return_value = True
    mock_redis.info.return_value = {"used_memory": 95000000, "maxmemory": 100000000}

    result = check_redis()

    assert result["status"] == "unhealthy"
    assert "Redis memory usage critical" in result["message"]


def test_check_redis_exception(mock_redis):
    """Test Redis health check when an exception occurs."""
    mock_redis.ping.side_effect = RedisError("Redis failure")

    result = check_redis()

    assert result["status"] == "unhealthy"
    assert "Redis error: Redis failure" in result["message"]


def test_get_health_all_healthy(mock_db_connection, mock_redis):
    """Test overall health check when everything is healthy."""
    mock_db_connection.execute.return_value.scalar.side_effect = ["10MB", 5]
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True
    mock_redis.get.return_value = b"test_value"
    mock_redis.delete.return_value = True
    mock_redis.info.return_value = {"used_memory": 5000000, "maxmemory": 100000000}

    result = get_health()

    assert result.status == "healthy"
    assert isinstance(result.timestamp, str)
    assert result.checks["database"]["status"] == "healthy"
    assert result.checks["cache"]["status"] == "healthy"


def test_get_health_unhealthy(mock_db_connection, mock_redis):
    """Test overall health check when one component is unhealthy."""
    mock_db_connection.execute.side_effect = SQLAlchemyError("DB error")
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True
    mock_redis.get.return_value = b"test_value"
    mock_redis.delete.return_value = True
    mock_redis.info.return_value = {"used_memory": 5000000, "maxmemory": 100000000}

    result = get_health()

    assert result.status == "unhealthy"
    assert isinstance(result.timestamp, str)
    assert result.checks["database"]["status"] == "unhealthy"
    assert result.checks["cache"]["status"] == "healthy"
