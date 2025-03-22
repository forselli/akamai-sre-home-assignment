from sqlalchemy import JSON, Column, Integer, String

from .database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    origin = Column(String)
    data = Column(JSON)
