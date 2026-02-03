"""
MySQL数据库元数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.models.database import Base


class MySQLDatabase(Base):
    """MySQL数据库表"""
    __tablename__ = "mysql_databases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MySQLDatabase(name='{self.name}')>"
