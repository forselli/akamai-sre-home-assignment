from datetime import datetime

import pytest
from database import Base, Character, save_characters_to_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fixture to create a new database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_save_characters_to_db(db_session):
    """Test saving characters to the database."""
    characters = [
        {
            "id": 1,
            "name": "Rick Sanchez",
            "status": "Alive",
            "species": "Human",
            "type": "",
            "gender": "Male",
            "origin": {"name": "Earth", "url": "https://rickandmortyapi.com/api/location/1"},
            "location": {"name": "Citadel of Ricks", "url": "https://rickandmortyapi.com/api/location/3"},
            "image": "https://rickandmortyapi.com/api/character/avatar/1.jpeg",
            "episode": ["https://rickandmortyapi.com/api/episode/1"],
            "url": "https://rickandmortyapi.com/api/character/1",
            "created": datetime(2017, 11, 4, 18, 48, 46),
        }
    ]

    save_characters_to_db(characters, db_session)

    # Fetch character from DB
    saved_character = db_session.query(Character).filter_by(id=1).first()

    # Assertions
    assert saved_character is not None
    assert saved_character.name == "Rick Sanchez"
    assert saved_character.status == "Alive"
    assert saved_character.species == "Human"
    assert saved_character.gender == "Male"
    assert saved_character.origin["name"] == "Earth"
    assert saved_character.location["name"] == "Citadel of Ricks"
    assert saved_character.image == "https://rickandmortyapi.com/api/character/avatar/1.jpeg"
    assert saved_character.episode == ["https://rickandmortyapi.com/api/episode/1"]
    assert saved_character.url == "https://rickandmortyapi.com/api/character/1"
    assert saved_character.created == datetime(2017, 11, 4, 18, 48, 46)
