"""
GitLab用户模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.models.database import Base


class GitLabUser(Base):
    """GitLab用户表"""
    __tablename__ = "gitlab_users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200))
    avatar_url = Column(String(500))
    commits_week = Column(Integer, default=0)
    commits_month = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<GitLabUser(id={self.id}, username='{self.username}', name='{self.name}')>"
