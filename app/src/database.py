import os
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    status = Column(String)
    species = Column(String)
    type = Column(String)
    gender = Column(String)
    origin = Column(JSON)  # Stores the origin object
    location = Column(JSON)  # Stores the location object
    image = Column(String)
    episode = Column(JSON)  # Stores the episode list
    url = Column(String)
    created = Column(DateTime)


class LocationBase(BaseModel):
    name: str
    url: str


class CharacterResponse(BaseModel):
    id: int
    name: str
    status: str
    species: str
    type: str | None = ""
    gender: str
    origin: LocationBase
    location: LocationBase
    image: str
    episode: list[str]
    url: str
    created: datetime

    class Config:
        orm_mode = True


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_characters_to_db(characters: list[dict], db: Session):
    """Save the characters to the database."""
    for character in characters:
        db_character = Character(
            id=character.get("id"),
            name=character.get("name", ""),
            status=character.get("status", ""),
            species=character.get("species", ""),
            type=character.get("type", ""),
            gender=character.get("gender", ""),
            origin=character.get("origin", {}),
            location=character.get("location", {}),
            image=character.get("image", ""),
            episode=character.get("episode", []),
            url=character.get("url", ""),
            created=character.get("created"),
        )
        db.merge(db_character)
    db.commit()
