import json
from unittest.mock import MagicMock, patch

import pytest
from characters import get_all_characters  # Replace with actual module name
from fastapi import HTTPException
from sqlalchemy.orm import Session


@pytest.fixture
def db_session():
    """Fixture to create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("characters.redis_client") as mock_redis:
        yield mock_redis


@pytest.fixture
def mock_fetch_characters():
    """Mock API fetch function."""
    with patch("characters.fetch_characters") as mock_fetch:
        yield mock_fetch


@pytest.fixture
def mock_save_characters_to_db():
    """Mock database save function."""
    with patch("characters.save_characters_to_db") as mock_save:
        yield mock_save


def test_get_characters_from_cache(mock_redis, db_session):
    """Test when characters are already in the Redis cache."""
    cached_data = [{"id": 1, "name": "Rick Sanchez", "origin": {"name": "Earth"}}]
    mock_redis.get.return_value = json.dumps(cached_data).encode("utf-8")

    result = get_all_characters(db_session)

    assert result == cached_data
    mock_redis.get.assert_called_once_with("characters")


def test_get_characters_from_api(mock_redis, mock_fetch_characters, mock_save_characters_to_db, db_session):
    """Test when characters are fetched from the API and stored in the cache."""
    mock_redis.get.return_value = None  # Simulate cache miss
    api_response = {
        "info": {"pages": 1},
        "results": [
            {"id": 1, "name": "Rick Sanchez", "origin": {"name": "Earth"}},
            {"id": 2, "name": "Morty Smith", "origin": {"name": "Earth"}},
        ],
    }
    mock_fetch_characters.return_value = api_response

    result = get_all_characters(db_session)

    assert len(result) == 2
    assert result[0]["name"] == "Rick Sanchez"
    mock_fetch_characters.assert_called_once_with(
        "https://rickandmortyapi.com/api/character?species=Human&status=Alive&page=", 1
    )
    mock_save_characters_to_db.assert_called_once()


def test_get_characters_api_failure(mock_redis, mock_fetch_characters, db_session):
    """Test API failure scenario."""
    mock_redis.get.return_value = None  # Simulate cache miss
    mock_fetch_characters.side_effect = HTTPException(status_code=500)

    with pytest.raises(HTTPException) as exc_info:
        get_all_characters(db_session)

    assert exc_info.value.status_code == 500
