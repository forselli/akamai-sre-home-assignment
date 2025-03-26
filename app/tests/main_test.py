from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Create mock engine and connection
mock_engine = MagicMock()
mock_engine.connect.return_value = MagicMock()

# Mock both database engine creation and metadata creation
with patch("database.create_engine", return_value=mock_engine), patch("database.Base.metadata.create_all"):
    from main import app, get_db


# Create a test database session
def override_get_db():
    return MagicMock()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def mock_is_rate_limited():
    """Mock the is_rate_limited function."""
    with patch("main.is_rate_limited", new_callable=AsyncMock, return_value=False) as mock_rate_limited:
        yield mock_rate_limited


@pytest.fixture
def mock_get_characters():
    """Mock the async get_characters function."""
    with patch("main.get_characters", new_callable=AsyncMock) as mock_get_characters:
        mock_get_characters.return_value = [
            {"id": 1, "name": "Rick Sanchez", "origin": {"name": "Earth"}},
            {"id": 2, "name": "Morty Smith", "origin": {"name": "Earth"}},
        ]  # Simulated character data
        yield mock_get_characters


def test_rate_limited_endpoint(mock_is_rate_limited, mock_get_characters):
    # Set the mock to return True (rate limited)
    mock_is_rate_limited.return_value = True

    response = client.get("/characters")
    assert response.status_code == 429
