import os
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from . import models

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_characters_to_db(characters: List[dict], db: Session):
    """Save the characters to the database."""
    for character in characters:
        db_character = models.Character(
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
