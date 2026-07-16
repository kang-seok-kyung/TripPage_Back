# app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from app.database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(50), nullable=False, default="익명")
    password = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) # 팀원 DB 규격 반영

class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(String(100), nullable=False)
    content_type_id = Column(Integer, nullable=False)
    content_type = Column(String, nullable=True)
    title = Column(String(200), nullable=False)
    address = Column(String(300), nullable=False)
    mapx = Column(Float, nullable=False)
    mapy = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)
    region = Column(String(50), nullable=False)