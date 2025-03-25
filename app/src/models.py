from datetime import datetime

from database import Base
from pydantic import BaseModel
from sqlalchemy import JSON, Column, DateTime, Integer, String


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
