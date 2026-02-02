"""
配置模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from app.models.database import Base


class Config(Base):
    """配置表"""
    __tablename__ = "config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Config(id={self.id}, key='{self.key}')>"
